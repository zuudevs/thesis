import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { Overview } from '../types';

let cached: Overview | null = null;
let inflight: Promise<Overview> | null = null;

function load(): Promise<Overview> {
	if (cached) return Promise.resolve(cached);
	if (!inflight) {
		inflight = apiGet<Overview>('stats/overview').then((data) => {
			cached = data;
			return data;
		});
	}
	return inflight;
}

/** Overview di-fetch sekali lalu di-cache (facets stabil; invalidate setelah import). */
export function useOverview() {
	const [data, setData] = useState<Overview | null>(cached);
	const [error, setError] = useState<Error | null>(null);

	useEffect(() => {
		let alive = true;
		load()
			.then((d) => alive && setData(d))
			.catch((e) => alive && setError(e));
		return () => {
			alive = false;
		};
	}, []);

	const refresh = () => {
		cached = null;
		inflight = null;
		load().then(setData).catch(() => undefined);
	};

	return { data, error, refresh };
}