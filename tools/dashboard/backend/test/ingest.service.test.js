const assert = require('node:assert/strict');
const test = require('node:test');

const { quarantineInvalid } = require('../src/services/ingest.service');

test('karantina invalid menghapus Run dan Result lama dengan file yang sama', async () => {
	const calls = [];
	const stores = {
		Run: {
			findOne: (query) => {
				calls.push(['findOne', query]);
				return { lean: async () => ({ _id: 'run-id', run_id: 'run-1', corpus_key: 'corpus-1' }) };
			},
			deleteOne: async (query) => calls.push(['deleteRun', query]),
		},
		Result: {
			deleteMany: async (query) => calls.push(['deleteResults', query]),
		},
		InvalidRecord: {
			create: async (document) => calls.push(['createInvalid', document]),
		},
	};

	const removed = await quarantineInvalid(
		{
			fileName: 'broken.record.json',
			filePath: '/tmp/broken.record.json',
			scannedAt: new Date('2026-11-26T00:00:00Z'),
			reason: 'gagal validasi schema',
			validationErrors: [{ path: '/results/0' }],
		},
		stores,
	);

	assert.equal(removed, true);
	assert.deepEqual(calls[1], ['deleteResults', { run_id: 'run-1', corpus_key: 'corpus-1' }]);
	assert.deepEqual(calls[2], ['deleteRun', { _id: 'run-id' }]);
	assert.equal(calls[3][0], 'createInvalid');
});

test('karantina invalid tidak menghapus data bila tidak ada run lama', async () => {
	const calls = [];
	const stores = {
		Run: {
			findOne: () => ({ lean: async () => null }),
			deleteOne: async () => calls.push(['deleteRun']),
		},
		Result: {
			deleteMany: async () => calls.push(['deleteResults']),
		},
		InvalidRecord: {
			create: async () => calls.push(['createInvalid']),
		},
	};

	const removed = await quarantineInvalid(
		{
			fileName: 'broken.record.json',
			filePath: '/tmp/broken.record.json',
			scannedAt: new Date('2026-11-26T00:00:00Z'),
			reason: 'parse error',
		},
		stores,
	);

	assert.equal(removed, false);
	assert.deepEqual(calls, [['createInvalid']]);
});
