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

-- Table schema for Auth Service
     Column      |          Type          | Collation | Nullable |                Default                 
-----------------+------------------------+-----------+----------+----------------------------------------
 user_id         | integer                |           | not null | nextval('users_user_id_seq'::regclass)
 first_name      | character varying(255) |           | not null | 
 last_name       | character varying(255) |           | not null | 
 email           | character varying(255) |           | not null | 
 hashed_password | character varying(60)  |           | not null | 
Indexes:
    "users_pkey" PRIMARY KEY, btree (user_id)
    "users_email_key" UNIQUE CONSTRAINT, btree (email)