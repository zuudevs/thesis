const express = require('express');
const Run = require('../models/Run');
const Result = require('../models/Result');
const aggregate = require('../services/aggregate.service');

const router = express.Router();

function escapeRegex(s) {
	return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * GET /api/runs — daftar run (file record) dengan filter + pencarian + paginasi.
 * Query: site, kind, generator, library, corpus, engine, family, mode, scanner_mode,
 *        dirty, exploratory, from, to, q, page, pageSize, sort
 */
router.get('/', async (req, res, next) => {
	try {
		const match = {};
		if (req.query.site) match.site = req.query.site;
		if (req.query.kind) match.kind = req.query.kind;
		if (req.query.generator) match.generator = req.query.generator;
		if (req.query.library) match['library.name'] = req.query.library;
		if (req.query.corpus) match['corpus.name'] = req.query.corpus;
		if (req.query.scanner_mode) match['config.scanner_mode'] = req.query.scanner_mode;
		if (req.query.dirty === 'true') match['derived.dirty'] = true;
		if (req.query.dirty === 'false') match['derived.dirty'] = false;
		if (req.query.exploratory === 'true') match['derived.exploratory'] = true;
		if (req.query.exploratory === 'false') match['derived.exploratory'] = false;
		if (req.query.engine) {
			const arr = Array.isArray(req.query.engine) ? req.query.engine : [req.query.engine];
			match['derived.engines'] = { $in: arr };
		}
		if (req.query.family) {
			const arr = Array.isArray(req.query.family) ? req.query.family : [req.query.family];
			match['derived.families'] = { $in: arr };
		}
		if (req.query.mode) match['derived.modes'] = req.query.mode;
		if (req.query.from || req.query.to) {
			match['derived.date_utc'] = {};
			if (req.query.from) match['derived.date_utc'].$gte = new Date(req.query.from);
			if (req.query.to) match['derived.date_utc'].$lte = new Date(req.query.to);
		}
		if (req.query.q) {
			const rx = new RegExp(escapeRegex(req.query.q), 'i');
			match.$or = [
				{ run_id: rx },
				{ 'derived.names_text': rx },
				{ 'config.notes': rx },
				{ 'corpus.name': rx },
				{ 'host.hostname': rx },
			];
		}

		const page = Math.max(1, parseInt(req.query.page, 10) || 1);
		const pageSize = Math.min(200, Math.max(1, parseInt(req.query.pageSize, 10) || 25));
		const sortDir = req.query.sort === 'asc' ? 1 : -1;
		const sortField = req.query.sortBy || 'derived.date_utc';

		const [total, rows] = await Promise.all([
			Run.countDocuments(match),
			Run.find(match, { record: 0 })
				.sort({ [sortField]: sortDir })
				.skip((page - 1) * pageSize)
				.limit(pageSize)
				.lean(),
		]);

		res.json({ total, page, pageSize, rows });
	} catch (err) {
		next(err);
	}
});

/**
 * GET /api/runs/:runId — detail run_id (semua korpus) atau satu korpus
 * (?corpus=). Mengembalikan record verbatim + results.
 */
router.get('/:runId', async (req, res, next) => {
	try {
		const match = { run_id: req.params.runId };
		if (req.query.corpus) match.corpus_key = req.query.corpus;
		const runs = await Run.find(match).sort({ corpus_key: 1 }).lean();
		if (!runs.length) return res.status(404).json({ message: 'run_id tidak ditemukan' });

		const corpora = await Run.distinct('corpus_key', { run_id: req.params.runId });
		const [results, breakdown] = await Promise.all([
			Result.find(req.query.corpus ? match : { run_id: req.params.runId }).lean(),
			req.query.corpus ? aggregate.runBreakdown(req.params.runId, req.query.corpus) : Promise.resolve(null),
		]);

		res.json({ run_id: req.params.runId, corpora, runs, results, breakdown });
	} catch (err) {
		next(err);
	}
});

module.exports = router;