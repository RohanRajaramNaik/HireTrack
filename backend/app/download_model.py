"""One-off download of the sentence-transformers model for offline use.

Run once after `pip install` (needs internet):
    cd backend
    python -m app.download_model

The model is saved to <project>/models/all-MiniLM-L6-v2 and loaded from there
with HF_HUB_OFFLINE=1 at runtime, so the app never touches the network again.
"""
import os
import sys

# Must be set before importing huggingface/sentence-transformers.
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

from .config import settings  # noqa: E402

os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
# The xet transfer backend can stall on some networks; plain HTTPS is reliable.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

ALLOW = ["*.json", "*.txt", "model.safetensors", "1_Pooling/*", "2_Normalize/*", "modules.json"]


def main() -> int:
    target = settings.model_dir / "all-MiniLM-L6-v2"
    if (target / "model.safetensors").exists() and "--force" not in sys.argv:
        print(f"Model already present at {target}")
        return 0
    from huggingface_hub import snapshot_download

    print(f"Downloading {settings.model_name} (about 90 MB) ...", flush=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(settings.model_name, local_dir=str(target), allow_patterns=ALLOW)

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(target), device="cpu")
    vec = model.encode(["HireTrack self-test"], normalize_embeddings=True)
    print(f"Saved to {target} (embedding size {vec.shape[1]}). The app can now run offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
