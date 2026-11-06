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
    """Thread-safe, cached text -> vector encoder.

    The cache is keyed by the SHA-1 of the text (so no CV text is held twice or
    written to disk) and persisted to data/embedding_cache.npz, so CV summaries
    are only ever encoded once, even across restarts.
    """

    def __init__(self) -> None:
        self._model = None
        self._backend_name = "not-loaded"
        self._cache: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._dirty = False

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    @property
    def _cache_file(self):
        return settings.data_dir / "embedding_cache.npz"

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

            if not (local / "model.safetensors").exists():
                raise FileNotFoundError(f"{local} not found. Run: python -m app.download_model")
            self._model = SentenceTransformer(str(local), device="cpu")
            self._backend_name = "all-MiniLM-L6-v2"
            log.info("Loaded sentence-transformers model from %s", local)
            self._load_disk_cache()
        except Exception as exc:  # pragma: no cover - depends on environment
            log.warning("Semantic model unavailable (%s); using hashing fallback", exc)
            self._model, self._backend_name = HashingEmbedder(), HashingEmbedder.name

    def _load_disk_cache(self) -> None:
        try:
            if self._cache_file.exists():
                with np.load(self._cache_file, allow_pickle=False) as z:
                    if str(z["model"]) != self._backend_name:
                        return
                    for k, v in zip(z["keys"], z["vectors"]):
                        self._cache[str(k)] = v
                log.info("Loaded %d cached embeddings from disk", len(self._cache))
        except Exception:  # pragma: no cover - a corrupt cache is simply rebuilt
            log.warning("Embedding cache unreadable; it will be rebuilt")
            self._cache.clear()

    def save(self) -> None:
        """Write the cache to disk if anything new was encoded (real model only)."""
        with self._lock:
            if not self._dirty or isinstance(self._model, HashingEmbedder) or not self._cache:
                return
            keys = np.array(list(self._cache.keys()))
            vectors = np.vstack(list(self._cache.values())).astype(np.float32)
            tmp = self._cache_file.with_suffix(".tmp.npz")
            np.savez(tmp, keys=keys, vectors=vectors, model=np.array(self._backend_name))
            tmp.replace(self._cache_file)
            self._dirty = False
            log.info("Saved %d embeddings to disk cache", len(keys))

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
            keys = [self._key(t) for t in texts]
            missing = {}
            for k, t in zip(keys, texts):
                if k not in self._cache and k not in missing:
                    missing[k] = t
            if missing:
                todo = list(missing.values())
                if isinstance(self._model, HashingEmbedder):
                    vecs = self._model.encode(todo)
                else:
                    vecs = self._model.encode(
                        todo,
                        batch_size=batch_size,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
                for k, v in zip(missing.keys(), vecs):
                    self._cache[k] = np.asarray(v, dtype=np.float32)
                self._dirty = True
            if not texts:
                return np.zeros((0, 384), dtype=np.float32)
            return np.vstack([self._cache[k] for k in keys])

    def cached(self, texts: Sequence[str]) -> int:
        """How many of `texts` are already encoded (for the "preparing" status)."""
        return sum(1 for t in texts if self._key(t) in self._cache)

    def cache_size(self) -> int:
        return len(self._cache)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


embedder = Embedder()
