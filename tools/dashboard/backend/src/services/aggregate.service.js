const Result = require('../models/Result');

/**
 * Aggregate service — kueri agregasi untuk chart & panel progress.
 * Semua kueri hanya menghitung speedup DALAM satu run_id (site & korpus sama),
 * sesuai AGENTS.md §4: bukti = speedup dalam satu run_id per site.
 */
const ALLOWED_METRICS = [
	'bytes_per_second',
	'documents_per_second',
	'items_per_second',
	'seconds_mean',
	'cpu_seconds',
];

function buildMatch(q) {
	const match = {};
	if (q.site) match.site = q.site;
	if (q.kind) match.kind = q.kind;
	if (q.generator) match.generator = q.generator;
	if (q.library) match.library_name = q.library;
	if (q.corpus) match.corpus_name = q.corpus;
	if (q.engine) match.engine = Array.isArray(q.engine) ? { $in: q.engine } : q.engine;
	if (q.family) match.family = Array.isArray(q.family) ? { $in: q.family } : q.family;
	if (q.action) match.action = Array.isArray(q.action) ? { $in: q.action } : q.action;
	if (q.status) match.status = q.status;
	if (q.dirty !== undefined && q.dirty !== '') match.dirty = q.dirty === true || q.dirty === 'true';
	if (q.exploratory !== undefined && q.exploratory !== '') match.exploratory = q.exploratory === true || q.exploratory === 'true';
	if (q.mode) match.mode = q.mode;
	return match;
}

async function throughputTrend(q = {}) {
	const metric = ALLOWED_METRICS.includes(q.metric) ? q.metric : 'bytes_per_second';
	const match = buildMatch(q);
	if (q.from || q.to) {
		match.date_utc = {};
		if (q.from) match.date_utc.$gte = new Date(q.from);
		if (q.to) match.date_utc.$lte = new Date(q.to);
	}
	const dayKey = { $dateToString: { format: '%Y-%m-%d', date: '$date_utc' } };
	const rows = await Result.aggregate([
		{ $match: match },
		{ $addFields: { day: dayKey } },
		{
			$group: {
				_id: { name: '$name', day: '$day' },
				value: { $avg: `$metrics.${metric}` },
				seconds_mean: { $avg: '$metrics.seconds_mean' },
				run_id: { $first: '$run_id' },
				site: { $first: '$site' },
				corpus_name: { $first: '$corpus_name' },
				engine: { $first: '$engine' },
				count: { $sum: 1 },
			},
		},
		{ $sort: { '_id.day': 1 } },
	]);
	// Bentuk seri per nama result; titik = rata-rata harian (median antar run).
	const seriesMap = new Map();
	for (const row of rows) {
		const key = row._id.name;
		if (!seriesMap.has(key)) seriesMap.set(key, { key, meta: { engine: row.engine, corpus: row.corpus_name, site: row.site }, points: [] });
		seriesMap.get(key).points.push({ date: row._id.day, value: row.value, seconds_mean: row.seconds_mean, run_id: row.run_id });
	}
	return { metric, series: [...seriesMap.values()] };
}

