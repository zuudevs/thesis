const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const { validate } = require('../src/validators/measurement.validator');

const ROOT = path.resolve(__dirname, '../../../..');

function sample(name) {
	return JSON.parse(fs.readFileSync(path.join(ROOT, 'scripts/measurement-schema/samples', name), 'utf8'));
}

test('measurement validator menerima record canonical yang valid', () => {
	const result = validate(sample('valid.record.json'));
	assert.equal(result.valid, true, JSON.stringify(result.errors));
	assert.deepEqual(result.errors, []);
});

test('measurement validator menolak rationale kosong', () => {
	const result = validate(sample('invalid.empty_basis_papers.json'));
	assert.equal(result.valid, false);
	assert.ok(result.errors.some((error) => error.keyword === 'minItems'));
});

test('measurement validator menolak metadata host yang tidak lengkap', () => {
	const result = validate(sample('invalid.missing_metadata.json'));
	assert.equal(result.valid, false);
	assert.ok(result.errors.length > 0);
});
