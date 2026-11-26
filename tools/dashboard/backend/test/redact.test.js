const assert = require('node:assert/strict');
const test = require('node:test');

const { redactMongoUri } = require('../src/lib/redact');

test('redactMongoUri menyembunyikan userinfo MongoDB', () => {
	assert.equal(
		redactMongoUri('mongodb://user:secret@127.0.0.1:27017/ze_json'),
		'mongodb://***@127.0.0.1:27017/ze_json',
	);
});

test('redactMongoUri menyembunyikan password pada query parameter', () => {
	assert.equal(
		redactMongoUri('mongodb://127.0.0.1:27017/ze_json?password=secret&retryWrites=true'),
		'mongodb://127.0.0.1:27017/ze_json?password=***&retryWrites=true',
	);
});

test('redactMongoUri tidak mengubah URI tanpa credential', () => {
	const uri = 'mongodb://127.0.0.1:27017/ze_json';
	assert.equal(redactMongoUri(uri), uri);
});