/** Kunci subjek: normalisasi nama agar pasangan baseline/candidate bertemu. */
function subjectKey(item) {
	return String(item.name || '')
		.toLowerCase()
		.replace(/@.*/g, '')
		.replace(/v8|ze-wasm64|wasm64|wasm64_cabi|wasm|ze/gi, '')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

function isBaseline(item) {
	return item.engine === 'v8' || item.family === 'v8';
}

/**
 * Panel acceptance: ambil semua pasangan (baseline v8 vs candidate) DALAM satu
 * run_id + korpus (aturan bukti AGENTS.md §4), hitung speedup = t_baseline /
 * t_candidate, lalu tampilkan run TERBARU per (site, family, subjek, korpus).
 */
async function acceptancePanel(q = {}) {
	const threshold = Number(q.threshold) || 1.5;
	const match = buildMatch(q);
	if (q.from || q.to) {
		match.date_utc = {};
		if (q.from) match.date_utc.$gte = new Date(q.from);
		if (q.to) match.date_utc.$lte = new Date(q.to);
	}
	const rows = await Result.find(match)
		.select('run_id corpus_key name family action subject engine metrics.seconds_mean metrics.bytes_per_second metrics.documents_per_second site kind corpus_name date_utc dirty exploratory git_hash library_runtime')
		.lean();

	const groups = new Map();
	for (const r of rows) {
		const key = `${r.run_id}::${r.corpus_key}`;
		if (!groups.has(key)) groups.set(key, []);
		groups.get(key).push(r);
	}

	const pairs = [];
	for (const items of groups.values()) {
		const baselines = items.filter(isBaseline);
		const candidates = items.filter((i) => !isBaseline(i) && i.metrics && i.metrics.seconds_mean);
		for (const base of baselines) {
			const baseKey = subjectKey(base);
			for (const cand of candidates) {
				if (subjectKey(cand) !== baseKey) continue;
				if (!base.metrics || !base.metrics.seconds_mean) continue;
				const speedup = base.metrics.seconds_mean / cand.metrics.seconds_mean;
				pairs.push({
					run_id: base.run_id,
					corpus_key: base.corpus_key,
					date_utc: base.date_utc,
					site: base.site,
					kind: base.kind,
					corpus_name: base.corpus_name,
					family: base.family,
					subject_key: baseKey,
					dirty: base.dirty,
					exploratory: base.exploratory,
					git_hash: base.git_hash,
					runtime_label: base.library_runtime,
					baseline: {
						name: base.name,
						engine: base.engine,
						seconds_mean: base.metrics.seconds_mean,
						bytes_per_second: base.metrics.bytes_per_second || null,
					},
					candidate: {
						name: cand.name,
						engine: cand.engine,
						seconds_mean: cand.metrics.seconds_mean,
						bytes_per_second: cand.metrics.bytes_per_second || null,
					},
					speedup,
					status: speedup >= threshold ? 'tercapai' : 'belum',
				});
			}
		}
	}

	// Terbaru per (site, family, subjek, korpus).
	const latest = new Map();
	for (const p of pairs.sort((a, b) => new Date(a.date_utc) - new Date(b.date_utc))) {
		const key = [p.site, p.family, p.subject_key, p.corpus_name, p.candidate.engine].join('|');
		latest.set(key, p);
	}

	// Tren speedup (semua pasangan, kronologis) untuk chart progress.
	const trend = pairs
		.sort((a, b) => new Date(a.date_utc) - new Date(b.date_utc))
		.map((p) => ({
			date: p.date_utc,
			run_id: p.run_id,
			site: p.site,
			family: p.family,
			corpus_name: p.corpus_name,
			subject_key: p.subject_key,
			candidate_engine: p.candidate.engine,
			speedup: p.speedup,
			status: p.status,
			dirty: p.dirty,
			exploratory: p.exploratory,
		}));

	return { threshold, count: pairs.length, latest: [...latest.values()], trend };
}

/** Perbandingan mode scanner dalam run 'multi' (structural/scanner8/64/128/reference). */
async function scannerPanel(q = {}) {
	const match = buildMatch(q);
	match.mode = { $ne: null };
	const rows = await Result.find(match)
		.select('run_id name family action subject engine mode metrics.bytes_per_second metrics.seconds_mean site corpus_name date_utc')
		.lean();
	const byRun = new Map();
	for (const r of rows) {
		const key = `${r.run_id}::${r.corpus_key}`;
		if (!byRun.has(key)) byRun.set(key, { run_id: r.run_id, site: r.site, corpus_name: r.corpus_name, date_utc: r.date_utc, modes: [] });
		byRun.get(key).modes.push({
			mode: r.mode,
			name: r.name,
			bytes_per_second: (r.metrics && r.metrics.bytes_per_second) || null,
			seconds_mean: (r.metrics && r.metrics.seconds_mean) || null,
		});
	}
	return { runs: [...byRun.values()].sort((a, b) => new Date(b.date_utc) - new Date(a.date_utc)) };
}

/** Throughput antar-engine dalam satu run (untuk run detail chart). */
async function runBreakdown(runId, corpusKey) {
	const query = { run_id: runId };
	if (corpusKey) query.corpus_key = corpusKey;
	const rows = await Result.find(query)
		.select('name engine metrics.bytes_per_second metrics.seconds_mean metrics.documents_per_second status')
		.lean();
	return rows.map((r) => ({
		name: r.name,
		engine: r.engine,
		status: r.status,
		bytes_per_second: (r.metrics && r.metrics.bytes_per_second) || null,
		seconds_mean: (r.metrics && r.metrics.seconds_mean) || null,
		documents_per_second: (r.metrics && r.metrics.documents_per_second) || null,
	}));
}

module.exports = { throughputTrend, buildMatch, ALLOWED_METRICS, acceptancePanel, scannerPanel, runBreakdown };