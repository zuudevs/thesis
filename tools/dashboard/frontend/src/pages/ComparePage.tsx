import { useState } from 'react';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Grid,
    IconButton,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    TextField,
    Typography,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { apiGet, apiPost, fmt, fmtBytesPerSec, fmtDateTime, fmtSeconds, fmtSpeedup } from '../api/client';
import type { CompareResponse, Paged, ResultRow } from '../types';
import { DirtyBadge, ExploratoryBadge, EngineChip } from '../components/Badges';
import GuardrailBanner from '../components/GuardrailBanner';
import EChart from '../components/EChart';

interface Picked {
    run_id: string;
    corpus_key: string;
    name: string;
}

export default function ComparePage() {
    const [picked, setPicked] = useState<Picked[]>([]);
    const [query, setQuery] = useState<string>('');
    const [rows, setRows] = useState<Paged<ResultRow> | null>(null);
    const [result, setResult] = useState<CompareResponse | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [busy, setBusy] = useState(false);

    const search = () => {
        setError(null);
        apiGet<Paged<ResultRow>>('results', { q: query, page: 1, pageSize: 20, sort: 'date', sortDir: 'desc' })
            .then((r) => setRows(r))
            .catch((e) => setError(e));
    };

    const add = (item: Picked) => {
        if (picked.some((p) => p.run_id === item.run_id && p.corpus_key === item.corpus_key && p.name === item.name)) return;
        if (picked.length >= 8) {
            setError(new Error('Maksimal 8 result per perbandingan.'));
            return;
        }
        setPicked([...picked, item]);
    };

    const remove = (index: number) => setPicked(picked.filter((_, i) => i !== index));

    const runCompare = () => {
        if (picked.length < 2) {
            setError(new Error('Pilih minimal 2 result.'));
            return;
        }
        setBusy(true);
        setError(null);
        apiPost<CompareResponse>('compare', { items: picked })
            .then((r) => setResult(r))
            .catch((e) => setError(e))
            .finally(() => setBusy(false));
    };

    const chartRows = result?.rows ?? [];

    return (
        <Stack spacing={2}>
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Compare measurement
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                        Cari result (nama / purpose), tambahkan ke keranjang (maks 8), lalu bandingkan. Aturan AGENTS.md §4
                        diterapkan otomatis: lintas run_id / site / kind / korpus DIBLOKIR; lintas runtime/toolchain,
                        commit, dirty, dan exploratory diberi peringatan.
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                        <TextField
                            size="small"
                            fullWidth
                            label="Cari result (mis. D-file-store, nd9/s2-open, scanner64)"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && search()}
                        />
                        <Button variant="contained" onClick={search}>
                            Cari
                        </Button>
                    </Stack>

                    {error && <Alert severity="error" sx={{ mb: 2 }}>{error.message}</Alert>}

                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Hasil pencarian</TableCell>
                                <TableCell>Engine</TableCell>
                                <TableCell>Korpus</TableCell>
                                <TableCell>Waktu run</TableCell>
                                    <TableCell align="right">throughput B per detik</TableCell>
                                    <TableCell align="right">latency rerata</TableCell>
                                <TableCell />
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {(rows?.rows ?? []).map((r) => (
                                <TableRow key={r._id} hover>
                                    <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{r.name}</TableCell>
                                    <TableCell>
                                        <EngineChip engine={r.engine} />
                                    </TableCell>
                                    <TableCell>{r.corpus_name}</TableCell>
                                    <TableCell>
                                        {fmtDateTime(r.date_utc)}
                                        <DirtyBadge dirty={r.dirty} />
                                        <ExploratoryBadge exploratory={r.exploratory} />
                                    </TableCell>
                                    <TableCell align="right">{fmtBytesPerSec(r.metrics.bytes_per_second)}</TableCell>
                                    <TableCell align="right">{fmtSeconds(r.metrics.seconds_mean)}</TableCell>
                                    <TableCell align="right">
                                        <Button size="small" onClick={() => add({ run_id: r.run_id, corpus_key: r.corpus_key, name: r.name })}>
                                            Tambah
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {!rows?.rows?.length && (
                                <TableRow>
                                    <TableCell colSpan={7} align="center">
                                        {rows ? 'Tidak ada hasil.' : 'Cari result untuk mulai.'}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                        <Typography variant="h6">Keranjang ({picked.length})</Typography>
                        <Button variant="contained" disabled={busy || picked.length < 2} onClick={runCompare} startIcon={busy ? <CircularProgress size={16} /> : undefined}>
                            Bandingkan
                        </Button>
                    </Stack>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {picked.map((p, i) => (
                            <Chip
                                key={`${p.run_id}-${p.corpus_key}-${p.name}-${i}`}
                                label={`${p.name} · ${p.corpus_key}`}
                                onDelete={() => remove(i)}
                                deleteIcon={<DeleteIcon />}
                                variant="outlined"
                            />
                        ))}
                        {!picked.length && <Typography variant="caption" color="text.secondary">Keranjang kosong.</Typography>}
                    </Stack>
                    {picked.length === 1 && (
                        <Typography variant="caption" color="warning.main" display="block" sx={{ mt: 1 }}>
                            Tambah minimal 1 result lagi untuk membandingkan.
                        </Typography>
                    )}
                </CardContent>
            </Card>

            {result && (
                <>
                    <Card>
                        <CardContent>
                            <GuardrailBanner checks={result.checks} />
                            {result.valid ? (
                                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                    Referensi (item pertama): <b>{result.reference.name}</b> — semua rasio dihitung terhadap
                                    latency-nya.
                                </Typography>
                            ) : (
                                <Alert severity="error" sx={{ mt: 1 }}>
                                    Perbandingan tidak sah — perbaiki pilihan (lihat blok di atas). Hasil tetap ditampilkan
                                    untuk inspeksi, jangan dipakai sebagai bukti.
                                </Alert>
                            )}
                        </CardContent>
                    </Card>

                    <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <Card>
                                <CardContent>
                                    <Typography variant="h6" gutterBottom>
                                        Latency (µs/ms/s) — lebih rendah lebih baik
                                    </Typography>
                                    <EChart
                                        height={320}
                                        option={{
                                            tooltip: { trigger: 'axis' },
                                            grid: { left: 60, right: 40, top: 20, bottom: 60 },
                                            xAxis: { type: 'category', data: chartRows.map((r) => r.name), axisLabel: { rotate: 20, fontSize: 10, fontFamily: 'monospace' } },
                                            yAxis: { type: 'value' },
                                            series: [
                                                {
                                                    type: 'bar',
                                                    data: chartRows.map((r) => r.seconds_mean ?? 0),
                                                    itemStyle: { color: '#00838f' },
                                                    label: { show: true, position: 'top', fontSize: 10, formatter: (p: { value: number }) => fmtSeconds(p.value) },
                                                },
                                            ],
                                        }}
                                    />
                                </CardContent>
                            </Card>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Card>
                                <CardContent>
                                    <Typography variant="h6" gutterBottom>
                                        Throughput (B/detik) — lebih tinggi lebih baik
                                    </Typography>
                                    <EChart
                                        height={320}
                                        option={{
                                            tooltip: { trigger: 'axis' },
                                            grid: { left: 70, right: 40, top: 20, bottom: 60 },
                                            xAxis: { type: 'category', data: chartRows.map((r) => r.name), axisLabel: { rotate: 20, fontSize: 10, fontFamily: 'monospace' } },
                                            yAxis: { type: 'value' },
                                            series: [
                                                {
                                                    type: 'bar',
                                                    data: chartRows.map((r) => r.bytes_per_second ?? 0),
                                                    itemStyle: { color: '#3949ab' },
                                                    label: { show: true, position: 'top', fontSize: 10, formatter: (p: { value: number }) => fmtBytesPerSec(p.value) },
                                                },
                                            ],
                                        }}
                                    />
                                </CardContent>
                            </Card>
                        </Grid>
                    </Grid>

                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Rincian perbandingan
                            </Typography>
                            <Box sx={{ overflowX: 'auto' }}>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Result</TableCell>
                                            <TableCell>Engine</TableCell>
                                            <TableCell>Site / korpus</TableCell>
                                            <TableCell>Waktu run</TableCell>
                                    <TableCell align="right">speedup vs referensi</TableCell>
                                    <TableCell align="right">latency rerata</TableCell>
                                    <TableCell align="right">throughput B per detik</TableCell>
                                            <TableCell>Rationale</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {chartRows.map((r, i) => (
                                            <TableRow key={`${r.run_id}-${r.name}-${i}`} hover>
                                                <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                                                    {r.name}
                                                    <DirtyBadge dirty={r.dirty} />
                                                    <ExploratoryBadge exploratory={r.exploratory} />
                                                </TableCell>
                                                <TableCell>
                                                    <EngineChip engine={r.engine} />
                                                </TableCell>
                                                <TableCell>
                                                    {r.site} / {r.corpus_name}
                                                </TableCell>
                                                <TableCell>{fmtDateTime(r.date_utc)}</TableCell>
                                                <TableCell align="right">{fmtSpeedup(r.speedup_vs_ref)}</TableCell>
                                                <TableCell align="right">{fmtSeconds(r.seconds_mean)}</TableCell>
                                                <TableCell align="right">{fmtBytesPerSec(r.bytes_per_second)}</TableCell>
                                                <TableCell sx={{ maxWidth: 280 }}>
                                                    <Typography variant="caption">{r.purpose}</Typography>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </Box>
                        </CardContent>
                    </Card>
                </>
            )}
        </Stack>
    );
}
