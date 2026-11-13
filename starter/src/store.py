"""Persistent vector storage and exact cosine search with pgvector."""

import json
import math

import psycopg
from psycopg.types.json import Jsonb

from .models import Chunk


FILTER_FIELDS = {
    "section",
    "year",
    "version",
    "category",
    "audience",
    "language",
    "effective_date",
    "document_type",
}


class PgVectorStore:
    def __init__(
        self,
        database_url: str,
        dimensions: int,
        model_signature: str,
    ) -> None:
        if type(dimensions) is not int or not 1 <= dimensions <= 2000:
            raise ValueError("Invalid vector dimensions.")

        self.dimensions = dimensions
        self.model_signature = model_signature

        self.connection = psycopg.connect(
            database_url,
            connect_timeout=10,
            autocommit=True,
        )

    def close(self) -> None:
        self.connection.close()

    def create_schema(self) -> None:
        with self.connection.transaction():
            self.connection.execute(
                "CREATE EXTENSION IF NOT EXISTS vector"
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS day6_store_settings (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            self.connection.execute(
                """
                INSERT INTO day6_store_settings (name, value)
                VALUES ('model_signature', %s)
                ON CONFLICT (name) DO NOTHING
                """,
                (self.model_signature,),
            )

            existing = self.connection.execute(
                """
                SELECT value
                FROM day6_store_settings
                WHERE name = 'model_signature'
                """
            ).fetchone()[0]

            if existing != self.model_signature:
                raise ValueError(
                    "Database already uses another model snapshot. "
                    "Do not mix incompatible embeddings."
                )

            # dimensions is validated as an integer above.
            self.connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS day6_chunks (
                    strategy TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata JSONB NOT NULL,
                    embedding VECTOR({self.dimensions}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id),
                    CHECK (strategy IN ('A', 'B'))
                )
                """
            )

            vector_type = self.connection.execute(
                """
                SELECT format_type(atttypid, atttypmod)
                FROM pg_attribute
                WHERE attrelid = 'day6_chunks'::regclass
                  AND attname = 'embedding'
                """
            ).fetchone()[0]

            if vector_type != f"vector({self.dimensions})":
                raise ValueError("Existing vector dimensions differ.")

    def _vector_literal(self, vector: list[float]) -> str:
        if len(vector) != self.dimensions:
            raise ValueError("Incorrect vector dimensions.")

        values = [float(value) for value in vector]

        if not all(math.isfinite(value) for value in values):
            raise ValueError("Vector contains non-finite values.")

        if not any(value != 0 for value in values):
            raise ValueError("Zero vector is invalid for cosine search.")

        return json.dumps(values, allow_nan=False)

    def upsert(
        self,
        strategy: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        """Atomically replace a complete strategy snapshot.

        This removes obsolete chunks when source data changes,
        and prevents duplicates on repeated ingestion.
        """
        if strategy not in {"A", "B"}:
            raise ValueError("Store A or B. C reuses B.")

        if not chunks or len(chunks) != len(vectors):
            raise ValueError("Need one vector per chunk.")

        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("Duplicate chunk IDs.")

        rows = []

        for chunk, vector in zip(chunks, vectors):
            rows.append((
                strategy,
                chunk.chunk_id,
                chunk.document_id,
                chunk.source,
                chunk.page,
                chunk.text,
                Jsonb(chunk.metadata),
                self._vector_literal(vector),
            ))

        # If insertion fails, deletion is rolled back too.
        with self.connection.transaction():
            self.connection.execute(
                "DELETE FROM day6_chunks WHERE strategy = %s",
                (strategy,),
            )

            with self.connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO day6_chunks (
                        strategy, chunk_id, document_id, source,
                        page, text, metadata, embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    rows,
                )

    def count(self, strategy: str) -> int:
        stored_strategy = "B" if strategy == "C" else strategy

        return self.connection.execute(
            "SELECT COUNT(*) FROM day6_chunks WHERE strategy = %s",
            (stored_strategy,),
        ).fetchone()[0]

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict | None = None,
    ) -> list[dict]:
        if strategy not in {"A", "B", "C"}:
            raise ValueError("Unknown strategy.")

        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if filters is None:
            filters = {}

        if not isinstance(filters, dict):
            raise ValueError("Filters must be a dictionary.")

        if not set(filters).issubset(FILTER_FIELDS):
            raise ValueError("Unsupported filter field.")

        if any(
            type(value) not in (str, int, bool)
            for value in filters.values()
        ):
            raise ValueError("Filter values must be scalar.")

        if strategy != "C" and filters:
            raise ValueError("Only C applies metadata filters.")

        stored_strategy = "B" if strategy == "C" else strategy
        vector = self._vector_literal(query_vector)

        rows = self.connection.execute(
            """
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                text,
                metadata,
                1 - (embedding <=> %s::vector) AS score
            FROM day6_chunks
            WHERE strategy = %s
              AND metadata @> %s
            ORDER BY embedding <=> %s::vector, chunk_id
            LIMIT %s
            """,
            (
                vector,
                stored_strategy,
                Jsonb(filters),
                vector,
                top_k,
            ),
        ).fetchall()

        fields = (
            "chunk_id",
            "document_id",
            "source",
            "page",
            "text",
            "metadata",
            "score",
        )

        return [
            dict(zip(fields, row))
            for row in rows
        ]

    def versions(self) -> dict:
        return {
            "postgresql": self.connection.execute(
                "SHOW server_version"
            ).fetchone()[0],
            "pgvector": self.connection.execute(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
                """
            ).fetchone()[0],
        }