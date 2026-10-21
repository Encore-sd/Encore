const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

// Ensure the sqlite-data directory exists inside the container
const dir = path.resolve(__dirname, '../sqlite-data');
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

// Connect to the local SQLite database file
const dbPath = path.join(dir, 'local.db');
const db = new Database(dbPath, { verbose: console.log });

// Execute the table creation script matching your ERD
db.exec(`
  CREATE TABLE IF NOT EXISTS ResolvedMemories (
      MemoryID INTEGER PRIMARY KEY AUTOINCREMENT,
      UserID INTEGER,
      RefrenceNumber TEXT,
      AudioTranscription TEXT,
      ImageFileLocation TEXT,
      GPSLongitude REAL,
      GPSLatitude REAL,
      TimeCaptured TEXT
  );

  CREATE TABLE IF NOT EXISTS UnresolvedMemories (
      MemoryID INTEGER PRIMARY KEY AUTOINCREMENT,
      UserID INTEGER,
      RefrenceNumber TEXT,
      AudioFileLocation TEXT,
      ImageFileLocation TEXT,
      GPSLongitude REAL,
      GPSLatitude REAL,
      TimeCaptured TEXT
  );
`);

console.log('SQLite tables initialized successfully!');

module.exports = db;
