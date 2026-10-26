-- nvidia/llama-nemotron-embed-1b-v2 reached end of life on NVIDIA NIM on 2026-08-25 (HTTP 410).
-- nvidia/nemotron-3.5-embed-1b answers the same request at 2048 dimensions, so the column and index stay.
-- Rows embedded with the old model would not rank against new query vectors, so they are removed first.
DELETE FROM rag.chunks WHERE embed_model = 'nvidia/llama-nemotron-embed-1b-v2';

ALTER TABLE rag.chunks DROP CONSTRAINT rag_chunks_embed_model;

ALTER TABLE rag.chunks ADD CONSTRAINT rag_chunks_embed_model CHECK (
  (embedding IS NULL AND embed_model IS NULL)
  OR (
    embedding IS NOT NULL
    AND level = 'paragraph'
    AND embed_model IS NOT NULL
    AND embed_model = 'nvidia/nemotron-3.5-embed-1b'
  )
);
