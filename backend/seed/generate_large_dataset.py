"""Generate a large, fictitious IT candidate pool for demos and performance tests.

    python seed/generate_large_dataset.py              # writes seed/large_candidates.json
    python seed/generate_large_dataset.py --count 500  # custom size

The Admin screen's "Load large demo dataset" calls generate() directly.
Output is deterministic for a given seed, so every demo shows the same data.
All names, emails and employers are made up.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

FIRST_NAMES = [
    "Sipho", "Thandiwe", "Lerato", "Kagiso", "Ayanda", "Naledi", "Mpho", "Zanele", "Tshepo", "Nomsa",
    "Andile", "Lwazi", "Busisiwe", "Thabo", "Palesa", "Karabo", "Lindiwe", "Bongani", "Nokuthula", "Themba",
    "Refilwe", "Sibusiso", "Precious", "Mandla", "Dineo", "Kabelo", "Ntombi", "Lebo", "Siyabonga", "Zodwa",
    "Johan", "Pieter", "Anri", "Ruan", "Marike", "Francois", "Elize", "Henk", "Liezl", "Wian",
    "Chantelle", "Tasneem", "Fatima", "Yusuf", "Priya", "Kavitha", "Rajesh", "Nikhil", "Aisha", "Zaid",
    "Megan", "Jason", "Nicole", "Craig", "Kirsten", "Brandon", "Caitlin", "Dylan", "Tamryn", "Grant",
    "Ofentse", "Kamogelo", "Boitumelo", "Tumelo", "Onalenna", "Masego", "Rethabile", "Katlego", "Amahle", "Luyanda",
]
SURNAMES = [
    "Nkosi", "Dlamini", "Mahlangu", "Molefe", "Zulu", "Mokoena", "Sithole", "Khumalo", "Ndlovu", "Ngcobo",
    "Mthembu", "Shabalala", "Masilela", "Mabena", "Radebe", "Mazibuko", "Cele", "Hadebe", "Mkhize", "Gumede",
    "Botha", "van Wyk", "Pretorius", "du Plessis", "Venter", "Nel", "van der Merwe", "Coetzee", "Steyn", "Kruger",
    "Adams", "Jacobs", "Petersen", "Hendricks", "Isaacs", "Patel", "Naidoo", "Pillay", "Govender", "Moodley",
    "Smith", "Williams", "Brown", "Taylor", "Fourie", "Maluleke", "Baloyi", "Mathebula", "Chauke", "Tshabalala",
    "Modise", "Seabi", "Motaung", "Letsoalo", "Phiri", "Mabaso", "Mabuza", "Ntuli", "Moloi", "Sekgobela",
]

INDUSTRIES = [
    "retail bank", "short-term insurer", "mobile network operator", "online retailer", "logistics group",
    "healthcare provider", "mining house", "fintech start-up", "government department", "university",
    "energy utility", "media company", "airline", "property group", "consulting firm", "e-commerce marketplace",
]

# Each role: titles by seniority, core skills (most candidates have most of
# these), optional skills, and sentence templates for the CV summary.
ROLES: dict[str, dict] = {
    "data": {
        "titles": ["Junior Data Engineer", "Data Engineer", "Senior Data Engineer", "Lead Data Engineer"],
        "core": ["Python", "SQL", "ETL", "Data Modelling"],
        "optional": ["AWS", "Azure", "GCP", "Airflow", "Spark", "dbt", "Kafka", "Snowflake", "Databricks",
                     "Terraform", "Redshift", "Postgres", "Docker", "Py", "Data Warehousing"],
        "openers": [
            "Data engineer at a {industry}, building pipelines that move data from {n} source systems into the {platform}.",
            "I design and run batch and streaming pipelines for a {industry}, landing data in the {platform}.",
            "{years_word} years building data platforms; currently responsible for ingestion into the {platform} at a {industry}.",
        ],
        "middles": [
            "Orchestrate daily loads with {tool} and model reporting tables so analysts can self-serve.",
            "Rewrote legacy stored procedures as tested, version-controlled transformations, cutting run time by {pct} percent.",
            "Added data quality checks and alerting that reduced failed loads by {pct} percent.",
            "Process roughly {rows} million rows a day with distributed compute while keeping cloud costs predictable.",
            "Work with data scientists to publish trusted feature tables and document lineage.",
        ],
        "platforms": ["AWS data lake", "Azure lakehouse", "Snowflake warehouse", "GCP BigQuery warehouse", "on-premise warehouse"],
        "tools": ["Airflow", "Data Factory", "Dagster", "cron and shell scripts", "Step Functions"],
    },
    "cloud": {
        "titles": ["Cloud Support Engineer", "Cloud Engineer", "Senior Cloud Engineer", "Cloud Architect"],
        "core": ["AWS", "Linux", "Networking", "Terraform"],
        "optional": ["Azure", "GCP", "Kubernetes", "Docker", "Python", "Bash", "IAM", "CloudFormation",
                     "Ansible", "K8s", "Cost Optimisation", "Monitoring"],
        "openers": [
            "Cloud engineer at a {industry}, responsible for {n} production accounts and their landing zone.",
            "I build and operate cloud infrastructure for a {industry}, mostly on the {platform}.",
            "{years_word} years in infrastructure, the last few migrating workloads from data centres to the {platform}.",
        ],
        "middles": [
            "Define networks, identity and databases as code with {tool} and review every change through pull requests.",
            "Reduced the monthly cloud bill by {pct} percent through right-sizing and reserved capacity.",
            "Run on-call for {n} services and write post-incident reviews that lead to real fixes.",
            "Designed a multi-region set-up that improved recovery time objectives for critical systems.",
            "Automated account provisioning so new teams get secure environments in under a day.",
        ],
        "platforms": ["AWS platform", "Azure platform", "Google Cloud platform", "hybrid VMware and AWS estate"],
        "tools": ["Terraform", "CloudFormation", "Bicep", "Pulumi"],
    },
    "software": {
        "titles": ["Junior Software Developer", "Software Developer", "Senior Software Engineer", "Tech Lead"],
        "core": ["JavaScript", "Git", "REST APIs", "SQL"],
        "optional": ["React", "Node.js", "TypeScript", "Java", "C#", ".NET", "Python", "Postgres", "Docker",
                     "Angular", "Vue", "JS", "TS", "MongoDB", "Spring Boot", "AWS"],
        "openers": [
            "Software developer at a {industry}, shipping features to a product used by {n} thousand customers.",
            "I build web applications end to end for a {industry}, from the front end to the services behind it, on the {platform} stack.",
            "{years_word} years writing production software, most recently on the {platform} stack.",
        ],
        "middles": [
            "Design APIs, write the database migrations and cover changes with automated tests before review.",
            "Improved page load times by {pct} percent by profiling slow queries and caching hot paths.",
            "Mentor junior developers and run code reviews focused on readability and safety.",
            "Built an internal component library that made new screens faster to deliver and more accessible.",
            "Took ownership of a legacy module, added tests and refactored it without downtime.",
        ],
        "platforms": ["React and Node", "Angular and .NET", "Java Spring", "Vue and Python", "mobile and web"],
        "tools": ["GitHub Actions", "Azure DevOps", "Jenkins", "GitLab CI"],
    },
    "security": {
        "titles": ["SOC Analyst", "Security Analyst", "Senior Security Engineer", "Security Architect"],
        "core": ["Security Operations", "SIEM", "Incident Response", "Networking"],
        "optional": ["Penetration Testing", "Vulnerability Management", "Python", "Azure", "AWS", "ISO 27001",
                     "Splunk", "Firewalls", "Threat Hunting", "Pen Testing", "Identity and Access Management"],
        "openers": [
            "Security analyst in the operations centre of a {industry}, triaging alerts across {n} thousand endpoints.",
            "I protect the systems of a {industry}, focusing on detection and response on the {platform}.",
            "{years_word} years in information security, from monitoring to leading investigations.",
        ],
        "middles": [
            "Tune detection rules in {tool} to cut false positives by {pct} percent.",
            "Lead incident response for phishing and malware cases and write clear timelines for management.",
            "Run quarterly vulnerability scans and track remediation with system owners.",
            "Built playbooks that automate the first steps of common investigations.",
            "Support audits against ISO 27001 controls and keep evidence organised.",
        ],
        "platforms": ["Microsoft security stack", "Splunk platform", "cloud and on-premise estate"],
        "tools": ["Splunk", "Microsoft Sentinel", "QRadar", "Elastic"],
    },
    "bi": {
        "titles": ["Junior BI Developer", "BI Developer", "Senior BI Analyst", "BI Manager"],
        "core": ["SQL", "Power BI", "Data Visualisation", "Excel"],
        "optional": ["DAX", "SSIS", "Tableau", "Python", "Data Warehousing", "SQL Server", "PBI", "Stakeholder Management",
                     "Qlik", "Statistics"],
        "openers": [
            "BI developer at a {industry}, owning {n} dashboards used by finance and operations.",
            "I turn messy operational data into reports that managers at a {industry} actually use.",
            "{years_word} years in reporting and analytics, building on the {platform}.",
        ],
        "middles": [
            "Model star schemas and write measures so numbers match across every report.",
            "Replaced {n} manual spreadsheets with automated refreshes, saving days of work each month.",
            "Run requirement sessions with business users and prototype visuals before building.",
            "Improved report performance by {pct} percent through better data models.",
            "Train staff to explore data themselves with governed datasets.",
        ],
        "platforms": ["Microsoft BI stack", "Tableau platform", "Qlik platform"],
        "tools": ["Power BI", "SSIS", "Tableau Prep"],
    },
    "qa": {
        "titles": ["Junior Tester", "QA Engineer", "Senior QA Engineer", "Test Lead"],
        "core": ["Test Automation", "Manual Testing", "Test Planning", "SQL"],
        "optional": ["Selenium", "Cypress", "Python", "JavaScript", "API Testing", "Jira", "Performance Testing",
                     "Playwright", "CI/CD", "Postman", "Java"],
        "openers": [
            "QA engineer at a {industry}, responsible for release quality across {n} applications.",
            "I make sure software at a {industry} works before customers see it, using the {platform}.",
            "{years_word} years in testing, moving from manual test packs to automated suites.",
        ],
        "middles": [
            "Built an automated regression suite with {tool} that runs on every pull request.",
            "Cut regression time by {pct} percent by automating the most-used customer journeys.",
            "Write test plans with product owners and report defects with clear reproduction steps.",
            "Run performance tests before peak trading periods and report bottlenecks to developers.",
            "Validate data after releases with SQL checks against expected results.",
        ],
        "platforms": ["Selenium framework", "Cypress framework", "Playwright framework"],
        "tools": ["Selenium", "Cypress", "Playwright", "Postman"],
    },
    "devops": {
        "titles": ["Junior DevOps Engineer", "DevOps Engineer", "Senior DevOps Engineer", "Site Reliability Engineer"],
        "core": ["CI/CD", "Docker", "Linux", "Git"],
        "optional": ["Kubernetes", "K8s", "Terraform", "AWS", "Azure", "Ansible", "Jenkins", "GitHub Actions",
                     "Prometheus", "Grafana", "Python", "Bash", "Helm"],
        "openers": [
            "DevOps engineer at a {industry}, running the build and release pipelines for {n} teams.",
            "I keep deployments boring at a {industry}: automated, observable and easy to roll back on the {platform}.",
            "{years_word} years automating infrastructure and delivery pipelines.",
        ],
        "middles": [
            "Moved builds to {tool}, taking deployment time from hours to {n} minutes.",
            "Containerised legacy services and run them on Kubernetes with health checks and autoscaling.",
            "Set up monitoring dashboards and alerts that cut mean time to recovery by {pct} percent.",
            "Manage configuration with Ansible and infrastructure with Terraform.",
            "Coach developers to own their pipelines and on-call rotas.",
        ],
        "platforms": ["Kubernetes platform", "AWS platform", "Azure platform", "on-premise Linux estate"],
        "tools": ["GitHub Actions", "Jenkins", "GitLab CI", "Azure DevOps", "Argo CD"],
    },
    "support": {
        "titles": ["Service Desk Agent", "IT Support Technician", "Senior Support Engineer", "IT Support Lead"],
        "core": ["Troubleshooting", "Windows", "Active Directory", "Customer Service"],
        "optional": ["Office 365", "Networking", "ITIL", "Linux", "PowerShell", "Hardware Support", "Jira",
                     "ServiceNow", "Azure AD", "SQL"],
        "openers": [
            "IT support technician at a {industry}, looking after {n} users across several sites.",
            "I resolve hardware, software and access problems for staff at a {industry} using the {platform}.",
            "{years_word} years in IT support, from the service desk to second-line escalations.",
        ],
        "middles": [
            "Resolve around {n} tickets a week and keep first-contact resolution above target.",
            "Wrote knowledge-base articles that reduced repeat calls by {pct} percent.",
            "Manage user accounts, laptops and licences, and onboard new starters.",
            "Follow ITIL incident and change processes and escalate with clear notes.",
            "Automated routine account tasks with PowerShell scripts.",
        ],
        "platforms": ["ServiceNow service desk", "Jira Service Management", "Microsoft 365 environment"],
        "tools": ["ServiceNow", "PowerShell", "Intune"],
    },
}

ROLE_WEIGHTS = {"data": 18, "cloud": 13, "software": 22, "security": 9, "bi": 11, "qa": 9, "devops": 10, "support": 8}
# Education level distribution (1 Matric ... 7 Doctorate)
EDU_LEVELS = ["Matric", "Higher Certificate", "Diploma", "Bachelor's Degree", "Honours", "Master's", "Doctorate"]
EDU_WEIGHTS = [6, 10, 22, 34, 16, 10, 2]

YEARS_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight",
               9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}

CLOSERS = [
    "Looking for a team that values {value}.",
    "Known for {value} and calm problem-solving under pressure.",
    "Hold a {cert} and keep learning through community meet-ups.",
    "Enjoy {value} and explaining technical work to non-technical colleagues.",
    "",
    "",
]
VALUES = ["clear documentation", "ownership", "careful testing", "mentoring", "pragmatic delivery", "measurable impact"]
CERTS = ["cloud practitioner certificate", "vendor associate certification",
         "Scrum Master certificate", "ITIL Foundation certificate"]


def _years(rng: random.Random, level_idx: int) -> float:
    ranges = [(0, 2), (2, 5), (5, 10), (8, 20)]
    lo, hi = ranges[level_idx]
    return float(rng.randint(lo, hi))


def _summary(rng: random.Random, role: dict, years: float) -> str:
    fill = {
        "industry": rng.choice(INDUSTRIES),
        "n": rng.randint(3, 60),
        "platform": rng.choice(role["platforms"]),
        "tool": rng.choice(role["tools"]),
        "pct": rng.choice([15, 20, 25, 30, 35, 40, 45, 50, 60]),
        "rows": rng.randint(2, 900),
        "years_word": YEARS_WORDS.get(int(years), str(int(years)) if years else "Under one"),
        "value": rng.choice(VALUES),
        "cert": rng.choice(CERTS),
    }
    if years < 1:
        opener = rng.choice([o for o in role["openers"] if "{years_word}" not in o])
    else:
        opener = rng.choice(role["openers"])
    middles = rng.sample(role["middles"], k=rng.randint(2, 3))
    parts = [opener, *middles, rng.choice(CLOSERS)]
    return " ".join(p.format(**fill) for p in parts if p).strip()


def generate(count: int = 2000, seed: int = 20251106) -> list[dict]:
    """Return `count` fictitious candidates in the same shape as dummy_candidates.json."""
    rng = random.Random(seed)
    roles = list(ROLE_WEIGHTS)
    weights = [ROLE_WEIGHTS[r] for r in roles]
    seen_names: set[str] = set()
    seen_summaries: set[str] = set()
    out: list[dict] = []
    while len(out) < count:
        role_key = rng.choices(roles, weights)[0]
        role = ROLES[role_key]
        level_idx = rng.choices([0, 1, 2, 3], [20, 40, 28, 12])[0]
        years = _years(rng, level_idx)
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"
        if name in seen_names:
            name = f"{name.split(' ', 1)[0]} {rng.choice(FIRST_NAMES)[0]}. {name.split(' ', 1)[1]}"
        if name in seen_names:
            continue
        summary = _summary(rng, role, years)
        if summary in seen_summaries or not 20 <= len(summary) <= 3000:
            continue
        core = rng.sample(role["core"], k=rng.randint(2, len(role["core"])))
        optional = rng.sample(role["optional"], k=rng.randint(1, 5))
        edu = rng.choices(EDU_LEVELS, EDU_WEIGHTS)[0]
        if role_key == "support" and edu in ("Master's", "Doctorate"):
            edu = "Diploma"
        titles = role["titles"][level_idx]
        if level_idx:
            titles += "; " + role["titles"][level_idx - 1]
        email_user = name.lower().replace(" ", ".").replace("..", ".").replace("'", "")
        seen_names.add(name)
        seen_summaries.add(summary)
        out.append(
            {
                "full_name": name,
                "email": f"{email_user}.{len(out)}@example.org",
                "years_experience": years,
                "education": edu,
                "previous_titles": titles,
                "skills": core + [s for s in optional if s not in core],
                "resume_summary": summary,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20251106)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("large_candidates.json"))
    args = ap.parse_args()
    data = generate(args.count, args.seed)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(data)} candidates to {args.out}")


if __name__ == "__main__":
    main()
