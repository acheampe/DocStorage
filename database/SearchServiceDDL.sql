-- PostgreSQL
-- Name: Manny Ach
-- Date: 11.30.24
-- Project: DocStorage - Search Service DDL

-- Create table with correct schema
CREATE TABLE DocumentIndex (
    index_id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL,
    content_text TEXT,
    doc_metadata JSONB,  -- Changed from metadata to doc_metadata
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(doc_metadata->>'filename', '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(content_text, '')), 'B')
    ) STORED
);

-- Create indexes
CREATE INDEX idx_document_search ON DocumentIndex USING GIN (search_vector);
CREATE INDEX idx_doc_id ON DocumentIndex (doc_id);

-- Create timestamp update function
CREATE OR REPLACE FUNCTION update_last_indexed()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_indexed = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER trigger_update_last_indexed
    BEFORE UPDATE ON DocumentIndex
    FOR EACH ROW
    EXECUTE FUNCTION update_last_indexed();

-- Create a new migration file (e.g., migrations/versions/xxx_update_search_vector.py)
ALTER TABLE documentindex DROP COLUMN search_vector;
ALTER TABLE documentindex ADD COLUMN search_vector tsvector 
    GENERATED ALWAYS AS (
        to_tsvector('english', 
            coalesce(content_text, '') || ' ' || 
            coalesce(doc_metadata->>'filename', '') || ' ' || 
            coalesce(doc_metadata->>'description', '')
        )
    ) STORED;

-- Drop existing table and recreate with generated column
DROP TABLE IF EXISTS documentindex;

CREATE TABLE documentindex (
    index_id SERIAL PRIMARY KEY,
    doc_id INTEGER UNIQUE NOT NULL,
    content_text TEXT DEFAULT '',
    doc_metadata JSONB DEFAULT '{}',
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(content_text, '') || ' ' ||
            coalesce(doc_metadata->>'filename', '') || ' ' ||
            coalesce(doc_metadata->>'description', '')
        )
    ) STORED
);

CREATE INDEX idx_document_search ON documentindex USING gin(search_vector);

-- Drop the existing table
DROP TABLE IF EXISTS documentindex CASCADE;

-- Recreate the table with the updated search vector
CREATE TABLE documentindex (
    index_id SERIAL PRIMARY KEY,
    doc_id INTEGER UNIQUE NOT NULL,
    content_text TEXT DEFAULT '',
    doc_metadata JSONB DEFAULT '{}',
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(content_text, '') || ' ' ||
            regexp_replace(coalesce(doc_metadata->>'filename', ''), '[_.]', ' ', 'g') || ' ' ||
            coalesce(doc_metadata->>'description', '')
        )
    ) STORED
);

-- Recreate the search index
CREATE INDEX idx_document_search ON documentindex USING gin(search_vector);