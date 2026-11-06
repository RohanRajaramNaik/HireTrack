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


def main() -> int:
    target = settings.model_dir / "all-MiniLM-L6-v2"
    if (target / "config.json").exists() and "--force" not in sys.argv:
        print(f"Model already present at {target}")
        return 0
    from sentence_transformers import SentenceTransformer

    print(f"Downloading {settings.model_name} ...")
    model = SentenceTransformer(settings.model_name, device="cpu")
    target.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(target))
    vec = model.encode(["HireTrack self-test"], normalize_embeddings=True)
    print(f"Saved to {target} (embedding size {vec.shape[1]}). The app can now run offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
