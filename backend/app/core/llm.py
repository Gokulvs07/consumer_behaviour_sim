import os
os.environ["HF_HUB_OFFLINE"] = "1"

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings


_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(
            settings.embedding_model,
            device="cpu",
            local_files_only=True,
        )
    return _embedder


def embed_texts(texts: list[str]) -> np.ndarray:
    """Returns L2-normalized embeddings so dot product == cosine similarity."""
    model = get_embedder()
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)


async def generate_persona_response(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Calls local Ollama /api/chat endpoint asynchronously."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 150,
            "num_ctx": 2048,  # Keeps VRAM usage low so it stays on GPU
        },
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    """Calls local Ollama /api/chat endpoint asynchronously."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 150,  # Keep reactions concise and visceral
        },
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
