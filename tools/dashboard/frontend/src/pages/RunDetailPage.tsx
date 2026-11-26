import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import {
    Alert,
    Box,
    Breadcrumbs,
    Card,
    CardContent,
    CircularProgress,
    Grid,
    Link,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    ToggleButton,
    ToggleButtonGroup,
    Typography,
} from '@mui/material';
import { apiGet, fmt, fmtBytes, fmtBytesPerSec, fmtDateTime, fmtSeconds } from '../api/client';
import type { RunDetail } from '../types';
import { DirtyBadge, ExploratoryBadge, EngineChip } from '../components/Badges';
import EChart from '../components/EChart';

export default function RunDetailPage() {
    const { runId } = useParams<{ runId: string }>();
    const [searchParams, setSearchParams] = useSearchParams();
    const corpus = searchParams.get('corpus') ?? '';
    const [data, setData] = useState<RunDetail | null>(null);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let alive = true;
        setData(null);
        apiGet<RunDetail>(`runs/${encodeURIComponent(runId ?? '')}`, corpus ? { corpus } : {})
            .then((d) => alive && setData(d))
            .catch((e) => alive && setError(e));
        return () => {
            alive = false;
        };
    }, [runId, corpus]);

    if (error) return <Alert severity="error">Gagal memuat detail run: {error.message}</Alert>;
    if (!data) return <CircularProgress />;

    const run = data.runs[0];
    const results = data.results;
    const engineCounts = results.reduce<Record<string, number>>((acc, r) => {
        acc[r.engine] = (acc[r.engine] ?? 0) + 1;
        return acc;
    }, {});

    return (
        <Stack spacing={2}>
            <Breadcrumbs>
                <Link href="/runs" onClick={(e) => e.preventDefault()}>
                    Runs
                </Link>
                <Typography color="text.primary" sx={{ fontFamily: 'monospace' }}>
                    {runId}
                </Typography>
            </Breadcrumbs>

            {data.corpora.length > 1 && (
                <Card>
                    <CardContent>
                        <Typography variant="subtitle2" gutterBottom>
                            Korpus dalam run ini ({data.corpora.length} file record):
                        </Typography>
                        <ToggleButtonGroup
                            size="small"
                            value={corpus}
                            exclusive
                            onChange={(_, v) => {
                                if (v === null) return;
                                setSearchParams(v ? { corpus: v } : {});
                            }}
                        >
                            {data.corpora.map((c) => (
                                <ToggleButton key={c} value={c}>
                                    {c}
                                </ToggleButton>
                            ))}
                        </ToggleButtonGroup>
                    </CardContent>
                </Card>
            )}

            <Grid container spacing={2}>
                <MetaCard title="Identitas run">
                    <Meta label="Waktu (UTC)" value={fmtDateTime(run.config.date_utc)} />
                    <Meta label="Site" value={run.site} />
                    <Meta label="Kind" value={run.kind} />
                    <Meta label="Generator" value={run.generator} />
                    <Meta label="Library" value={`${run.library.name} ${run.library.version}`} />
                    <Meta label="Runtime" value={run.derived.runtime_label} />
                    <Meta
                        label="Git"
                        value={`${run.git_commit.hash} (${run.git_commit.repo})`}
                        chips={
                            <>
                                <DirtyBadge dirty={run.derived.dirty} />
                                <ExploratoryBadge exploratory={run.derived.exploratory} />
                            </>
                        }
                    />
                </MetaCard>
                <MetaCard title="Mesin">
                    <Meta label="Hostname" value={run.host.hostname} />
                    <Meta label="CPU" value={`${run.host.cpu_model} · ${run.host.cpu_cores ?? '?'} core · ${run.host.cpu_freq ?? ''}`} />
                    <Meta label="OS" value={`${run.host.os} ${run.host.os_version ?? ''} (${run.host.arch})`} />
                    <Meta label="Toolchain" value={run.host.toolchain ?? '—'} />
                </MetaCard>
                <MetaCard title="Korpus & konfigurasi">
                    <Meta label="Korpus" value={run.corpus.name} />
                    <Meta label="Dokumen" value={fmt(run.corpus.document_count)} />
                    <Meta label="Ukuran" value={fmtBytes(run.corpus.total_bytes)} />
                    <Meta label="sha256 korpus" value={run.corpus.sha256} raw />
                    <Meta
                        label="Iterations / repeats"
                        value={`${run.config.iterations ?? '—'} / ${run.config.repeats ?? '—'}`}
                    />
                    <Meta label="Warmup" value={String(run.config.warmup_runs ?? '—')} />
                    <Meta label="Scanner mode" value={run.config.scanner_mode ?? '—'} />
                    {run.config.notes ? <Meta label="Catatan" value={String(run.config.notes)} wrap /> : null}
                </MetaCard>
            </Grid>

            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Throughput per result
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                        {Object.entries(engineCounts).map(([engine, n]) => (
                            <EngineChip key={engine} engine={`${engine} x${n}`} />
                        ))}
                    </Stack>
                    <EChart
                        height={Math.max(280, results.length * 22)}
                        option={{
                            tooltip: {
                                trigger: 'axis',
                                axisPointer: { type: 'shadow' },
                                formatter: (p: unknown) => {
                                    const arr = p as { name: string; value: number }[];
                                    const first = arr[0];
                                    return `${first.name}<br/>${fmtBytesPerSec(first.value)}`;
                                },
                            },
                            grid: { left: 10, right: 90, top: 20, bottom: 10, containLabel: true },
                            xAxis: { type: 'value' },
                            yAxis: {
                                type: 'category',
                                data: results.map((r) => r.name).reverse(),
                                axisLabel: { fontFamily: 'monospace', fontSize: 11 },
                            },
                            series: [
                                {
                                    type: 'bar',
                                    data: results
                                        .map((r) => r.metrics.bytes_per_second ?? 0)
                                        .reverse(),
                                    itemStyle: { color: '#3949ab' },
                                    label: {
                                        show: true,
                                        position: 'right',
                                        formatter: (p: { value: number }) => fmtBytesPerSec(p.value),
                                        fontSize: 10,
                                    },
                                },
                            ],
                        }}
                    />
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Results ({results.length})
                    </Typography>
                    <Box sx={{ overflowX: 'auto' }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Nama</TableCell>
                                    <TableCell>Engine</TableCell>
                                    <TableCell align="right">latency rerata</TableCell>
                                    <TableCell align="right">speed bytes</TableCell>
                                    <TableCell align="right">dokumen per detik</TableCell>
                                    <TableCell>Rationale - purpose</TableCell>
                                    <TableCell>Basis paper</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {results.map((r) => (
                                    <TableRow key={r._id} hover>
                                        <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{r.name}</TableCell>
                                        <TableCell>
                                            <EngineChip engine={r.engine} />
                                            {r.mode ? (
                                                <Typography variant="caption" display="block" color="text.secondary">
                                                    mode: {r.mode}
                                                </Typography>
                                            ) : null}
                                        </TableCell>
                                        <TableCell align="right">{fmtSeconds(r.metrics.seconds_mean)}</TableCell>
                                        <TableCell align="right">{fmtBytesPerSec(r.metrics.bytes_per_second)}</TableCell>
                                        <TableCell align="right">{fmt(r.metrics.documents_per_second)}</TableCell>
                                        <TableCell sx={{ maxWidth: 320 }}>
                                            {r.purpose}
                                            <Typography variant="caption" display="block" color="text.secondary">
                                                status: {r.status}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Stack spacing={0.25}>
                                                {(r.basis_papers ?? []).map((paper) => (
                                                    <Typography key={paper} variant="caption" sx={{ fontFamily: 'monospace' }}>
                                                        {paper}
                                                    </Typography>
                                                ))}
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </Box>
                </CardContent>
            </Card>
        </Stack>
    );
}

function MetaCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
                <CardContent>
                    <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        {title}
                    </Typography>
                    <Table size="small">
                        <TableBody>{children}</TableBody>
                    </Table>
                </CardContent>
            </Card>
        </Grid>
    );
}

function Meta({
    label,
    value,
    chips,
    wrap,
    raw,
}: {
    label: string;
    value: string;
    chips?: React.ReactNode;
    wrap?: boolean;
    raw?: boolean;
}) {
    return (
        <TableRow>
            <TableCell sx={{ borderBottom: 'none', color: 'text.secondary', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                {label}
            </TableCell>
            <TableCell sx={{ borderBottom: 'none', wordBreak: raw ? 'break-all' : 'break-word', whiteSpace: wrap ? 'normal' : 'nowrap', fontFamily: raw ? 'monospace' : undefined, fontSize: raw ? 11 : undefined }}>
                {value}
                {chips}
            </TableCell>
        </TableRow>
    );
}
