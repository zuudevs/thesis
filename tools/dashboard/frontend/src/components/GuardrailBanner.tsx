import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import type { CompareResponse } from '../types';

/**
 * Banner guardrail AGENTS.md §4:
 * - blok → merah (perbandingan tidak sah)
 * - warning → kuning (narara riset / label wajib)
 */
export default function GuardrailBanner({ checks }: { checks: CompareResponse['checks'] }) {
	if (!checks.blocks.length && !checks.warnings.length) {
		return <Alert severity="success">Tidak ada pelanggaran guardrail statis: satu run_id, site, kind, dan korpus.</Alert>;
	}
	return (
		<Stack spacing={1}>
			{checks.blocks.map((b) => (
				<Alert key={b.code} severity="error">
					<b>{b.code}</b> — {b.message}
				</Alert>
			))}
			{checks.warnings.map((w) => (
				<Alert key={w.code} severity="warning">
					<b>{w.code}</b> — {w.message}
				</Alert>
			))}
		</Stack>
	);
}