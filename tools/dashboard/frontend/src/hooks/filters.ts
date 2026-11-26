import { EMPTY_FILTERS, type FilterValues } from '../components/FilterPanel';

/** ISO datetime (API) → YYYY-MM-DD (input type=date). */
export function fmtDateInput(iso: string): string {
	if (!iso) return '';
	if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return '';
	return d.toISOString().slice(0, 10);
}

/** Filter state → URLSearchParams (nilai kosong dihilangkan). */
export function filtersToParams(values: FilterValues): URLSearchParams {
	const params = new URLSearchParams();
	for (const [key, val] of Object.entries(values)) {
		if (val) params.set(key, val);
	}
	return params;
}

/** URLSearchParams → Filter state (aman terhadap key tak dikenal). */
export function paramsToFilters(params: URLSearchParams): FilterValues {
	const out: FilterValues = { ...EMPTY_FILTERS };
	for (const key of Object.keys(EMPTY_FILTERS)) {
		const v = params.get(key);
		if (v) (out as unknown as Record<string, string>)[key] = v;
	}
	return out;
}