import { useState } from 'react';
import {
    Alert,
    Box,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    FormControl,
    Grid,
    InputLabel,
    MenuItem,
    Select,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    Tab,
    Tabs,
    Typography,
} from '@mui/material';
import { apiGet, fmt, fmtDateTime, fmtSpeedup } from '../api/client';
import type { AcceptanceResponse, ScannerRun, TrendResponse } from '../types';
import { useOverview } from '../hooks/useOverview';
import FilterPanel, { EMPTY_FILTERS, type FilterValues } from '../components/FilterPanel';
import { DirtyBadge, ExploratoryBadge, SpeedupChip } from '../components/Badges';
import EChart from '../components/EChart';

const METRICS = [
    { value: 'bytes_per_second', label: 'Throughput (B/detik)' },
    { value: 'documents_per_second', label: 'Dokumen per detik' },
    { value: 'items_per_second', label: 'Item per detik' },
    { value: 'seconds_mean', label: 'Waktu rerata (detik)' },
    { value: 'cpu_seconds', label: 'CPU (detik)' },
];

const SERIES_COLORS = ['#3949ab', '#00838f', '#e65100', '#6a1b9a', '#2e7d32', '#c62828', '#4527a0', '#ef6c00'];

export default function AnalysisPage() {
    const [tab, setTab] = useState(0);
    return (
        <Stack spacing={2}>
            <Tabs value={tab} onChange={(_, v) => setTab(v)}>
                <Tab label="Timeline throughput" />
                <Tab label="Panel acceptance" />
                <Tab label="Mode scanner" />
            </Tabs>
            {tab === 0 && <TrendTab />}
            {tab === 1 && <AcceptanceTab />}
            {tab === 2 && <ScannerTab />}
        </Stack>
    );
}

