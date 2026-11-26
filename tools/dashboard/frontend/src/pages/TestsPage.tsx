import { useEffect, useState } from 'react';
import {
    Alert,
    Card,
    CardContent,
    Chip,
    Pagination,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';
import { apiGet, fmt, fmtDateTime, fmtSeconds } from '../api/client';
import type { Paged, ResultRow } from '../types';
import { DirtyBadge, ExploratoryBadge, EngineChip } from '../components/Badges';

const PAGE_SIZE = 25;

const STATUS_COLOR: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    ok: 'success',
    skip: 'warning',
    fail: 'error',
};

/**
 * Tests — tabel result kind=test (gtest). Data belum ada hari ini; halaman
 * siap dipakai begitu record test mulai diimpor.
 */
export default function TestsPage() {
    const [data, setData] = useState<Paged<ResultRow> | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [page, setPage] = useState(1);
    const [status, setStatus] = useState('');

    useEffect(() => {
        let alive = true;
        const params: Record<string, unknown> = { kind: 'test', page, pageSize: PAGE_SIZE };
        if (status) params.status = status;
        apiGet<Paged<ResultRow>>('results', params)
            .then((d) => alive && setData(d))
            .catch((e) => alive && setError(e));
        return () => {
            alive = false;
        };
    }, [page, status]);

    const rows = data?.rows ?? [];
    const counts = rows.reduce<Record<string, number>>((acc, r) => {
        acc[r.status] = (acc[r.status] ?? 0) + 1;
        return acc;
    }, {});

    return (
        <Stack spacing={2}>
            {error && <Alert severity="error">Gagal memuat tests: {error.message}</Alert>}
            <Alert severity={data && data.total > 0 ? 'info' : 'warning'}>
                {data && data.total > 0
                    ? `${fmt(data.total)} result test terimpor (status: ${Object.entries(counts).map(([k, v]) => `${k}=${v}`).join(', ') || '—'}).`
                    : 'Belum ada record kind=test di out/measurements. Halaman ini siap: begitu record gtest diimpor, tabel akan terisi otomatis.'}
            </Alert>

            <Card>
                <CardContent>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                        <Typography variant="h6">Tests (gtest)</Typography>
                        {(['', 'ok', 'skip', 'fail'] as const).map((s) => (
                            <Chip
                                key={s || 'all'}
                                label={s || 'Semua status'}
                                size="small"
                                variant={status === s ? 'filled' : 'outlined'}
                                color={STATUS_COLOR[s] ?? 'default'}
                                onClick={() => {
                                    setPage(1);
                                    setStatus(s);
                                }}
                            />
                        ))}
                    </Stack>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Waktu run</TableCell>
                                <TableCell>Test</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Engine</TableCell>
                                    <TableCell align="right">latency rerata</TableCell>
                                <TableCell>Purpose</TableCell>
                                <TableCell>Basis paper</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {rows.map((r) => (
                                <TableRow key={r._id} hover>
                                    <TableCell>
                                        {fmtDateTime(r.date_utc)}
                                        <DirtyBadge dirty={r.dirty} />
                                        <ExploratoryBadge exploratory={r.exploratory} />
                                    </TableCell>
                                    <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{r.name}</TableCell>
                                    <TableCell>
                                        <Chip size="small" label={r.status} color={STATUS_COLOR[r.status] ?? 'default'} variant="outlined" />
                                    </TableCell>
                                    <TableCell>
                                        <EngineChip engine={r.engine} />
                                    </TableCell>
                                    <TableCell align="right">{fmtSeconds(r.metrics.seconds_mean)}</TableCell>
                                    <TableCell sx={{ maxWidth: 300 }}>{r.purpose}</TableCell>
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
                            {!rows.length && (
                                <TableRow>
                                    <TableCell colSpan={7} align="center">
                                        {data ? 'Tidak ada test pada filter ini.' : 'Memuat…'}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                    {data && data.total > PAGE_SIZE && (
                        <Stack alignItems="center" sx={{ mt: 2 }}>
                            <Pagination count={Math.ceil(data.total / PAGE_SIZE)} page={page} onChange={(_, p) => setPage(p)} size="small" />
                        </Stack>
                    )}
                </CardContent>
            </Card>
        </Stack>
    );
}
