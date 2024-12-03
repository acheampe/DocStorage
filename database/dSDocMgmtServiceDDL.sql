-- PostgreSQL
-- Name: Manny Ach
-- Date: 11.26.24
-- Project: DocStorage - Document Management Service DDL

-- -----------------------------------------------------
-- Entity: Documents to support Document Management Service DB
-- -----------------------------------------------------

CREATE TABLE Documents (
    doc_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,          -- Internal filename (with timestamp)
    original_filename VARCHAR(255) NOT NULL,  -- Original filename
    file_type VARCHAR(100) NOT NULL,
    file_size INT NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
    
    -- Removed the foreign key constraint since we will be using a different database
    -- Referential integrity will be handled at the application level
);

-- Add index for faster user-based queries
CREATE INDEX idx_documents_user_id ON Documents(user_id);