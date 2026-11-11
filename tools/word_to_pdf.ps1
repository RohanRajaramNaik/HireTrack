# Open a .docx in Microsoft Word, update all fields (table of contents, page
# numbers), save it, and export a PDF next to it.
#   powershell -ExecutionPolicy Bypass -File tools\word_to_pdf.ps1 <path.docx>
param([Parameter(Mandatory = $true)][string]$Path)
$full = (Resolve-Path $Path).Path
$pdf = [System.IO.Path]::ChangeExtension($full, '.pdf')
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($full, $false, $false)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)   # 17 = wdExportFormatPDF
    $doc.Close($false)
    Write-Output "Saved $full"
    Write-Output "PDF   $pdf"
}
finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
