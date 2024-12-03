-- PostgreSQL
-- Name: Manny Ach
-- Date: 12.01.24
-- Project: DocStorage - Share Service DDL

-- -----------------------------------------------------
-- Entity: SharedDocuments to support Share Service DB
-- -----------------------------------------------------

CREATE TABLE SharedDocuments (
    share_id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,          -- User who owns/shared the document
    recipient_id INTEGER NOT NULL,       -- User who received access
    display_name VARCHAR(255) NOT NULL,  -- Current name of the document (can be updated)
    original_name VARCHAR(255) NOT NULL, -- Original name when first shared
    shared_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    expiry_date TIMESTAMP,              -- Optional expiration date for sharing
    status VARCHAR(20) NOT NULL DEFAULT 'active'  -- active, revoked, expired
);

-- Add indexes for faster queries
CREATE INDEX idx_shared_docs_owner ON SharedDocuments(owner_id);
CREATE INDEX idx_shared_docs_recipient ON SharedDocuments(recipient_id);
CREATE INDEX idx_shared_docs_doc ON SharedDocuments(doc_id);
CREATE INDEX idx_shared_docs_status ON SharedDocuments(status);
-- Add index for recipient lookup
CREATE INDEX idx_recipient_id ON SharedDocuments(recipient_id);
CREATE INDEX idx_owner_id ON SharedDocuments(owner_id);

-- Add unique constraint to prevent duplicate shares
CREATE UNIQUE INDEX idx_unique_share 
ON SharedDocuments(doc_id, owner_id, recipient_id) 
WHERE status = 'active';

-- Create view for active shares only
CREATE VIEW active_shares AS
SELECT * FROM SharedDocuments
WHERE status = 'active'
AND (expiry_date IS NULL OR expiry_date > CURRENT_TIMESTAMP);

-- Function to automatically update last_accessed
CREATE OR REPLACE FUNCTION update_last_accessed()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update last_accessed on any access
CREATE TRIGGER trigger_update_last_accessed
    BEFORE UPDATE ON SharedDocuments
    FOR EACH ROW
    WHEN (OLD.last_accessed IS DISTINCT FROM NEW.last_accessed)
    EXECUTE FUNCTION update_last_accessed();