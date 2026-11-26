const express = require('express');
const aggregate = require('../services/aggregate.service');

const router = express.Router();

/** GET /api/charts/trend?metric=&site=&corpus=&engine=&... — tren throughput harian. */
router.get('/trend', async (req, res, next) => {
	try {
		res.json(await aggregate.throughputTrend(req.query));
	} catch (err) {
		next(err);
	}
});

/** GET /api/charts/acceptance?threshold=1.5&site=&... — panel + tren speedup. */
router.get('/acceptance', async (req, res, next) => {
	try {
		res.json(await aggregate.acceptancePanel(req.query));
	} catch (err) {
		next(err);
	}
});

/** GET /api/charts/scanner?site=&corpus= — mode scanner dalam run 'multi'. */
router.get('/scanner', async (req, res, next) => {
	try {
		res.json(await aggregate.scannerPanel(req.query));
	} catch (err) {
		next(err);
	}
});

module.exports = router;