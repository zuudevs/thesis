import { useState } from 'react';
import {
    Alert,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Divider,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { apiGet, apiPost, fmtDateTime } from '../api/client';
import type { ImportStatus, ImportSummary, InvalidRecordRow } from '../types';
import { useOverview } from '../hooks/useOverview';

export default function ImportPage() {
    const { data: overview, refresh: refreshOverview } = useOverview();
    const [status, setStatus] = useState<ImportStatus | null>(overview?.import ?? null);
    const [summary, setSummary] = useState<ImportSummary | null>(null);
    const [invalid, setInvalid] = useState<InvalidRecordRow[] | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [busy, setBusy] = useState(false);

    const loadStatus = () => {
        apiGet<ImportStatus>('imports/status').then(setStatus).catch((e) => setError(e));
        apiGet<{ rows: InvalidRecordRow[] }>('imports/invalid').then((r) => setInvalid(r.rows)).catch(() => setInvalid([]));
    };

    const scan = () => {
        setBusy(true);
        setError(null);
        apiPost<ImportSummary>('imports/scan')
            .then((s) => {
                setSummary(s);
                refreshOverview();
                loadStatus();
            })
            .catch((e) => setError(e))
            .finally(() => setBusy(false));
    };

    return (
        <Stack spacing={2}>
            {error && <Alert severity="error">Gagal impor: {error.message}</Alert>}

            <Card>
                <CardContent>
                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                        <Button variant="contained" onClick={scan} disabled={busy} startIcon={busy ? <CircularProgress size={16} /> : <RefreshIcon />}>
                            Re-scan & impor
                        </Button>
                        <Button onClick={loadStatus} disabled={busy}>
                            Muat status
                        </Button>
                    </Stack>

                    <Table size="small">
                        <TableBody>
                            <Row label="Folder sumber" value={status?.measurements_dir ?? overview?.import.measurements_dir ?? '—'} />
                            <Row label="Schema validasi" value={status?.schema_path ?? overview?.import.schema_path ?? '—'} />
                            <Row label="Impor terakhir" value={fmtDateTime(status?.last_import_at ?? overview?.import.last_import_at)} />
                            <Row label="Run terimpor" value={String(status?.counts.runs ?? overview?.counts.runs ?? 0)} />
                            <Row label="Result terimpor" value={String(status?.counts.results ?? overview?.counts.results ?? 0)} />
                            <Row label="Record invalid (dikarantina)" value={String(status?.counts.invalid ?? overview?.counts.invalid_records ?? 0)} />
                        </TableBody>
                    </Table>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                        Importer memvalidasi SETIAP file terhadap schemas/measurement.schema.json (sumber kebenaran). Record
                        gagal validasi tidak masuk basis analisis (AGENTS.md §4) — tercantum di bawah.
                    </Typography>
                </CardContent>
            </Card>

            {summary && (
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Hasil scan terakhir
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            <Chip label={`${summary.scanned_files} file dipindai`} variant="outlined" />
                            <Chip label={`${summary.created} baru`} color="success" variant="outlined" />
                            <Chip label={`${summary.updated} diperbarui`} color="info" variant="outlined" />
                            <Chip label={`${summary.unchanged} tak berubah`} variant="outlined" />
                            <Chip label={`${summary.invalid} gagal validasi`} color={summary.invalid ? 'error' : 'default'} variant="outlined" />
                            {summary.pruned ? <Chip label={`${summary.pruned} di-prune`} color="warning" variant="outlined" /> : null}
                        </Stack>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Record invalid (karantina)
                    </Typography>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>File</TableCell>
                                <TableCell>Alasan</TableCell>
                                <TableCell>Error schema</TableCell>
                                <TableCell>Dipindai</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {(invalid ?? []).map((r) => (
                                <TableRow key={r._id}>
                                    <TableCell sx={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all' }}>{r.file_name}</TableCell>
                                    <TableCell>{r.reason}</TableCell>
                                    <TableCell sx={{ maxWidth: 420 }}>
                                        {(r.validation_errors ?? []).slice(0, 4).map((e, i) => (
                                            <Typography key={i} variant="caption" display="block">
                                                {e.path || '/'}: {e.message}
                                            </Typography>
                                        ))}
                                        {(r.validation_errors ?? []).length > 4 && (
                                            <Typography variant="caption" color="text.secondary">
                                                +{(r.validation_errors ?? []).length - 4} lainnya…
                                            </Typography>
                                        )}
                                    </TableCell>
                                    <TableCell>{fmtDateTime(r.scanned_at)}</TableCell>
                                </TableRow>
                            ))}
                            {invalid && !invalid.length && (
                                <TableRow>
                                    <TableCell colSpan={4} align="center">
                                        Tidak ada record invalid. Semua file lolos validasi schema.
                                    </TableCell>
                                </TableRow>
                            )}
                            {!invalid && (
                                <TableRow>
                                    <TableCell colSpan={4} align="center">
                                        Klik "Muat status" untuk mengambil daftar invalid.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <Divider />
            <Typography variant="caption" color="text.secondary">
                CLI alternatif: <code>npm run import</code> (atau <code>npm run import:prune</code>) dari folder
                <code>tools/dashboard/</code> — setara dengan tombol Re-scan ini.
            </Typography>
        </Stack>
    );
}

function Row({ label, value }: { label: string; value: string }) {
    return (
        <TableRow>
            <TableCell sx={{ borderBottom: 'none', color: 'text.secondary', whiteSpace: 'nowrap', width: 240 }}>{label}</TableCell>
            <TableCell sx={{ borderBottom: 'none', wordBreak: 'break-all' }}>{value}</TableCell>
        </TableRow>
    );
}