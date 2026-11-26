const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const Ajv = require('ajv');

const Run = require('../models/Run');
const Result = require('../models/Result');
const InvalidRecord = require('../models/InvalidRecord');
const { measurementsDir, schemaPath } = require('../lib/paths');

let compiledValidator = null;

/**
 * Ingest service — memindai folder out/measurements, memvalidasi setiap record
 * terhadap schemas/measurement.schema.json (sumber kebenaran, dibaca dari root
 * repo — bukan salinan lokal), lalu upsert ke MongoDB.
 *
 * Kunci upsert Run = (run_id, corpus_key). run_id TIDAK unik per file: satu
 * run_id mengukur hingga 6 korpus, masing-masing satu file *_record.json.
 */
function getValidator() {
	if (!compiledValidator) {
		const schemaRaw = fs.readFileSync(schemaPath(), 'utf8');
		const schema = JSON.parse(schemaRaw);
		const ajv = new Ajv({ allErrors: true, strict: false });
		compiledValidator = ajv.compile(schema);
	}
	return compiledValidator;
}

/**
 * Karantina file invalid dan hapus data import lama dengan nama file yang sama.
 * Tanpa penghapusan ini, record yang pernah valid tetapi kemudian rusak tetap
 * tersedia di Run/Result dan bisa dipakai analisis.
 */
async function quarantineInvalid(
	{ fileName, filePath, scannedAt, reason, validationErrors = [] },
	stores = { Run, Result, InvalidRecord },
) {
	const staleRun = await stores.Run.findOne({ file_name: fileName }).lean();
	if (staleRun) {
		await stores.Result.deleteMany({ run_id: staleRun.run_id, corpus_key: staleRun.corpus_key });
		await stores.Run.deleteOne({ _id: staleRun._id });
	}
	await stores.InvalidRecord.create({
		file_name: fileName,
		file_path: filePath,
		scanned_at: scannedAt,
		reason,
		validation_errors: validationErrors,
	});
	return Boolean(staleRun);
}

/** Parse ringan name record: family/action/subject(+mode scanner). Verbatim tetap disimpan. */
function parseName(name) {
	const parts = String(name || '').split('/');
	const family = parts[0] || null;
	let action = parts.length > 1 ? parts[1] : null;
	let subject = parts.length > 2 ? parts.slice(2).join('/') : null;
	let mode = null;
	if (action && action.includes('@')) {
		const at = action.indexOf('@');
		mode = action.slice(at + 1);
		action = action.slice(0, at);
	}
	return { family, action, subject, mode };
}

