const express = require('express');
const sqlitedb = require('./db/init-sqlite');
const PORT = process.env.PORT || 5000;

// Grab the remote backend URL from the environment variable (fallback to Docker service name)
const REMOTE_BACKEND_URL = process.env.REMOTE_BACKEND_URL || 'http://localhost:5001';

const app = express();


// Middleware to parse JSON bodies
app.use(express.json());

// Basic health check route
app.get('/', (req, res) => {
  res.status(200).send('Encore Local Backend is running!');
});

// Basic health check to make sure the remote backend is reachable by the local one
app.get('/remote-health', async (req, res) => {
  try {
    // Attempt to ping the remote backend's root health check endpoint with a timeout or standard fetch
    const response = await fetch(`${REMOTE_BACKEND_URL}/`);
    
    if (response.ok) {
      const text = await response.text();
      res.status(200).json({
        status: 'connected',
        remoteUrl: REMOTE_BACKEND_URL,
        responseMessage: text
      });
    } else {
      res.status(502).json({
        status: 'unreachable',
        remoteUrl: REMOTE_BACKEND_URL,
        error: `Remote server responded with status: ${response.status}`
      });
    }
  } catch (error) {
    // This block catches network errors (e.g., remote backend is down, or user is offline)
    res.status(503).json({
      status: 'offline',
      remoteUrl: REMOTE_BACKEND_URL,
      message: 'Could not reach remote backend. Operating in offline mode.',
      error: error.message
    });
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
  console.log(`Local backend is listening on port ${PORT}`);
});
