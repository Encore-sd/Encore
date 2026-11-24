const express = require('express');
const router = express.Router();
const authenticateToken = require('../middleware/auth');

// The dimension that the query vector is. Must match the dimension in the database
const vectorDim = 768;

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

	router.post('/retriever/:userId', authenticateToken, async (req, res) => {

		// Verify the caller is an AI service account
		const aiUserId = req.user.userId;
		try {
			const aiUser = await pool.query(
				`SELECT role FROM users WHERE userid = $1 LIMIT 1`,
				[aiUserId]
			);

			if(aiUser.rows.length === 0){
				return res.status(404).json({
					success: false,
					message: 'user not found.'
				});
			} else if(aiUser.rows[0].role !== 'ai'){
				return res.status(403).json({
					success: false,
					message: 'Access denied, must be AI.'
				});
			}
		} catch (error) {
			return res.status(500).json({
					success: false,
					message: 'Internal Server Error.',
					error: error.message
				});
		}


		const requestedUserId = parseInt(req.params.userId, 10);

		if(isNaN(requestedUserId)) {
			return res.status(404).json({
				success: false,
				message: 'Invalid userId.'
			});
		}

		// Verify K is a valid value
		const parsedK = parseInt(req.body.k, 10);
		if(isNaN(parsedK) || parsedK < 1) {
			return res.status(400).json({
				success: false,
				message: 'paramater k must be a positive integer.'
			});
		}
		const k = Math.min(100, parsedK);

		// Verify the query vector is valid
		const { queryVector } = req.body;
		let formattedVector = null;

		if(Array.isArray(queryVector)) {
			if (
				queryVector.length !== vectorDim || 
				!queryVector.every((val) => typeof val === 'number' && Number.isFinite(val))
			) {
				return res.status(400).json({
					success: false,
					message: `queryVector must be an array of ${vectorDim} finite numbers (received length ${queryVector.length}).`
				});
			}
			formattedVector = `[${queryVector.join(',')}]`;
		} else if (typeof queryVector === 'string' && queryVector.trim().length > 0) {
			formattedVector = queryVector.trim();
		} else {
			return res.status(400).json({
				success: false,
				message: `queryVector is required and must be ${vectorDim}-element number array.`
			});
		}

		// Query pgvector for the k closest memories belonging to requestedUserId
		try {
			const retrieverQuery = `
				SELECT
					memoryid,
					userid,
					audiotranscription,
					imagefilelocation,
					gpslongitude,
					gpslatitude,
					timecaptured,
					(embedding <=> $2::vector) AS distance
				FROM memories
				WHERE userid=$1 AND embedding IS NOT NULL ORDER BY embedding <=> $2::vector ASC
				LIMIT $3;
			`;

			const result = await pool.query(retrieverQuery, [
				requestedUserId,
				formattedVector,
				k
			]);

			return res.status(200).json({
				success: true,
				userId: requestedUserId,
				k: k,
				count: result.rows.length,
				memories: result.rows
			});
		} catch (error) {
			return res.status(500).json({
				success: false,
				message: 'Internal Server Error during vector retrival.',
				error: error.message
			});
		}

	});

	return router;
};
