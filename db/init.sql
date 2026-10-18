-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    userid SERIAL PRIMARY KEY,
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    token VARCHAR(255),
    tokenexpiredate TIMESTAMP
);

-- Create Memories Table (1-to-Many relationship with Users)[cite: 1]
CREATE TABLE IF NOT EXISTS memories (
    memoryid SERIAL PRIMARY KEY,
    userid INT NOT NULL,
    audiotranscription TEXT,
    audiofilelocation VARCHAR(500),
    imagefilelocation VARCHAR(500),
    keywords TEXT,
    gpslongitude NUMERIC(11, 8),
    gpslatitude NUMERIC(10, 8),
    timecaptured TIMESTAMP,
    CONSTRAINT fk_user
        FOREIGN KEY(userid) 
        REFERENCES users(userid)
        ON DELETE CASCADE
);
