import { Grid, Card, CardContent, Typography, Stack, Chip, Alert, Box, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import { useOverview } from '../hooks/useOverview';
import { fmt, fmtDateTime } from '../api/client';
import EChart from '../components/EChart';
import { DirtyBadge, ExploratoryBadge } from '../components/Badges';

export default function OverviewPage() {
	const { data, error } = useOverview();

	if (error) return <Alert severity="error">Gagal memuat ringkasan: {error.message}</Alert>;
	if (!data) return <Alert severity="info">Memuat…</Alert>;

	const perDay = data.runs_per_day.slice(-60);
	const familyTop = data.family_top.slice(0, 8);
	const dist = data.distribution;

	return (
		<Stack spacing={3}>
			<Grid container spacing={2}>
				<Kpi label="Total run (file record)" value={fmt(data.counts.runs)} />
				<Kpi label="Total result" value={fmt(data.counts.results)} />
				<Kpi label="Run dirty tree" value={fmt(data.dirty_runs)} note="hash -dirty wajib disebut di laporan" />
				<Kpi label="Run exploratory" value={fmt(data.exploratory_runs)} note="bukan acceptance evidence" />
				<Kpi label="Record invalid (dikarantina)" value={fmt(data.counts.invalid_records)} note="gagal validasi schema" />
			</Grid>

			<Card>
				<CardContent>
					<Typography variant="h6" gutterBottom>
						Aktivitas riset (run per hari)
					</Typography>
					<EChart
						height={280}
						option={{
							tooltip: { trigger: 'axis' },
							grid: { left: 50, right: 20, top: 30, bottom: 60 },
							legend: { data: ['Run unik', 'File record'] },
							xAxis: { type: 'category', data: perDay.map((d) => d.day) },
							yAxis: { type: 'value' },
							dataZoom: [{ type: 'slider' }],
							series: [
								{ name: 'Run unik', type: 'bar', data: perDay.map((d) => d.runs), itemStyle: { color: '#3949ab' } },
								{ name: 'File record', type: 'line', data: perDay.map((d) => d.files), itemStyle: { color: '#00838f' } },
							],
						}}
					/>
					<Typography variant="caption" color="text.secondary">
						Periode: {fmtDateTime(data.date_range.first)} — {fmtDateTime(data.date_range.last)} · sumber:{' '}
						{data.import.measurements_dir}
					</Typography>
				</CardContent>
			</Card>

			<Grid container spacing={2}>
				<Grid item xs={12} md={6}>
					<Card>
						<CardContent>
							<Typography variant="h6" gutterBottom>
								Sebaran per site
							</Typography>
							<DistTable rows={dist.bySite} />
							<Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
								Sebaran per kind
							</Typography>
							<DistTable rows={dist.byKind} />
						</CardContent>
					</Card>
				</Grid>
				<Grid item xs={12} md={6}>
					<Card>
						<CardContent>
							<Typography variant="h6" gutterBottom>
								Family result teratas
							</Typography>
							<Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
								{familyTop.map((f) => (
									<Chip key={f.family} label={`${f.family} · ${fmt(f.count)}`} variant="outlined" />
								))}
							</Stack>
							<Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
								Library
							</Typography>
							<Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
								{Object.entries(dist.byLibrary).map(([k, v]) => (
									<Chip key={k} label={`${k} · ${fmt(v)}`} variant="outlined" />
								))}
							</Stack>
						</CardContent>
					</Card>
				</Grid>
			</Grid>

			<Card>
				<CardContent>
					<Typography variant="h6" gutterBottom>
						Kembar angka (benchmark & test)
					</Typography>
					<Alert severity="info" sx={{ mb: 2 }}>
						Dashboard saat ini mendukung <b>kind=benchmark</b> dan <b>kind=test</b>. Record test akan muncul di
						menu <b>Tests</b> begitu data gtest mulai diimpor.
					</Alert>
					<DistTable rows={dist.byGenerator} label="Generator" />
				</CardContent>
			</Card>
		</Stack>
	);
}

function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
	return (
		<Grid item xs={12} sm={6} md={4}>
			<Card sx={{ height: '100%' }}>
				<CardContent>
					<Typography variant="body2" color="text.secondary">
						{label}
					</Typography>
					<Typography variant="h4">{value}</Typography>
					{note && (
						<Typography variant="caption" color="text.secondary">
							{note}
						</Typography>
					)}
				</CardContent>
			</Card>
		</Grid>
	);
}

function DistTable({ rows, label = 'Nilai' }: { rows: Record<string, number>; label?: string }) {
	const entries = Object.entries(rows).sort((a, b) => b[1] - a[1]);
	return (
		<Table size="small">
			<TableHead>
				<TableRow>
					<TableCell>{label}</TableCell>
					<TableCell align="right">File record</TableCell>
				</TableRow>
			</TableHead>
			<TableBody>
				{entries.map(([k, v]) => (
					<TableRow key={k}>
						<TableCell>
							{k}
							<DirtyBadge dirty={k.includes('dirty')} />
							<ExploratoryBadge exploratory={false} />
						</TableCell>
						<TableCell align="right">{fmt(v)}</TableCell>
					</TableRow>
				))}
				{!entries.length && (
					<TableRow>
						<TableCell colSpan={2} align="center">
							—
						</TableCell>
					</TableRow>
				)}
			</TableBody>
		</Table>
	);
}