function toNumberOrNull(v) {
	return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function sha256(buf) {
	return crypto.createHash('sha256').update(buf).digest('hex');
}

function uniqSorted(arr) {
	return [...new Set(arr.filter(Boolean))].sort();
}

async function scanAndImport(options = {}) {
	const dir = options.dir || measurementsDir();
	const validate = getValidator();
	const startedAt = new Date();

	const summary = {
		dir,
		started_at: startedAt,
		finished_at: null,
		scanned_files: 0,
		created: 0,
		updated: 0,
		unchanged: 0,
		invalid: 0,
		invalid_runs_removed: 0,
		errors: [],
		pruned: 0,
	};

	if (!fs.existsSync(dir)) {
		throw new Error(`Folder pengukuran tidak ditemukan: ${dir}`);
	}

	const files = fs
		.readdirSync(dir)
		.filter((f) => f.endsWith('.json'))
		.sort();

	// Snapshot nama file valid untuk opsi prune.
	const presentFiles = new Set(files);

	await InvalidRecord.deleteMany({});

	for (const fileName of files) {
		summary.scanned_files += 1;
		const filePath = path.join(dir, fileName);
		let record;
		let raw;
		try {
			raw = fs.readFileSync(filePath);
			record = JSON.parse(raw.toString('utf8'));
		} catch (err) {
			summary.invalid += 1;
			summary.errors.push({ file: fileName, reason: `tidak bisa dibaca/di-parse: ${err.message}` });
			const removed = await quarantineInvalid({
				fileName,
				filePath,
				scannedAt: startedAt,
				reason: `parse error: ${err.message}`,
			});
			if (removed) summary.invalid_runs_removed += 1;
			continue;
		}

		if (!validate(record)) {
			summary.invalid += 1;
			const errs = (validate.errors || []).map((e) => ({
				path: e.instancePath,
				message: e.message,
				keyword: e.keyword,
			}));
			summary.errors.push({ file: fileName, reason: 'gagal validasi schema', errors: errs.slice(0, 5) });
			const removed = await quarantineInvalid({
				fileName,
				filePath,
				scannedAt: startedAt,
				reason: 'gagal validasi schema',
				validationErrors: errs,
			});
			if (removed) summary.invalid_runs_removed += 1;
			continue;
		}

		const fileHash = sha256(raw);
		const corpusKey = (record.corpus && record.corpus.name) || '(none)';

		const existing = await Run.findOne({ run_id: record.run_id, corpus_key: corpusKey }).lean();
		if (existing && existing.file_sha256 === fileHash) {
			summary.unchanged += 1;
			continue;
		}

		const results = (record.results || []).map((r) => {
			const parsed = parseName(r.name);
			return { ...r, ...parsed };
		});

		const derived = {
			n_results: results.length,
			engines: uniqSorted(results.map((r) => r.engine)),
			families: uniqSorted(results.map((r) => r.family)),
			modes: uniqSorted(results.map((r) => r.mode)),
			statuses: uniqSorted(results.map((r) => r.status)),
			dirty: Boolean(record.git_commit && record.git_commit.dirty),
			exploratory: Boolean(record.config && record.config.exploratory),
			scanner_mode: (record.config && record.config.scanner_mode) || null,
			date_utc: (record.config && record.config.date_utc) ? new Date(record.config.date_utc) : null,
			corpus_name: (record.corpus && record.corpus.name) || null,
			host_label: [record.host && record.host.hostname, record.host && record.host.cpu_model]
				.filter(Boolean)
				.join(' · '),
			runtime_label: record.library && record.library.language_runtime,
			toolchain: record.host && record.host.toolchain,
			names_text: results.map((r) => r.name).join(' | '),
		};

		// Upsert run (record disimpan verbatim agar provenance utuh).
		const runDoc = await Run.findOneAndUpdate(
			{ run_id: record.run_id, corpus_key: corpusKey },
			{
				run_id: record.run_id,
				corpus_key: corpusKey,
				file_name: fileName,
				file_sha256: fileHash,
				imported_at: startedAt,
				schema_version: record.schema_version,
				kind: record.kind,
				generator: record.generator,
				site: record.site,
				library: record.library,
				git_commit: record.git_commit,
				host: record.host,
				corpus: record.corpus,
				config: record.config,
				record,
				results_brief: results.map((r) => ({
					name: r.name,
					engine: r.engine,
					status: r.status,
					family: r.family,
					action: r.action,
					subject: r.subject,
					mode: r.mode,
					seconds_mean: toNumberOrNull(r.metrics && r.metrics.seconds_mean),
					bytes_per_second: toNumberOrNull(r.metrics && r.metrics.bytes_per_second),
				})),
				derived,
			},
			{ upsert: true, returnDocument: 'after', setDefaultsOnInsert: true }
		);
		if (existing) summary.updated += 1;
		else summary.created += 1;

		// Ganti seluruh result docs milik run+corpus ini (identitas byte result dijaga
		// lewat sha256 file; kalau file berubah, results ikut disegarkan).
		await Result.deleteMany({ run_id: record.run_id, corpus_key: corpusKey });
		const resultDocs = results.map((r) => ({
			run_ref: runDoc._id,
			run_id: record.run_id,
			corpus_key: corpusKey,
			name: r.name,
			family: r.family,
			action: r.action,
			subject: r.subject,
			mode: r.mode,
			engine: r.engine,
			status: r.status,
			purpose: r.rationale && r.rationale.purpose,
			basis_papers: (r.rationale && r.rationale.basis_papers) || [],
			metrics: r.metrics || {},
			extras: r.extras || {},
			site: record.site,
			kind: record.kind,
			generator: record.generator,
			library_name: record.library && record.library.name,
			library_runtime: record.library && record.library.language_runtime,
			git_hash: record.git_commit && record.git_commit.hash,
			dirty: Boolean(record.git_commit && record.git_commit.dirty),
			exploratory: Boolean(record.config && record.config.exploratory),
			scanner_mode: (record.config && record.config.scanner_mode) || null,
			corpus_name: (record.corpus && record.corpus.name) || null,
			date_utc: (record.config && record.config.date_utc)
				? new Date(record.config.date_utc)
				: null,
			hostname: record.host && record.host.hostname,
			toolchain: record.host && record.host.toolchain,
			cpu_model: record.host && record.host.cpu_model,
		}));
		if (resultDocs.length) await Result.insertMany(resultDocs);
	}

	if (options.prune) {
		const stale = await Run.find({ file_name: { $nin: [...presentFiles] } });
		for (const run of stale) {
			await Result.deleteMany({ run_id: run.run_id, corpus_key: run.corpus_key });
			await Run.deleteOne({ _id: run._id });
			summary.pruned += 1;
		}
	}

	summary.finished_at = new Date();
	summary.collection_counts = {
		runs: await Run.countDocuments(),
		results: await Result.countDocuments(),
		invalid: await InvalidRecord.countDocuments(),
	};
	return summary;
}

async function importStatus() {
	const last = await Run.findOne().sort({ imported_at: -1 }).lean();
	return {
		measurements_dir: measurementsDir(),
		schema_path: schemaPath(),
		last_import_at: (last && last.imported_at) || null,
		counts: {
			runs: await Run.countDocuments(),
			results: await Result.countDocuments(),
			invalid: await InvalidRecord.countDocuments(),
		},
	};
}

async function listInvalid() {
	return InvalidRecord.find().sort({ scanned_at: -1 }).lean();
}

module.exports = { scanAndImport, importStatus, listInvalid, parseName, quarantineInvalid };