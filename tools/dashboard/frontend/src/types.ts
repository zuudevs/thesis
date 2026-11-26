// Tipe data API dashboard (mencerminkan schemas/measurement.schema.json).

export interface ImportStatus {
	measurements_dir: string;
	schema_path: string;
	last_import_at: string | null;
	counts: { runs: number; results: number; invalid: number };
}

export interface Overview {
	counts: { runs: number; results: number; invalid_records: number };
	import: ImportStatus;
	facets: {
		sites: string[];
		kinds: string[];
		generators: string[];
		engines: string[];
		corpora: string[];
		families: string[];
		modes: string[];
		statuses: string[];
		libraries: string[];
	};
	distribution: Record<string, Record<string, number>>;
	dirty_runs: number;
	exploratory_runs: number;
	date_range: { first: string | null; last: string | null };
	runs_per_day: { day: string; runs: number; files: number }[];
	family_top: { family: string; count: number }[];
}

export interface RunRow {
	_id: string;
	run_id: string;
	corpus_key: string;
	file_name: string;
	imported_at: string;
	kind: 'benchmark' | 'test';
	generator: string;
	site: string;
	library: { name: string; version: string; language_runtime?: string };
	git_commit: { hash: string; dirty: boolean; repo: string };
	host: {
		hostname: string;
		cpu_model: string;
		os: string;
		arch: string;
		os_version?: string;
		cpu_cores?: number;
		cpu_freq?: string;
		ram_gb?: number;
		toolchain?: string;
	};
	corpus: { name: string; document_count: number; total_bytes: number; sha256: string };
	config: Record<string, unknown> & { date_utc?: string; scanner_mode?: string; notes?: string };
	results_brief: {
		name: string;
		engine: string;
		status: string;
		family: string;
		action: string;
		subject: string | null;
		mode?: string | null;
		seconds_mean: number | null;
		bytes_per_second: number | null;
	}[];
	derived: {
		n_results: number;
		engines: string[];
		families: string[];
		modes: string[];
		dirty: boolean;
		exploratory: boolean;
		scanner_mode: string | null;
		date_utc: string | null;
		corpus_name: string | null;
		host_label: string;
		runtime_label: string;
	};
}

export interface ResultRow {
	_id: string;
	run_id: string;
	corpus_key: string;
	name: string;
	family: string;
	action: string;
	subject: string | null;
	mode: string | null;
	engine: string;
	status: string;
	purpose: string;
	basis_papers: string[];
	metrics: {
		bytes_per_second?: number;
		seconds_mean?: number;
		seconds_stddev?: number;
		cpu_seconds?: number;
		documents_per_second?: number;
		items_per_second?: number;
		peak_rss_bytes?: number;
	};
	extras: Record<string, unknown>;
	site: string;
	kind: string;
	generator: string;
	library_name: string;
	library_runtime: string;
	git_hash: string;
	dirty: boolean;
	exploratory: boolean;
	scanner_mode: string | null;
	corpus_name: string;
	date_utc: string;
	hostname: string;
	toolchain: string;
	cpu_model: string;
}

export interface RunDetail {
	run_id: string;
	corpora: string[];
	runs: RunRow[];
	results: ResultRow[];
	breakdown: { name: string; engine: string; bytes_per_second: number | null; seconds_mean: number | null; documents_per_second: number | null }[] | null;
}

export interface Paged<T> {
	total: number;
	page: number;
	pageSize: number;
	rows: T[];
}

export interface TrendSeries {
	key: string;
	meta: { engine: string; corpus: string; site: string };
	points: { date: string; value: number | null; seconds_mean: number | null; run_id: string }[];
}

export interface TrendResponse {
	metric: string;
	series: TrendSeries[];
}

export interface AcceptancePair {
	run_id: string;
	corpus_key: string;
	date_utc: string;
	site: string;
	kind: string;
	corpus_name: string;
	family: string;
	subject_key: string;
	dirty: boolean;
	exploratory: boolean;
	git_hash: string;
	runtime_label: string;
	baseline: { name: string; engine: string; seconds_mean: number; bytes_per_second: number | null };
	candidate: { name: string; engine: string; seconds_mean: number; bytes_per_second: number | null };
	speedup: number;
	status: 'tercapai' | 'belum';
}

export interface AcceptanceResponse {
	threshold: number;
	count: number;
	latest: AcceptancePair[];
	trend: AcceptancePairTrendPoint[];
}

export interface AcceptancePairTrendPoint {
	date: string;
	run_id: string;
	site: string;
	family: string;
	corpus_name: string;
	subject_key: string;
	candidate_engine: string;
	speedup: number;
	status: string;
	dirty: boolean;
	exploratory: boolean;
}

export interface ScannerRun {
	run_id: string;
	site: string;
	corpus_name: string;
	date_utc: string;
	modes: { mode: string; name: string; bytes_per_second: number | null; seconds_mean: number | null }[];
}

export interface CompareRow {
	run_id: string;
	corpus_key: string;
	corpus_name: string;
	name: string;
	engine: string;
	site: string;
	dirty: boolean;
	exploratory: boolean;
	git_hash: string;
	runtime_label: string;
	toolchain: string;
	date_utc: string;
	seconds_mean: number | null;
	bytes_per_second: number | null;
	documents_per_second: number | null;
	speedup_vs_ref: number | null;
	bps_ratio_vs_ref: number | null;
	purpose: string;
	basis_papers: string[];
}

export interface CompareResponse {
	reference: { run_id: string; corpus_key: string; name: string };
	rows: CompareRow[];
	checks: { blocks: { code: string; message: string }[]; warnings: { code: string; message: string }[] };
	valid: boolean;
}

export interface ImportSummary {
	dir: string;
	scanned_files: number;
	created: number;
	updated: number;
	unchanged: number;
	invalid: number;
	errors: { file: string; reason: string; errors?: unknown }[];
	pruned: number;
	collection_counts: { runs: number; results: number; invalid: number };
}

export interface InvalidRecordRow {
	_id: string;
	file_name: string;
	file_path: string;
	scanned_at: string;
	reason: string;
	validation_errors: { path: string; message: string; keyword: string }[];
}