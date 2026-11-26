const path = require('path');

/** Root repo (v5) — tools/dashboard/backend/src/lib -> 5 tingkat naik. */
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..', '..');

function fromRepo(configured, fallbackFromRoot) {
	if (configured && String(configured).trim()) {
		return path.isAbsolute(configured)
			? configured
			: path.resolve(REPO_ROOT, configured);
	}
	return path.resolve(REPO_ROOT, fallbackFromRoot);
}

/** Folder sumber record pengukuran (out/measurements). */
function measurementsDir() {
	return fromRepo(process.env.MEASUREMENTS_DIR, 'out/measurements');
}

/** Schema JSON sumber kebenaran (schemas/measurement.schema.json di root repo). */
function schemaPath() {
	return fromRepo(process.env.SCHEMA_PATH, 'schemas/measurement.schema.json');
}

module.exports = { REPO_ROOT, measurementsDir, schemaPath, fromRepo };