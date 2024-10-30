-- PostgreSQL
-- Name: Manny Ach
-- Date: 08.29.24
-- Project: DocStorage - Auth Service DDL

-- -----------------------------------------------------
-- Entity: Users to support Auth Service DB
-- -----------------------------------------------------

CREATE TABLE Users (

    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(60) NOT NULL
    
);