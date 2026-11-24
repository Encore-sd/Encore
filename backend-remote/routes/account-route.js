const express = require('express');
const router = express.Router();
const authenticateToken = require('../middleware/auth');

module.exports = (pool) => {

	// Insert a single memorie's details without sending it to the AI
	router.delete('/:userId', authenticateToken, async (req, res) => {
		const requestedUserId = parseInt(req.params.userId, 10);
		const authenticatedUserId = req.user.userId;

		if(isNaN(requestedUserId) || requestedUserId !== authenticatedUserId) {
			return res.status(403).json({
				success: false,
				message: 'Access denied.'
			});
		}

		// set-up the database client
		const client = await pool.connect();

		try {
			
			//start the sql query
			await client.query('BEGIN');

			//Delete the user's memories
			const deleteMemoryResult = await pool.query(`DELETE FROM memories WHERE userid=$1 RETURNING memoryid`, [requestedUserId]);

			//Delete the user's account
			const deleteUserResult = await pool.query(`DELETE FROM users WHERE userid=$1 RETURNING userid`, [requestedUserId]);

			if (deleteUserResult.rowCount === 0) {
				// revert the changes the query made
				await client.query('ROLLBACK');
				return res.status(404).json({
					success: false,
					message: 'User not found.'
				});
			}

			// commit the changes the query makes
			await client.query('COMMIT');

			return res.status(200).json({
				success: true,
				memories: deleteMemoryResult.rows,
				userId: deleteUserResult.rows[0].userid,
				message: 'account deleted successfully.'
			});

		} catch (error) {
			return res.status(500).json({
				success: false,
				message: 'Internal server error.',
				error: error.message
			});
		} finally {
			// release the database client
			client.release();
		}

	});

	return router;

};
