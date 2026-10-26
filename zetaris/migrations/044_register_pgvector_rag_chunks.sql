-- JDBC registration of rag.chunks. Password stays a placeholder.
-- PGVECTOR_PASSWORD must match POSTGRES_PASSWORD in pgvector/.env.
-- Agents must not send the cosine or L2 distance operators to Zetaris. Ranking stays in Postgres.
CREATE DATASOURCE PGVECTOR_RAG DESCRIBE BY "pgvector rag chunks" OPTIONS (
  jdbcdriver "org.postgresql.Driver",
  jdbcurl "jdbc:postgresql://host.docker.internal:15432/floodsense",
  username "floodsense",
  password "${PGVECTOR_PASSWORD}",
  schema "rag"
)
-- statement
REGISTER DATASOURCE TABLE "chunks" FROM PGVECTOR_RAG
