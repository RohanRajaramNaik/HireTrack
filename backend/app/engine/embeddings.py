"""Sentence embeddings for the semantic score.

Loads all-MiniLM-L6-v2 from the local models/ folder (CPU only, offline) and
caches every embedding in memory, keyed by the exact text. Re-running a match
or matching 2,000 candidates against a second job only encodes text that has
never been seen before, in batches.

If the model is missing (not yet downloaded) or disabled for tests, a small
deterministic bag-of-words hashing embedder is used so the app keeps working;
a warning is logged and /api/stats reports which embedder is active.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from collections.abc import Sequence

import numpy as np

from ..config import settings

log = logging.getLogger("hiretrack.embeddings")

_WORD_RE = re.compile(r"[a-z0-9+#.]+")


class HashingEmbedder:
    """Fallback: signed feature hashing of word unigrams + bigrams, L2-normalised."""

    name = "hashing-fallback"
    dim = 384

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = _WORD_RE.findall(text.lower())
            grams = words + [f"{a} {b}" for a, b in zip(words, words[1:])]
            for g in grams:
                h = int.from_bytes(hashlib.md5(g.encode()).digest()[:4], "little")
                out[i, h % self.dim] += 1.0 if (h >> 31) & 1 else -1.0
            norm = np.linalg.norm(out[i])
            if norm:
                out[i] /= norm
        return out


class Embedder:
    """Thread-safe, cached text -> vector encoder."""

    def __init__(self) -> None:
        self._model = None
        self._backend_name = "not-loaded"
        self._cache: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()

    # -- model loading -----------------------------------------------------
    def _load(self) -> None:
        if self._model is not None:
            return
        if settings.disable_model:
            self._model, self._backend_name = HashingEmbedder(), HashingEmbedder.name
            return
        local = settings.model_dir / "all-MiniLM-L6-v2"
        try:
            from sentence_transformers import SentenceTransformer

            if not local.exists():
                raise FileNotFoundError(f"{local} not found. Run: python -m app.download_model")
            self._model = SentenceTransformer(str(local), device="cpu")
            self._backend_name = "all-MiniLM-L6-v2"
            log.info("Loaded sentence-transformers model from %s", local)
        except Exception as exc:  # pragma: no cover - depends on environment
            log.warning("Semantic model unavailable (%s); using hashing fallback", exc)
            self._model, self._backend_name = HashingEmbedder(), HashingEmbedder.name

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def warm_up(self) -> None:
        with self._lock:
            self._load()

    # -- encoding ------------------------------------------------------------
    def encode(self, texts: Sequence[str], batch_size: int = 64) -> np.ndarray:
        """Return an (n, dim) matrix of L2-normalised embeddings for `texts`.

        Only texts missing from the cache are sent to the model, in batches.
        """
        with self._lock:
            self._load()
            missing = list(dict.fromkeys(t for t in texts if t not in self._cache))
            if missing:
                if isinstance(self._model, HashingEmbedder):
                    vecs = self._model.encode(missing)
                else:
                    vecs = self._model.encode(
                        missing,
                        batch_size=batch_size,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
                for t, v in zip(missing, vecs):
                    self._cache[t] = np.asarray(v, dtype=np.float32)
            if not texts:
                return np.zeros((0, 384), dtype=np.float32)
            return np.vstack([self._cache[t] for t in texts])

    def cache_size(self) -> int:
        return len(self._cache)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


embedder = Embedder()
