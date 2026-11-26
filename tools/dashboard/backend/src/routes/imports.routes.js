const express = require('express');
const ingest = require('../services/ingest.service');

const router = express.Router();

/** POST /api/imports/scan — pindai out/measurements & upsert ke MongoDB. */
router.post('/scan', async (req, res, next) => {
	try {
		const summary = await ingest.scanAndImport({ dir: req.query.dir, prune: req.query.prune === 'true' });
		res.json(summary);
	} catch (err) {
		err.status = err.status || 400;
		next(err);
	}
});

/** GET /api/imports/status — folder, waktu import terakhir, hitungan koleksi. */
router.get('/status', async (req, res, next) => {
	try {
		res.json(await ingest.importStatus());
	} catch (err) {
		next(err);
	}
});

/** GET /api/imports/invalid — record yang gagal validasi schema. */
router.get('/invalid', async (req, res, next) => {
	try {
		res.json({ rows: await ingest.listInvalid() });
	} catch (err) {
		next(err);
	}
});

module.exports = router;