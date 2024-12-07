-- PostgreSQL
-- Name: Manny Ach
-- Date: 11.30.24
-- Project: DocStorage - Search Service DDL

-- Create table with correct schema
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

-- Update the insert statement to exclude search_vector
CREATE OR REPLACE FUNCTION insert_document(
    p_doc_id INTEGER,
    p_content_text TEXT,
    p_doc_metadata JSONB
) RETURNS TABLE (
    index_id INTEGER,
    last_indexed TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    INSERT INTO documentindex (
        doc_id,
        content_text,
        doc_metadata
    ) VALUES (
        p_doc_id,
        p_content_text,
        p_doc_metadata
    )
    RETURNING documentindex.index_id, documentindex.last_indexed;
END;
$$ LANGUAGE plpgsql;

-- Recreate the search index
CREATE INDEX idx_document_search ON documentindex USING gin(search_vector);


-- Table schema for Search Service                                                         
---------------+-----------------------------+-----------+----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 index_id      | integer                     |           | not null | nextval('documentindex_index_id_seq'::regclass)
 doc_id        | integer                     |           | not null | 
 content_text  | text                        |           |          | ''::text
 doc_metadata  | jsonb                       |           |          | '{}'::jsonb
 last_indexed  | timestamp without time zone |           |          | CURRENT_TIMESTAMP
 search_vector | tsvector                    |           |          | generated always as (to_tsvector('english'::regconfig, (((COALESCE(content_text, ''::text) || ' '::text) || regexp_replace(COALESCE(doc_metadata ->> 'filename'::text, ''::text), '[_.]'::text, ' '::text, 'g'::text)) || ' '::text) || COALESCE(doc_metadata ->> 'description'::text, ''::text))) stored
Indexes:
    "documentindex_pkey" PRIMARY KEY, btree (index_id)
    "documentindex_doc_id_key" UNIQUE CONSTRAINT, btree (doc_id)
    "idx_document_search" gin (search_vector)
