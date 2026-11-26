import { Grid, TextField, MenuItem, FormControlLabel, Switch, Button, Box } from '@mui/material';
import type { Overview } from '../types';
import { fmtDateInput } from '../hooks/filters';

export interface FilterValues {
	site: string;
	kind: string;
	library: string;
	corpus: string;
	generator: string;
	engine: string;
	family: string;
	mode: string;
	dirty: string; // '' | 'true' | 'false'
	exploratory: string;
	from: string; // YYYY-MM-DD or ''
	to: string;
	q: string;
}

export const EMPTY_FILTERS: FilterValues = {
	site: '',
	kind: '',
	library: '',
	corpus: '',
	generator: '',
	engine: '',
	family: '',
	mode: '',
	dirty: '',
	exploratory: '',
	from: '',
	to: '',
	q: '',
};

interface Props {
	value: FilterValues;
	onChange: (next: FilterValues) => void;
	facets?: Overview['facets'];
	showDate?: boolean;
	showSearch?: boolean;
	showGenerator?: boolean;
}

function MultiSelect({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (v: string) => void }) {
	return (
		<TextField select size="small" fullWidth label={label} value={value} onChange={(e) => onChange(e.target.value)} SelectProps={{ displayEmpty: true }}>
			<MenuItem value="">Semua</MenuItem>
			{options.map((o) => (
				<MenuItem key={o} value={o}>
					{o}
				</MenuItem>
			))}
		</TextField>
	);
}

/** Panel filter bersama untuk halaman Runs & Analisis. */
export default function FilterPanel({
	value,
	onChange,
	facets,
	showDate = true,
	showSearch = true,
	showGenerator = false,
}: Props) {
	const set = (patch: Partial<FilterValues>) => onChange({ ...value, ...patch });

	return (
		<Box>
			<Grid container spacing={2}>
				{showSearch && (
					<Grid item xs={12} sm={6} md={3}>
						<TextField
							size="small"
							fullWidth
							label="Pencarian (run_id, nama result, purpose, notes)"
							value={value.q}
							onChange={(e) => set({ q: e.target.value })}
						/>
					</Grid>
				)}
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Site" options={facets?.sites ?? []} value={value.site} onChange={(v) => set({ site: v })} />
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Kind" options={facets?.kinds ?? []} value={value.kind} onChange={(v) => set({ kind: v })} />
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Library" options={facets?.libraries ?? []} value={value.library} onChange={(v) => set({ library: v })} />
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Korpus" options={facets?.corpora ?? []} value={value.corpus} onChange={(v) => set({ corpus: v })} />
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Engine" options={facets?.engines ?? []} value={value.engine} onChange={(v) => set({ engine: v })} />
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Family" options={facets?.families ?? []} value={value.family} onChange={(v) => set({ family: v })} />
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<MultiSelect label="Mode scanner" options={facets?.modes ?? []} value={value.mode} onChange={(v) => set({ mode: v })} />
				</Grid>
				{showGenerator && (
					<Grid item xs={6} sm={3} md={2}>
						<MultiSelect label="Generator" options={facets?.generators ?? []} value={value.generator} onChange={(v) => set({ generator: v })} />
					</Grid>
				)}
				<Grid item xs={6} sm={3} md={2}>
					<TextField
						select
						size="small"
						fullWidth
						label="Tree state"
						value={value.dirty}
						onChange={(e) => set({ dirty: e.target.value })}
					>
						<MenuItem value="">Semua</MenuItem>
						<MenuItem value="false">Bersih (clean)</MenuItem>
						<MenuItem value="true">Dirty</MenuItem>
					</TextField>
				</Grid>
				<Grid item xs={6} sm={3} md={2}>
					<TextField
						select
						size="small"
						fullWidth
						label="Sifat run"
						value={value.exploratory}
						onChange={(e) => set({ exploratory: e.target.value })}
					>
						<MenuItem value="">Semua</MenuItem>
						<MenuItem value="false">Acceptance</MenuItem>
						<MenuItem value="true">Exploratory</MenuItem>
					</TextField>
				</Grid>
				{showDate && (
					<>
						<Grid item xs={6} sm={3} md={2}>
							<TextField
								size="small"
								fullWidth
								type="date"
								label="Dari"
								InputLabelProps={{ shrink: true }}
								value={fmtDateInput(value.from)}
								onChange={(e) => set({ from: e.target.value })}
							/>
						</Grid>
						<Grid item xs={6} sm={3} md={2}>
							<TextField
								size="small"
								fullWidth
								type="date"
								label="Sampai"
								InputLabelProps={{ shrink: true }}
								value={fmtDateInput(value.to)}
								onChange={(e) => set({ to: e.target.value })}
							/>
						</Grid>
					</>
				)}
				<Grid item xs={12}>
					<FormControlLabel control={<Switch size="small" checked={value.dirty === 'true'} onChange={(e) => set({ dirty: e.target.checked ? 'true' : '' })} />} label="Hanya dirty" />
					<FormControlLabel control={<Switch size="small" checked={value.dirty === 'false'} onChange={(e) => set({ dirty: e.target.checked ? 'false' : '' })} />} label="Hanya bersih" />
					<Button size="small" onClick={() => onChange(EMPTY_FILTERS)} sx={{ ml: 2 }}>
						Reset filter
					</Button>
				</Grid>
			</Grid>
		</Box>
	);
}