from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.ml.texts import user_query


class TextEncoder:
    def __init__(self) -> None:
        self.model = SentenceTransformer(
            settings.text_encoder_model,
            device=settings.text_encoder_device,
        )

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=settings.text_encoder_batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def encode_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            [user_query(text)],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        return vector.astype(float).tolist()


@lru_cache(maxsize=1)
def get_text_encoder() -> TextEncoder:
    return TextEncoder()
