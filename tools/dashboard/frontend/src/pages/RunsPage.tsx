import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
	Card,
	CardContent,
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableRow,
	Stack,
	Pagination,
	Typography,
	IconButton,
	Tooltip,
	Box,
	Collapse,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { apiGet, fmt, fmtBytesPerSec, fmtDateTime } from '../api/client';
import Alert from '@mui/material/Alert';
import type { Paged, RunRow } from '../types';
import FilterPanel, { EMPTY_FILTERS, type FilterValues } from '../components/FilterPanel';
import { paramsToFilters, filtersToParams } from '../hooks/filters';
import { useOverview } from '../hooks/useOverview';
import { DirtyBadge, ExploratoryBadge, EngineChip } from '../components/Badges';

const PAGE_SIZE = 25;

export default function RunsPage() {
	const [searchParams, setSearchParams] = useSearchParams();
	const [values, setValues] = useState<FilterValues>(() => paramsToFilters(searchParams));
	const [data, setData] = useState<Paged<RunRow> | null>(null);
	const [error, setError] = useState<Error | null>(null);
	const [page, setPage] = useState(1);
	const { data: overview } = useOverview();

	// Filter → URL (biar state bertahan saat reload / bisa dibagikan).
	useEffect(() => {
		setSearchParams(filtersToParams(values), { replace: true });
		setPage(1);
	}, [values, setSearchParams]);

	useEffect(() => {
		let alive = true;
		const params: Record<string, unknown> = { ...values, page, pageSize: PAGE_SIZE };
		apiGet<Paged<RunRow>>('runs', params)
			.then((d) => alive && setData(d))
			.catch((e) => alive && setError(e));
		return () => {
			alive = false;
		};
	}, [values, page]);

	const rows = data?.rows ?? [];
	const pageCount = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));

	return (
		<Stack spacing={2}>
			<Card>
				<CardContent>
					<FilterPanel value={values} onChange={setValues} facets={overview?.facets} />
				</CardContent>
			</Card>

			{error && <Alert severity="error">Gagal memuat runs: {error.message}</Alert>}

			<Card>
				<CardContent>
					<Stack direction="row" justifyContent="space-between" alignItems="center">
						<Typography variant="h6">
							{data ? `${fmt(data.total)} file record` : 'Memuat…'}
						</Typography>
						<Pagination
							count={pageCount}
							page={page}
							onChange={(_, p) => setPage(p)}
							color="primary"
							size="small"
						/>
					</Stack>
					<Box sx={{ overflowX: 'auto' }}>
						<Table size="small">
							<TableHead>
								<TableRow>
									<TableCell>Waktu (UTC)</TableCell>
									<TableCell>run_id</TableCell>
									<TableCell>Site</TableCell>
									<TableCell>Korpus</TableCell>
									<TableCell>Kind / Generator</TableCell>
									<TableCell>Library / runtime</TableCell>
									<TableCell>Engines</TableCell>
									<TableCell align="right">Result</TableCell>
									<TableCell align="right">Throughput terbaik</TableCell>
									<TableCell />
								</TableRow>
							</TableHead>
							<TableBody>
								{rows.map((row) => (
									<TableRow key={row._id} hover>
										<TableCell>{fmtDateTime(row.derived.date_utc)}</TableCell>
										<TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
											{row.run_id}
											<DirtyBadge dirty={row.derived.dirty} />
											<ExploratoryBadge exploratory={row.derived.exploratory} />
										</TableCell>
										<TableCell>{row.site}</TableCell>
										<TableCell>{row.corpus.name}</TableCell>
										<TableCell>
											{row.kind}
											<br />
											<Typography variant="caption" color="text.secondary">
												{row.generator}
											</Typography>
										</TableCell>
										<TableCell>
											{row.library.name}
											<br />
											<Typography variant="caption" color="text.secondary">
												{row.derived.runtime_label}
											</Typography>
										</TableCell>
										<TableCell>
											<Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
												{row.derived.engines.map((e) => (
													<EngineChip key={e} engine={e} />
												))}
											</Stack>
										</TableCell>
										<TableCell align="right">{fmt(row.derived.n_results)}</TableCell>
										<SpeedCell row={row} />
										<TableCell align="right">
											<Tooltip title="Buka detail run">
												<IconButton size="small" component="a" href={`/runs/${row.run_id}`}>
													<OpenInNewIcon fontSize="small" />
												</IconButton>
											</Tooltip>
										</TableCell>
									</TableRow>
								))}
								{!rows.length && (
									<TableRow>
										<TableCell colSpan={10} align="center">
											Tidak ada run yang cocok dengan filter.
										</TableCell>
									</TableRow>
								)}
							</TableBody>
						</Table>
					</Box>
				</CardContent>
			</Card>
		</Stack>
	);
}

/** Throughput terbaik dalam run (bytes/s) + nama result penghasilnya. */
function SpeedCell({ row }: { row: RunRow }) {
	const [open, setOpen] = useState(false);
	const { best, bestName } = useMemo(() => {
		let value = 0;
		let name = '';
		for (const r of row.results_brief) {
			if (r.bytes_per_second && r.bytes_per_second > value) {
				value = r.bytes_per_second;
				name = r.name;
			}
		}
		return { best: value, bestName: name };
	}, [row]);

	return (
		<TableCell align="right">
			<Tooltip title={bestName || '—'}>
				<span onClick={() => setOpen(!open)} style={{ cursor: 'pointer', textDecoration: 'underline dotted' }}>
					{fmtBytesPerSec(best || null)}
				</span>
			</Tooltip>
			<Collapse in={open}>
				<Typography variant="caption" display="block" color="text.secondary">
					{bestName}
				</Typography>
			</Collapse>
		</TableCell>
	);
}