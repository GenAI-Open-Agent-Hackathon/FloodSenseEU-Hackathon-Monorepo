-- Apply to the rag-profile Postgres on 127.0.0.1:15432. Not a Zetaris file.
-- The password stays in pgvector/.env. This file has no password.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE rag.chunks (
  chunk_id text PRIMARY KEY,
  parent_chunk_id text REFERENCES rag.chunks (chunk_id),
  path text NOT NULL,
  level text NOT NULL CHECK (level IN ('doc', 'page', 'section', 'paragraph')),
  doc_id text NOT NULL,
  tier smallint NOT NULL CHECK (tier IN (1, 2, 3)),
  event_id text,
  title text NOT NULL,
  source_url text NOT NULL,
  publisher text NOT NULL,
  licence text NOT NULL,
  attribution text NOT NULL,
  page integer,
  paragraph integer,
  lines text,
  section text,
  text text NOT NULL,
  text_sha256 text NOT NULL,
  embedding vector(2048),
  embed_model text,
  CONSTRAINT rag_chunks_embed_model CHECK (
    (embedding IS NULL AND embed_model IS NULL)
    OR (
      embedding IS NOT NULL
      AND level = 'paragraph'
      AND embed_model IS NOT NULL
      AND embed_model = 'nvidia/llama-nemotron-embed-1b-v2'
    )
  ),
  CONSTRAINT rag_chunks_paragraph_locator CHECK (
    level <> 'paragraph'
    OR (
      page IS NOT NULL AND page >= 1
      AND paragraph IS NOT NULL AND paragraph >= 1
      AND lines IS NOT NULL AND lines <> ''
    )
  )
);

CREATE INDEX rag_chunks_embed_hnsw
  ON rag.chunks
  USING hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)
  WHERE level = 'paragraph' AND embedding IS NOT NULL;

-- search (Postgres only, not Zetaris):
-- SELECT chunk_id, (embedding::halfvec(2048) <=> $1::halfvec(2048)) AS distance
-- FROM rag.chunks
-- WHERE level = 'paragraph'
--   AND embedding IS NOT NULL
--   AND ($2::text IS NULL OR event_id = $2)
-- ORDER BY embedding::halfvec(2048) <=> $1::halfvec(2048)
-- LIMIT $3;
--
-- fallback if the installed pgvector refuses the halfvec index:
-- SELECT chunk_id, (embedding <=> $1::vector) AS distance
-- FROM rag.chunks
-- WHERE level = 'paragraph'
--   AND embedding IS NOT NULL
--   AND ($2::text IS NULL OR event_id = $2)
-- ORDER BY embedding <=> $1::vector
-- LIMIT $3;
