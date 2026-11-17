const express = require('express');
const router = express.Router();
const sqlitedb = require('../db/init-sqlite');

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;

// Prepared once and reused for every request
const countMemories = sqlitedb.prepare(
	'SELECT COUNT(*) AS total FROM ResolvedMemories WHERE UserID = ?'
);
const selectMemories = sqlitedb.prepare(`
	SELECT MemoryID, UserID, ReferenceNumber, AudioTranscription, ImageFileLocation,
	       GPSLongitude, GPSLatitude, TimeCaptured
	FROM ResolvedMemories
	WHERE UserID = ?
	ORDER BY TimeCaptured DESC, MemoryID DESC
	LIMIT ? OFFSET ?
`);

// read a query param as a positive integer, falling back to a default
function toPositiveInt(value, fallback) {
	const n = Number.parseInt(value, 10);
	if (Number.isInteger(n) && n > 0) {
		return n;
	} else {
		return fallback;
	}
}

// Get all memories for a user stored locally (users opted out of remote storage)
// GET /memories/:userId?page=1&limit=20
router.get('/:userId', (req, res) => {
	const userId = Number.parseInt(req.params.userId, 10);
	if (!Number.isInteger(userId) || userId <= 0 || String(userId) !== req.params.userId) {
		return res.status(400).json({ success: false, error: 'userId must be a positive integer' });
	}

	const page = toPositiveInt(req.query.page, 1);
	const limit = Math.min(toPositiveInt(req.query.limit, DEFAULT_LIMIT), MAX_LIMIT);
	const offset = (page - 1) * limit;

	try {
		const { total } = countMemories.get(userId);
		const memories = selectMemories.all(userId, limit, offset);
		const totalPages = Math.ceil(total / limit);

		res.status(200).json({
			success: true,
			memories,
			pagination: {
				page,
				limit,
				totalItems: total,
				totalPages,
				hasNextPage: page < totalPages,
				hasPrevPage: page > 1
			}
		});
	} catch (error) {
		res.status(500).json({ success: false, error: error.message });
	}
});

module.exports = router;
