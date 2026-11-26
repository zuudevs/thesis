const Ajv = require('ajv');

const ajv = new Ajv({
	allErrors: true,
	strict: false
});

module.exports = ajv;