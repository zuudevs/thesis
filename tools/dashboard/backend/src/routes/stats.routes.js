const express = require('express');
const stats = require('../services/stats.service');

const router = express.Router();

/** GET /api/stats/overview — KPI + facets untuk filter + aktivitas per hari. */
router.get('/overview', async (req, res, next) => {
	try {
		res.json(await stats.overview());
	} catch (err) {
		next(err);
	}
});

module.exports = router;