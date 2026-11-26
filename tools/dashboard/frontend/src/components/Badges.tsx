import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';

/** Badge tree dirty — hash/cocokkan status di laporan (AGENTS.md §4). */
export function DirtyBadge({ dirty }: { dirty: boolean }) {
	if (!dirty) return null;
	return (
		<Tooltip title="Working tree dirty — run ini memakai kode belum ter-commit; sebut di laporan.">
			<Chip size="small" color="warning" variant="outlined" label="dirty" sx={{ ml: 0.5 }} />
		</Tooltip>
	);
}

/** Badge run exploratory (--allow-dirty) — bukti eksplorasi, bukan acceptance. */
export function ExploratoryBadge({ exploratory }: { exploratory: boolean }) {
	if (!exploratory) return null;
	return (
		<Tooltip title="Run exploratory (--allow-dirty): bukti eksplorasi, bukan acceptance.">
			<Chip size="small" color="error" variant="outlined" label="exploratory" sx={{ ml: 0.5 }} />
		</Tooltip>
	);
}

/** Chip engine dengan warna konsisten. */
const ENGINE_COLOR: Record<string, 'primary' | 'secondary' | 'default' | 'info'> = {
	v8: 'default',
	wasm64_cabi: 'primary',
	scalar: 'secondary',
	simd: 'info',
};

export function EngineChip({ engine }: { engine: string }) {
	return <Chip size="small" color={ENGINE_COLOR[engine] || 'default'} label={engine} variant="outlined" />;
}

/** Chip speedup berwarna sesuai ambang acceptance. */
export function SpeedupChip({ value, threshold = 1.5 }: { value: number; threshold?: number }) {
	const met = value >= threshold;
	return (
		<Chip
			size="small"
			color={met ? 'success' : 'default'}
			label={`${value.toFixed(2)}× ${met ? '✓' : ''}`}
			variant={met ? 'filled' : 'outlined'}
			sx={{ fontWeight: 600 }}
		/>
	);
}