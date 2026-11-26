const express = require('express');
const compareService = require('../services/compare.service');

const router = express.Router();

/**
 * POST /api/compare
 * body: { items: [{ run_id, corpus_key, name }, ...] }
 * → rows + speedup vs referensi + guardrail checks (blok lintas
 *   run_id/site/kind/korpus).
 */
router.post('/', async (req, res, next) => {
	try {
		res.json(await compareService.compare(req.body.items || req.body));
	} catch (err) {
		next(err);
	}
});

module.exports = router;