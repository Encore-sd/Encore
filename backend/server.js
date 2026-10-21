const express = require('express');
const { Pool } = require('pg');

const app = express();
const sqlitedb = require('./db/init-sqlite');
const PORT = process.env.PORT || 5000;

// Middleware to parse JSON bodies
app.use(express.json());

// Set up PostgreSQL connection pool using environment variables from Docker Compose
const pool = new Pool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  port: process.env.DB_PORT || 5432,
});

// Basic health check route
app.get('/', (req, res) => {
  res.status(200).send('Encore Backend is running!');
});

// Database connection test route
app.get('/db-health', async (req, res) => {
  try {
    const result = await pool.query('SELECT NOW()');
    res.status(200).json({ success: true, time: result.rows[0].now });
  } catch (err) {
    console.error('Database connection error:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

// local Database sqlite connection test route
app.get('/sqlite-health', async (req, res) => {
  try {
    // Run a quick query to fetch table names from SQLite metadata
    const tables = sqlitedb.prepare("SELECT name FROM sqlite_master WHERE type='table';").all();
    
    res.status(200).json({
      status: 'healthy',
      database: 'SQLite (Local)',
      tablesFound: tables.map(t => t.name)
    });
  } catch (error) {
    res.status(500).json({
      status: 'unhealthy',
      error: error.message
    });
  }
});


app.listen(PORT, () => {
  console.log(`Server is listening on port ${PORT}`);
});
