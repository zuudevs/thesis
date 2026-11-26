/** Redact credential-bearing parts of a MongoDB URI before logging. */
function redactMongoUri(uri) {
	return String(uri)
		.replace(/(\/\/)([^/@]+)@/, '$1***@')
		.replace(/([?&](?:password|passwd|pwd)=)[^&]*/gi, '$1***');
}

module.exports = { redactMongoUri };
