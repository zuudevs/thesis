// Fetch helper untuk semua call API dashboard (base relatif → proxy Vite ke :3000).
const BASE = '/api';

export class HttpError extends Error {
	constructor(public status: number, message: string, public body?: unknown) {
		super(message);
	}
}

function toQuery(params: Record<string, unknown>): string {
	const qs = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		if (Array.isArray(value)) {
			if (value.length) qs.set(key, value.join(','));
		} else {
			qs.set(key, String(value));
		}
	}
	const s = qs.toString();
	return s ? `?${s}` : '';
}

export async function apiGet<T>(path: string, params: Record<string, unknown> = {}): Promise<T> {
	const res = await fetch(`${BASE}/${path}${toQuery(params)}`);
	const text = await res.text();
	const data = text ? JSON.parse(text) : null;
	if (!res.ok) {
		throw new HttpError(res.status, (data && data.message) || `HTTP ${res.status}`, data);
	}
	return data as T;
}

export async function apiPost<T>(path: string, body?: unknown, params: Record<string, unknown> = {}): Promise<T> {
	const res = await fetch(`${BASE}/${path}${toQuery(params)}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
	const text = await res.text();
	const data = text ? JSON.parse(text) : null;
	if (!res.ok) {
		throw new HttpError(res.status, (data && data.message) || `HTTP ${res.status}`, data);
	}
	return data as T;
}

// Pemformat angka gaya Indonesia (titik ribuan, koma desimal).
export function fmt(value: number | null | undefined, digits = 0): string {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	return value.toLocaleString('id-ID', { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

/** Format throughput (bytes/detik) dengan satuan. */
export function fmtBytesPerSec(value: number | null | undefined): string {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
	let v = value;
	let u = 0;
	while (v >= 1024 && u < units.length - 1) {
		v /= 1024;
		u += 1;
	}
	return `${fmt(v, v < 10 ? 2 : 0)} ${units[u]}`;
}

/** Durasi detik → μs/ms/s manusiawi. */
export function fmtSeconds(value: number | null | undefined): string {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	if (value < 1e-3) return `${fmt(value * 1e6, 1)} µs`;
	if (value < 1) return `${fmt(value * 1e3, 2)} ms`;
	return `${fmt(value, 3)} s`;
}

export function fmtSpeedup(value: number | null | undefined): string {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	return `${fmt(value, 2)}×`;
}

export function fmtDateTime(value: string | null | undefined): string {
	if (!value) return '—';
	const d = new Date(value);
	if (Number.isNaN(d.getTime())) return String(value);
	return d.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
}

export function fmtBytes(bytes: number | null | undefined): string {
	if (bytes === null || bytes === undefined || Number.isNaN(bytes)) return '—';
	const units = ['B', 'KB', 'MB', 'GB'];
	let v = bytes;
	let u = 0;
	while (v >= 1024 && u < units.length - 1) {
		v /= 1024;
		u += 1;
	}
	return `${fmt(v, v < 10 ? 2 : 0)} ${units[u]}`;
}