const assert = require('node:assert/strict');
const test = require('node:test');

const { evaluateGuardrails } = require('../src/services/compare.service');

function result(overrides = {}) {
	return {
		run_id: 'host-20261126000000-abcdef1',
		corpus_key: 'synthetic_1mb',
		corpus_name: 'synthetic_1mb',
		name: 'parse/body',
		site: 'dev_device',
		kind: 'benchmark',
		library_runtime: 'node-26.13.1',
		toolchain: 'v8-14.6',
		git_hash: 'abcdef1',
		dirty: false,
		exploratory: false,
		...overrides,
	};
}

test('guardrail membolehkan perbandingan dalam satu run_id dan korpus', () => {
	const checks = evaluateGuardrails([
		result({ name: 'baseline' }),
		result({ name: 'candidate' }),
	]);
	assert.deepEqual(checks.blocks, []);
	assert.deepEqual(checks.warnings, []);
});

test('guardrail memblokir run_id berbeda', () => {
	const checks = evaluateGuardrails([
		result(),
		result({ run_id: 'host-20261126000001-bbcdef2' }),
	]);
	assert.ok(checks.blocks.some((block) => block.code === 'CROSS_RUN'));
});

test('guardrail memblokir site, kind, dan korpus berbeda', () => {
	const checks = evaluateGuardrails([
		result(),
		result({ site: 'saq_server' }),
		result({ kind: 'test' }),
		result({ corpus_key: 'saq_payload_v1', corpus_name: 'saq_payload_v1' }),
	]);
	const codes = new Set(checks.blocks.map((block) => block.code));
	assert.ok(codes.has('CROSS_SITE'));
	assert.ok(codes.has('CROSS_KIND'));
	assert.ok(codes.has('CROSS_CORPUS'));
});

test('guardrail memberi warning untuk runtime dan toolchain berbeda', () => {
	const checks = evaluateGuardrails([
		result(),
		result({ library_runtime: 'node-24.19.0', toolchain: 'v8-13.6' }),
	]);
	const codes = new Set(checks.warnings.map((warning) => warning.code));
	assert.ok(codes.has('CROSS_RUNTIME'));
	assert.ok(codes.has('CROSS_TOOLCHAIN'));
});

test('guardrail memberi warning untuk dirty dan exploratory', () => {
	const checks = evaluateGuardrails([
		result(),
		result({ dirty: true, exploratory: true }),
	]);
	const codes = new Set(checks.warnings.map((warning) => warning.code));
	assert.ok(codes.has('DIRTY_TREE'));
	assert.ok(codes.has('EXPLORATORY'));
});
