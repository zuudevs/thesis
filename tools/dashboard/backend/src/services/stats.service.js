const mongoose = require('mongoose');
const Run = require('../models/Run');
const Result = require('../models/Result');
const InvalidRecord = require('../models/InvalidRecord');
const ingest = require('./ingest.service');

async function distinct(field, match = {}) {
	return Result.distinct(field, match);
}

function countBy(rows, field) {
	const out = {};
	for (const r of rows) out[r[field] || '(none)'] = (out[r[field] || '(none)'] || 0) + 1;
	return out;
}

/** Ringkasan + nilai distinct untuk mengisi opsi filter sidebar. */
async function overview() {
	const [runs, results, invalid, status] = await Promise.all([
		Run.countDocuments(),
		Result.countDocuments(),
		InvalidRecord.countDocuments(),
		ingest.importStatus(),
	]);

	const [sites, kinds, generators, engines, corpora, families, modes, statuses, libraries] =
		await Promise.all([
			distinct('site'),
			distinct('kind'),
			distinct('generator'),
			distinct('engine'),
			distinct('corpus_name'),
			distinct('family'),
			Result.distinct('mode', { mode: { $ne: null } }),
			distinct('status'),
			distinct('library_name'),
		]);

	const runDates = await Run.aggregate([
		{ $match: { 'derived.date_utc': { $ne: null } } },
		{ $group: { _id: null, first: { $min: '$derived.date_utc' }, last: { $max: '$derived.date_utc' } } },
	]);

	// Run per hari (untuk sparkline aktivitas riset).
	const perDay = await Run.aggregate([
		{ $match: { 'derived.date_utc': { $ne: null } } },
		{
			$group: {
				_id: { $dateToString: { format: '%Y-%m-%d', date: '$derived.date_utc' } },
				runs: { $addToSet: '$run_id' },
				files: { $sum: 1 },
			},
		},
		{ $sort: { _id: 1 } },
		{ $project: { day: '$_id', runs: { $size: '$runs' }, files: 1, _id: 0 } },
	]);

	// Sebaran per site/library/kind dari runs.
	const bySite = countBy(await Run.find().select('site').lean(), 'site');
	const byKind = countBy(await Run.find().select('kind').lean(), 'kind');
	const byGenerator = countBy(await Run.find().select('generator').lean(), 'generator');
	const byLibrary = countBy(await Run.find().select('library').lean(), 'library');

	const dirtyRuns = await Run.countDocuments({ 'derived.dirty': true });
	const exploratoryRuns = await Run.countDocuments({ 'derived.exploratory': true });

	// Family teratas (dari results_brief) untuk badge quick-filter.
	const familyTop = await Run.aggregate([
		{ $unwind: '$results_brief' },
		{ $group: { _id: '$results_brief.family', count: { $sum: 1 } } },
		{ $sort: { count: -1 } },
	]);

	return {
		counts: { runs, results, invalid_records: invalid },
		import: status,
		facets: {
			sites: sites.filter(Boolean).sort(),
			kinds: kinds.filter(Boolean).sort(),
			generators: generators.filter(Boolean).sort(),
			engines: engines.filter(Boolean).sort(),
			corpora: corpora.filter(Boolean).sort(),
			families: families.filter(Boolean).sort(),
			modes: modes.filter(Boolean).sort(),
			statuses: statuses.filter(Boolean).sort(),
			libraries: libraries.filter(Boolean).sort(),
		},
		distribution: { bySite, byKind, byGenerator, byLibrary },
		dirty_runs: dirtyRuns,
		exploratory_runs: exploratoryRuns,
		date_range: runDates[0] || { first: null, last: null },
		runs_per_day: perDay,
		family_top: familyTop.map((f) => ({ family: f._id, count: f.count })),
	};
}

module.exports = { overview };