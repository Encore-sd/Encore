-- Add the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    userid SERIAL PRIMARY KEY,
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    isverified BOOLEAN DEFAULT FALSE,
    verificationcode VARCHAR(10),
    createdate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	role VARCHAR(6) DEFAULT 'user'
);

-- Create Memories Table (1-to-Many relationship with Users)
CREATE TABLE IF NOT EXISTS memories (
    memoryid SERIAL PRIMARY KEY,
    userid INT NOT NULL,
    audiotranscription TEXT,
    imagefilelocation VARCHAR(500),
    gpslongitude NUMERIC(11, 8),
    gpslatitude NUMERIC(10, 8),
    timecaptured TIMESTAMP,
    embedding VECTOR(768),
    CONSTRAINT fk_user
        FOREIGN KEY(userid) 
        REFERENCES users(userid)
        ON DELETE CASCADE
);