function TrendTab() {
    const { data: overview } = useOverview();
    const [filters, setFilters] = useState<FilterValues>({ ...EMPTY_FILTERS });
    const [metric, setMetric] = useState('bytes_per_second');
    const [resp, setResp] = useState<TrendResponse | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [loading, setLoading] = useState(false);

    const load = () => {
        setLoading(true);
        setError(null);
        apiGet<TrendResponse>('charts/trend', {
            metric,
            site: filters.site,
            corpus: filters.corpus,
            engine: filters.engine,
            family: filters.family,
            kind: filters.kind,
            library: filters.library,
            mode: filters.mode,
            from: filters.from,
            to: filters.to,
        })
            .then((r) => {
                setResp(r);
                setLoading(false);
            })
            .catch((e) => {
                setError(e);
                setLoading(false);
            });
    };

    const top = (resp?.series ?? []).slice(0, 12);
    const dates = [...new Set(top.flatMap((s) => s.points.map((p) => p.date)))].sort();
    const series = top.map((s, i) => ({
        name: s.key,
        type: 'line' as const,
        smooth: true,
        symbolSize: 6,
        data: dates.map((d) => {
            const point = s.points.find((p) => p.date === d);
            return point ? point.value : null;
        }),
        itemStyle: { color: SERIES_COLORS[i % SERIES_COLORS.length] },
        lineStyle: { color: SERIES_COLORS[i % SERIES_COLORS.length] },
    }));

    const inverted = metric === 'seconds_mean' || metric === 'cpu_seconds';

    return (
        <Stack spacing={2}>
            <Card>
                <CardContent>
                    <FilterPanel value={filters} onChange={setFilters} facets={overview?.facets} showSearch={false} />
                    <Stack direction="row" spacing={2} sx={{ mt: 2 }} alignItems="center">
                        <FormControl size="small" sx={{ minWidth: 220 }}>
                            <InputLabel>Metrik</InputLabel>
                            <Select value={metric} label="Metrik" onChange={(e) => setMetric(e.target.value)}>
                                {METRICS.map((m) => (
                                    <MenuItem key={m.value} value={m.value}>
                                        {m.label}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <Chip
                            label={inverted ? 'Lebih RENDAH = lebih baik (waktu)' : 'Lebih TINGGI = lebih baik (throughput)'}
                            color={inverted ? 'warning' : 'info'}
                            size="small"
                        />
                        <Chip label={`${resp?.series.length ?? 0} seri (maks 12 ditampilkan)`} variant="outlined" size="small" />
                    </Stack>
                    <Box sx={{ mt: 2 }}>
                        <button onClick={load} disabled={loading} style={{ padding: '6px 16px', cursor: 'pointer' }}>
                            {loading ? 'Memuat…' : 'Tarik data'}
                        </button>
                    </Box>
                </CardContent>
            </Card>

            {error && <Alert severity="error">Gagal memuat tren: {error.message}</Alert>}
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Evolusi metrik riset (rata-rata harian per nama result)
                    </Typography>
                    {loading && <CircularProgress />}
                    {!loading && !series.length && <Alert severity="info">Tarik data untuk menampilkan tren.</Alert>}
                    {!loading && series.length > 0 && (
                        <EChart
                            height={480}
                            option={{
                                tooltip: { trigger: 'axis' },
                                legend: { type: 'scroll', bottom: 0 },
                                grid: { left: 70, right: 30, top: 30, bottom: 90 },
                                xAxis: { type: 'category', data: dates },
                                yAxis: { type: 'value', scale: true },
                                dataZoom: [{ type: 'slider' }, { type: 'inside' }],
                                series,
                            }}
                        />
                    )}
                    <Typography variant="caption" color="text.secondary">
                        Satu titik = median antar run pada tanggal tersebut untuk (nama result + korpus + site + engine). Data
                        lintas site tidak dicampur (lihat filter).
                    </Typography>
                </CardContent>
            </Card>
        </Stack>
    );
}

function AcceptanceTab() {
    const { data: overview } = useOverview();
    const [filters, setFilters] = useState<FilterValues>({ ...EMPTY_FILTERS });
    const [resp, setResp] = useState<AcceptanceResponse | null>(null);
    const [error, setError] = useState<Error | null>(null);

    const load = () => {
        apiGet<AcceptanceResponse>('charts/acceptance', {
            threshold: 1.5,
            site: filters.site,
            corpus: filters.corpus,
            family: filters.family,
            kind: filters.kind,
            library: filters.library,
            from: filters.from,
            to: filters.to,
        })
            .then(setResp)
            .catch((e) => setError(e));
    };

    const latest = resp?.latest ?? [];
    const met = latest.filter((p) => p.status === 'tercapai').length;

    return (
        <Stack spacing={2}>
            <Card>
                <CardContent>
                    <FilterPanel value={filters} onChange={setFilters} facets={overview?.facets} showSearch={false} showGenerator />
                    <Box sx={{ mt: 2 }}>
                        <button onClick={load} style={{ padding: '6px 16px', cursor: 'pointer' }}>
                            Muat panel acceptance
                        </button>
                    </Box>
                </CardContent>
            </Card>
            {error && <Alert severity="error">Gagal memuat acceptance: {error.message}</Alert>}

            <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="body2" color="text.secondary">
                                Pasangan terbaru terpantau
                            </Typography>
                            <Typography variant="h4">{latest.length}</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="body2" color="text.secondary">
                                Mencapai ambang 1.5x
                            </Typography>
                            <Typography variant="h4" color="success.main">
                                {met}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="body2" color="text.secondary">
                                Belum mencapai ambang
                            </Typography>
                            <Typography variant="h4" color="error.main">
                                {latest.length - met}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Run TERBARU per subjek (pasangan baseline v8 vs candidate, dalam satu run_id)
                    </Typography>
                    <Box sx={{ overflowX: 'auto' }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Site</TableCell>
                                    <TableCell>Family</TableCell>
                                    <TableCell>Subjek</TableCell>
                                    <TableCell>Korpus</TableCell>
                                    <TableCell>Waktu run</TableCell>
                                    <TableCell align="right">speedup x</TableCell>
                                    <TableCell align="right">baseline waktu rerata</TableCell>
                                    <TableCell align="right">candidate waktu rerata</TableCell>
                                    <TableCell>Status</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {latest.map((p) => (
                                    <TableRow key={`${p.site}-${p.family}-${p.subject_key}-${p.corpus_name}-${p.candidate.engine}`} hover>
                                        <TableCell>{p.site}</TableCell>
                                        <TableCell>{p.family}</TableCell>
                                        <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{p.subject_key}</TableCell>
                                        <TableCell>{p.corpus_name}</TableCell>
                                        <TableCell>
                                            {fmtDateTime(p.date_utc)}
                                            <DirtyBadge dirty={p.dirty} />
                                            <ExploratoryBadge exploratory={p.exploratory} />
                                        </TableCell>
                                        <TableCell align="right">{fmtSpeedup(p.speedup)}</TableCell>
                                        <TableCell align="right">{fmt(p.baseline.seconds_mean * 1e6, 1)} µs</TableCell>
                                        <TableCell align="right">{fmt(p.candidate.seconds_mean * 1e6, 1)} µs</TableCell>
                                        <TableCell>
                                            <SpeedupChip value={p.speedup} threshold={resp?.threshold ?? 1.5} />
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {!latest.length && (
                                    <TableRow>
                                        <TableCell colSpan={9} align="center">
                                            {resp ? 'Tidak ada pasangan baseline/candidate pada filter ini.' : 'Klik "Muat panel acceptance".'}
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </Box>
                </CardContent>
            </Card>

            {resp && resp.trend.length > 1 && (
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Tren speedup (semua pasangan, kronologis)
                        </Typography>
                        <SpeedupTrend trend={resp.trend} threshold={resp.threshold} />
                    </CardContent>
                </Card>
            )}
        </Stack>
    );
}

function SpeedupTrend({ trend, threshold }: { trend: AcceptanceResponse['trend']; threshold: number }) {
    const seriesMap = new Map<string, { date: string; run_id: string; speedup: number }[]>();
    for (const p of trend) {
        const key = `${p.family}/${p.subject_key}@${p.candidate_engine}`;
        if (!seriesMap.has(key)) seriesMap.set(key, []);
        seriesMap.get(key)!.push({ date: (p.date ?? '').slice(0, 10), run_id: p.run_id, speedup: p.speedup });
    }
    const keys = [...seriesMap.keys()].slice(0, 8);
    const dates = [...new Set(keys.flatMap((k) => seriesMap.get(k)!.map((p) => p.date)))].sort();
    const series = keys.map((k, i) => ({
        name: k,
        type: 'line' as const,
        smooth: true,
        symbolSize: 6,
        data: dates.map((d) => {
            const point = seriesMap.get(k)!.find((p) => p.date === d);
            return point ? Number(point.speedup.toFixed(4)) : null;
        }),
        itemStyle: { color: SERIES_COLORS[i % SERIES_COLORS.length] },
        lineStyle: { color: SERIES_COLORS[i % SERIES_COLORS.length] },
    }));

    return (
        <EChart
            height={420}
            option={{
                tooltip: { trigger: 'axis' },
                legend: { type: 'scroll', bottom: 0 },
                grid: { left: 50, right: 30, top: 30, bottom: 90 },
                xAxis: { type: 'category', data: dates },
                yAxis: { type: 'value', scale: true },
                dataZoom: [{ type: 'slider' }],
                series: [
                    ...series,
                    {
                        name: `ambang ${threshold}x`,
                        type: 'line',
                        data: dates.map(() => threshold),
                        markLine: { silent: true },
                        lineStyle: { type: 'dashed', color: '#c62828' },
                        itemStyle: { color: '#c62828' },
                        symbol: 'none',
                    },
                ],
            }}
        />
    );
}

function ScannerTab() {
    const [resp, setResp] = useState<ScannerRun[] | null>(null);
    const [error, setError] = useState<Error | null>(null);

    const load = () => {
        apiGet<{ runs: ScannerRun[] }>('charts/scanner').then((r) => setResp(r.runs)).catch((e) => setError(e));
    };

    const runs = resp ?? [];
    const latest = runs.slice(0, 8);

    return (
        <Stack spacing={2}>
            <Card>
                <CardContent>
                    <button onClick={load} style={{ padding: '6px 16px', cursor: 'pointer' }}>
                        Muat data mode scanner
                    </button>
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1 }}>
                        Run dengan config.scanner_mode=multi mengukur 5 varian dalam satu run_id (satu run, valid di banding).
                    </Typography>
                </CardContent>
            </Card>
            {error && <Alert severity="error">Gagal memuat scanner: {error.message}</Alert>}

            {latest.map((run) => {
                const modes = [...run.modes].sort((a, b) => a.mode.localeCompare(b.mode));
                const ref = modes.find((m) => m.mode === 'reference')?.bytes_per_second ?? null;
                return (
                    <Card key={`${run.run_id}-${run.corpus_name}`}>
                        <CardContent>
                            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                                <Typography variant="subtitle1" sx={{ fontFamily: 'monospace' }}>
                                    {run.run_id}
                                </Typography>
                                <Chip size="small" label={run.site} variant="outlined" />
                                <Chip size="small" label={run.corpus_name} variant="outlined" />
                                <Typography variant="caption" color="text.secondary">
                                    {fmtDateTime(run.date_utc)}
                                </Typography>
                            </Stack>
                            <EChart
                                height={260}
                                option={{
                                    tooltip: { trigger: 'axis' },
                                    grid: { left: 70, right: 40, top: 20, bottom: 30 },
                                    xAxis: { type: 'category', data: modes.map((m) => m.mode) },
                                    yAxis: { type: 'value' },
                                    series: [
                                        {
                                            type: 'bar',
                                            data: modes.map((m) => m.bytes_per_second ?? 0),
                                            itemStyle: { color: '#3949ab' },
                                            label: { show: true, position: 'top', formatter: (p: { value: number }) => fmt(p.value / 1e6, 0) + ' MB/s', fontSize: 10 },
                                        },
                                    ],
                                }}
                            />
                            {ref ? (
                                <Typography variant="caption" color="text.secondary">
                                    Tercepat: {fmtSpeedup(Math.max(...modes.map((m) => m.bytes_per_second ?? 0)) / ref)} vs
                                    reference.
                                </Typography>
                            ) : null}
                        </CardContent>
                    </Card>
                );
            })}
            {!latest.length && resp && <Alert severity="info">Tidak ada run multi-scanner pada data terimpor.</Alert>}
        </Stack>
    );
}
