const express = require('express');
const router = express.Router();
const sqlitedb = require('../db/init-sqlite');

// Grab the remote backend URL from the environment variable (fallback to Docker service name)
const REMOTE_BACKEND_URL = process.env.REMOTE_BACKEND_URL || 'http://backend-remote:5001';

// Local SQLite connection health check route
router.get('/sqlite', async (req, res) => {
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

// Basic health check to make sure the remote backend is reachable by the local one
router.get('/remote', async (req, res) => {
	try {
		// Attempt to ping the remote backend's root health check endpoint
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

module.exports = router;
