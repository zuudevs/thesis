#!/usr/bin/env node
/**
 * CLI importer: scan out/measurements -> validasi schema -> upsert MongoDB.
 *
 *   node scripts/import-measurements.js               # impor biasa
 *   node scripts/import-measurements.js --dir <path>  # folder lain
 *   node scripts/import-measurements.js --prune       # hapus run yang filenya hilang
 *
 * Exit code: 0 sukses (termasuk 0 valid), 1 gagal fatal.
 */
const path = require('path');
const mongoose = require('mongoose');

require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

const ingest = require('../src/services/ingest.service');
const { redactMongoUri } = require('../src/lib/redact');

async function main() {
	const args = process.argv.slice(2);
	const dirFlag = args.indexOf('--dir');
	const options = {};
	if (dirFlag >= 0 && args[dirFlag + 1]) options.dir = args[dirFlag + 1];
	if (args.includes('--prune')) options.prune = true;

	const uri =
		process.env.MONGODB_URI ||
		`mongodb://${process.env.MONGODB_HOST || '127.0.0.1'}:${process.env.MONGODB_PORT || 27017}/${process.env.MONGODB_NAME || 'ze_json'}`;

	try {
		await mongoose.connect(uri, { serverSelectionTimeoutMS: 5000 });
	} catch (err) {
		console.error(
			`Gagal konek MongoDB (${redactMongoUri(uri)}). Pastikan mongod berjalan:\n` +
				`  npm run mongo --prefix tools/dashboard  # dari root workspace\n\n` +
				`Error: ${err.message}`
		);
		process.exit(1);
	}

	const started = Date.now();
	const summary = await ingest.scanAndImport(options);
	const secs = ((Date.now() - started) / 1000).toFixed(1);

	console.log('=== Impor selesai ===');
	console.log(`Folder          : ${summary.dir}`);
	console.log(`File dipindai   : ${summary.scanned_files}`);
	console.log(`Baru / diperbarui / tak berubah : ${summary.created} / ${summary.updated} / ${summary.unchanged}`);
	console.log(`Gagal validasi  : ${summary.invalid}`);
	console.log(`Data invalid dihapus dari analisis: ${summary.invalid_runs_removed}`);
	if (summary.pruned) console.log(`Di-prune       : ${summary.pruned}`);
	console.log(`Koleksi         : runs=${summary.collection_counts.runs} results=${summary.collection_counts.results} invalid=${summary.collection_counts.invalid}`);
	console.log(`Durasi          : ${secs}s`);
	if (summary.invalid > 0) {
		console.log('\nDetail gagal:');
		for (const e of summary.errors) console.log(` - ${e.file}: ${e.reason}`);
	}
	await mongoose.disconnect();
	process.exit(0);
}

main().catch((err) => {
	console.error('Impor gagal:', err);
	process.exit(1);
});