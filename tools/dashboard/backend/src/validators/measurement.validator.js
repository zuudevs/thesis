const fs = require('fs');

const ajv = require('./index');
const { schemaPath } = require('../lib/paths');
const schema = JSON.parse(fs.readFileSync(schemaPath(), 'utf8'));

const validateMeasurement = ajv.compile(schema);

function validate(data) {
	const valid = validateMeasurement(data);

	return {
		valid,
		errors: valid
		 ? []
		 : validateMeasurement.errors.map(error => ({
			path: error.instancePath,
			schemaPath: error.schemaPath,
			keyword: error.keyword,
			message: error.message,
			params: error.params,
		}))
	};
}

module.exports = {
	validate,
	validateMeasurement
};