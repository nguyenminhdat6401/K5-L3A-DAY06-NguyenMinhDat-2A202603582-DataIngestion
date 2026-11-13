"""Real local embeddings using a pinned multilingual E5 snapshot."""

import re
from pathlib import Path

from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer


class MyEmbedder:
    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        revision: str | None = None,
    ) -> None:
        if model_name != "intfloat/multilingual-e5-small":
            raise ValueError(
                "This adapter is configured for multilingual-e5-small."
            )

        self.model_name = model_name

        # Default cache path:
        # .../snapshots/<commit_hash>/config.json
        config_path = hf_hub_download(
            repo_id=model_name,
            filename="config.json",
            revision=revision,
        )

        self.revision = Path(config_path).parent.name

        if not re.fullmatch(r"[0-9a-f]{40}", self.revision):
            raise RuntimeError(
                f"Unexpected model snapshot path: {config_path}"
            )

        self.model = SentenceTransformer(
            model_name,
            revision=self.revision,
            device="cpu",
            trust_remote_code=False,
        )

        get_dimension = getattr(
            self.model,
            "get_embedding_dimension",
            None,
        )

        if get_dimension is None:
            get_dimension = (
                self.model.get_sentence_embedding_dimension
            )

        self.dimensions = get_dimension()

        if self.dimensions != 384:
            raise ValueError(
                f"Unexpected embedding dimension: {self.dimensions}"
            )

    def _embed(
        self,
        texts: list[str],
        prefix: str,
    ) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("Cannot embed empty text.")

        inputs = [prefix + text for text in texts]

        encoded = self.model.tokenizer(
            inputs,
            truncation=False,
            padding=False,
        )

        lengths = [
            len(token_ids)
            for token_ids in encoded["input_ids"]
        ]

        limit = self.model.max_seq_length

        for index, length in enumerate(lengths):
            if length > limit:
                raise ValueError(
                    f"Input {index} has {length} tokens; "
                    f"model limit is {limit}. "
                    "Reduce chunk size before running experiments."
                )

        vectors = self.model.encode(
            inputs,
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(inputs) > 1,
        )

        return vectors.tolist()

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return self._embed(texts, prefix="passage: ")

    def embed_query(
        self,
        question: str,
    ) -> list[float]:
        return self._embed(
            [question],
            prefix="query: ",
        )[0]