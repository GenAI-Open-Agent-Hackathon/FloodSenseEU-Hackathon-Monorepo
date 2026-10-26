"""SQL contract for the empty rag.chunks table and the Zetaris JDBC registration."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RagSchemaTest(unittest.TestCase):
    def test_postgres_index_matches_the_spec(self) -> None:
        sql = (ROOT / "pgvector" / "migrations" / "001_rag_chunks.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE rag.chunks", sql)
        self.assertIn("embedding vector(2048)", sql)
        self.assertIn(
            "CREATE INDEX rag_chunks_embed_hnsw\n"
            "  ON rag.chunks\n"
            "  USING hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)\n"
            "  WHERE level = 'paragraph' AND embedding IS NOT NULL;",
            sql,
        )
        self.assertIn("embedding::halfvec(2048) <=> $1::halfvec(2048)", sql)
        self.assertIn("ORDER BY embedding <=> $1::vector", sql)
        self.assertNotIn("nvapi-", sql)

    def test_zetaris_registration_keeps_the_password_placeholder(self) -> None:
        sql = (ROOT / "zetaris" / "migrations" / "044_register_pgvector_rag_chunks.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn('password "${PGVECTOR_PASSWORD}"', sql)
        self.assertIn('REGISTER DATASOURCE TABLE "chunks" FROM PGVECTOR_RAG', sql)
        self.assertIn('schema "rag"', sql)
        self.assertNotIn("<=>", sql)
        self.assertNotIn("<->", sql)
        self.assertNotIn("local-dev-only", sql)
        self.assertNotIn("nvapi-", sql)


if __name__ == "__main__":
    unittest.main()
