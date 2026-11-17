const express = require('express');
const router = express.Router();
const authenticateToken = require('../middleware/auth');

module.exports = (pool) => {
	router.post('/', authenticateToken, async (req, res) => {
		const { query } = req.body;
		const userId = req.user.userId;

		if (!query) {
			return res.status(400).json({ success: false, message: 'Query test is required.'})
		}

		try {
			// *************Eventually the query will be sent to the AI here *********************
			return res.status(200).json({
				success: true,
				message: 'Query recived successfully.',
				userId: userId,
				query: query
			});
		} catch (error) {
			return res.status(500).json({ success: false, message: 'Internal server error.', error: error.message });
		}
	});
	return router;
};
