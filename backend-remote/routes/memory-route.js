const express = require('express');
const router = express.Router();
const authenticateToken = require('../middleware/auth');

module.exports = (pool) => {

	// Insert a single memorie's details without sending it to the AI
	router.post('/insert/:userId', authenticateToken, async (req, res) => {
	});

	//[baseUrl]/userId?limit=20&offset=0
	router.get('/:userId', authenticateToken, async (req, res) => {
		const requestedUserId = parseInt(req.params.userId, 10);
		const authenticatedUserId = req.user.userId;

		if(isNaN(requestedUserId) || requestedUserId !== authenticatedUserId) {
			return res.status(403).json({
				success: false,
				message: 'Access denied.'
			});
		}
		
		const limit = Math.min(100, Math.max(1, parseInt(req.query.limit, 10) || 20));
		const offset = Math.max(0, parseInt(req.query.offset, 10) || 0);

		try {
			const [memoriesResult, countResult] = await Promise.all([
				pool.query(
					`SELECT memoryid, audiotranscription, imagefilelocation FROM memories
					WHERE userid = $1
					ORDER BY timecaptured DESC
					LIMIT $2 OFFSET $3`,
					[requestedUserId, limit, offset]
				),
				pool.query(
					'SELECT COUNT(*) FROM memories WHERE userid = $1',
					[requestedUserId]
				)
			]);

			const totalItems = parseInt(countResult.rows[0].count, 10);
			const currentPage = Math.floor(offset / limit) + 1;
			const totalPages = Math.ceil(totalItems / limit);

			return res.status(200).json({
				success: true,
				memories: memoriesResult.rows,
				pagination: {
					limit: limit,
					offset: offset,
					currentPage: currentPage,
					totalItems: totalItems,
					totalPages: totalPages,
					hasNextPage: offset + limit < totalItems,
					hasPreviousPage: offset > 0
				}
			});

		} catch (error) {
			return res.status(500).json({
				success: false,
				message: 'Error fetching memories',
				error: error.message
			});
		}
	});

	router.get('/:userId/:memoryId', authenticateToken, async (req, res) => {
		const requestedUserId = parseInt(req.params.userId, 10);
		const authenticatedUserId = req.user.userId;

		if(isNaN(requestedUserId) || requestedUserId !== authenticatedUserId) {
			return res.status(403).json({
				success: false,
				message: 'Access denied.'
			});
		}

		try {
			const memory = await pool.query(
				`SELECT memoryid, audiotranscription, imagefilelocation, gpslongitude, gpslatitude, timecaptured FROM memories
				WHERE userid = $1 AND memoryid = $2
				LIMIT 1`,
				[requestedUserId, parseInt(req.params.memoryId, 10)]
			);

			if(memory.rows.length > 0){
				return res.status(200).json({
					success: true,
					memory: memory.rows[0]
				});
			} else {
				return res.status(404).json({
					success: false,
					message: 'Memory not found'
				});

			}

		} catch (error) {
			return res.status(500).json({
				success: false,
				message: 'Error fetching memory',
				error: error.message
			});
		}

	});

	router.delete('/:userId/:memoryId', authenticateToken, async (req, res) => {
		const requestedUserId = parseInt(req.params.userId, 10);
		const authenticatedUserId = req.user.userId;

		if(isNaN(requestedUserId) || requestedUserId !== authenticatedUserId) {
			return res.status(403).json({
				success: false,
				message: 'Access denied.'
			});
		}

		try {
			const memory = await pool.query(
				`DELETE FROM memories WHERE userid = $1 AND memoryid = $2`,
				[requestedUserId, parseInt(req.params.memoryId, 10)]
			);

			return res.status(200).json({
				success: true,
			});

		} catch (error) {
			return res.status(500).json({
				success: false,
				message: 'Error deleting memory',
				error: error.message
			});
		}

	});


	return router;
};
