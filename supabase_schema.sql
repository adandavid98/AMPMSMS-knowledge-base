-- AMPM Service POS Assistant - Supabase pgvector Schema Setup (768-dim Google Embeddings)
-- Paste and run this script in the Supabase SQL Editor (https://supabase.com)

-- 1. Enable the pgvector extension to work with embedding vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Safely backup existing documents table if it exists (Zero data loss)
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'documents') THEN
    DROP TABLE IF EXISTS documents_backup_384 CASCADE;
    ALTER TABLE documents RENAME TO documents_backup_384;
  END IF;
END $$;

-- 3. Create the documents table for storing POS help topic chunks (768-dim Google text-embedding-004)
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  embedding VECTOR(768) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Create HNSW Vector Index for fast sub-millisecond similarity queries
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx 
ON documents 
USING hnsw (embedding vector_cosine_ops);

-- 5. Create GIN Index on metadata for instant category & topic filtering
CREATE INDEX IF NOT EXISTS documents_metadata_gin_idx 
ON documents 
USING gin (metadata);

-- 6. Consolidated Hybrid Search Function (Vector + Keyword Search in 1 DB Round-Trip)
CREATE OR REPLACE FUNCTION match_documents_hybrid (
  query_embedding VECTOR(768),
  query_text TEXT DEFAULT '',
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
  id TEXT,
  text TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH vector_matches AS (
    SELECT
      d.id,
      d.text,
      d.metadata,
      (1 - (d.embedding <=> query_embedding))::FLOAT AS similarity
    FROM documents d
    WHERE
      (filter IS NULL OR filter = '{}'::jsonb OR d.metadata @> filter)
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count * 2
  ),
  keyword_matches AS (
    SELECT
      d.id,
      d.text,
      d.metadata,
      0.95::FLOAT AS similarity
    FROM documents d
    WHERE
      (filter IS NULL OR filter = '{}'::jsonb OR d.metadata @> filter)
      AND query_text IS NOT NULL AND query_text <> ''
      AND (
        d.text ILIKE '%' || query_text || '%'
        OR d.metadata->>'file_name' ILIKE '%' || query_text || '%'
        OR d.metadata->>'topic_title' ILIKE '%' || query_text || '%'
      )
    LIMIT match_count
  ),
  combined AS (
    SELECT * FROM vector_matches
    UNION ALL
    SELECT * FROM keyword_matches
  )
  SELECT * FROM (
    SELECT DISTINCT ON (c.id)
      c.id,
      c.text,
      c.metadata,
      c.similarity
    FROM combined c
    ORDER BY c.id, c.similarity DESC
  ) sub
  ORDER BY sub.similarity DESC
  LIMIT match_count;
END;
$$;

-- 7. Standard Vector Match Function (Fallback / Direct Vector Query)
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding VECTOR(768),
  match_count INT DEFAULT 5,
  filter JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
  id TEXT,
  text TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.text,
    documents.metadata,
    (1 - (documents.embedding <=> query_embedding))::FLOAT AS similarity
  FROM documents
  WHERE
    (filter IS NULL OR filter = '{}'::jsonb OR documents.metadata @> filter)
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 6. Create ticket_feedback table for tracking technician ratings and resolved field fixes
CREATE TABLE IF NOT EXISTS ticket_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  provider TEXT,
  feedback_type TEXT NOT NULL, -- 'thumbs_up', 'thumbs_down', 'resolved'
  category TEXT,
  user_email TEXT,
  notes TEXT
);

