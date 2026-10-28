const express = require('express');
const { Pool } = require('pg');

const app = express();
const PORT = process.env.PORT || 5001;

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
  res.status(200).send('Encore Remote Backend is running!');
});

// Database connection test route
app.get('/postgresql-health', async (req, res) => {
  try {
    const result = await pool.query('SELECT NOW()');
    res.status(200).json({ success: true, time: result.rows[0].now });
  } catch (err) {
    console.error('PostgreSQL Database connection error:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Remote backend is listening on port ${PORT}`);
});
