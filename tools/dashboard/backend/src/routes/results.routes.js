const express = require('express');
const Result = require('../models/Result');

const router = express.Router();

function escapeRegex(s) {
	return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const ALLOWED_SORTS = {
	date: 'date_utc',
	seconds: 'metrics.seconds_mean',
	bytes: 'metrics.bytes_per_second',
	docs: 'metrics.documents_per_second',
	items: 'metrics.items_per_second',
};

/**
 * GET /api/results — cari result lintas run.
 * Query: site, kind, generator, library, corpus, engine, family, action, mode,
 *        status, dirty, exploratory, from, to, q, page, pageSize, sort
 */
router.get('/', async (req, res, next) => {
	try {
		const match = {};
		const eq = (key, field) => {
			if (req.query[key]) match[field] = Array.isArray(req.query[key]) ? { $in: req.query[key] } : req.query[key];
		};
		eq('site', 'site');
		eq('kind', 'kind');
		eq('generator', 'generator');
		eq('library', 'library_name');
		eq('corpus', 'corpus_name');
		eq('engine', 'engine');
		eq('family', 'family');
		eq('action', 'action');
		eq('mode', 'mode');
		eq('status', 'status');
		if (req.query.dirty === 'true') match.dirty = true;
		if (req.query.dirty === 'false') match.dirty = false;
		if (req.query.exploratory === 'true') match.exploratory = true;
		if (req.query.exploratory === 'false') match.exploratory = false;
		if (req.query.from || req.query.to) {
			match.date_utc = {};
			if (req.query.from) match.date_utc.$gte = new Date(req.query.from);
			if (req.query.to) match.date_utc.$lte = new Date(req.query.to);
		}
		if (req.query.q) {
			const rx = new RegExp(escapeRegex(req.query.q), 'i');
			match.$or = [{ name: rx }, { purpose: rx }, { run_id: rx }];
		}

		const page = Math.max(1, parseInt(req.query.page, 10) || 1);
		const pageSize = Math.min(200, Math.max(1, parseInt(req.query.pageSize, 10) || 25));
		const sortDir = req.query.sortDir === 'asc' ? 1 : -1;
		const sortField = ALLOWED_SORTS[req.query.sort] || 'date_utc';

		const [total, rows] = await Promise.all([
			Result.countDocuments(match),
			Result.find(match).sort({ [sortField]: sortDir }).skip((page - 1) * pageSize).limit(pageSize).lean(),
		]);

		res.json({ total, page, pageSize, rows });
	} catch (err) {
		next(err);
	}
});

module.exports = router;