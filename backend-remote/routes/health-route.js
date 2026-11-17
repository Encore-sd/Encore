const express = require('express');
const router = express.Router();

// We export a function that accepts the 'pool' so the route has access to it
module.exports = (pool) => {
	// Database connection test route
	router.get('/postgresql', async (req, res) => {
		try {
			const result = await pool.query('SELECT NOW()');
			res.status(200).json({ success: true, time: result.rows[0].now });
		} catch (err) {
			console.error('PostgreSQL Database connection error:', err);
			res.status(500).json({ success: false, error: err.message });
		}
	});

	return router;
};
