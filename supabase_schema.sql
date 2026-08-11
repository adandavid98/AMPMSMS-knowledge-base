-- AMPM Service POS Assistant - Supabase pgvector Schema Setup (384-dim ONNX embeddings)
-- Paste and run this script in the Supabase SQL Editor (https://supabase.com)

-- 1. Enable the pgvector extension to work with embedding vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Drop table if exists to recreate with 384 dimensions
DROP TABLE IF EXISTS documents CASCADE;

-- 3. Create the documents table for storing POS help topic chunks (384-dim ONNX)
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  embedding VECTOR(384) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Create HNSW Vector Index for fast sub-millisecond similarity queries
CREATE INDEX documents_embedding_hnsw_idx 
ON documents 
USING hnsw (embedding vector_cosine_ops);

-- 5. Create RPC Match Function for Vector Cosine Similarity Search
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding VECTOR(384),
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

