import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
	AppBar,
	Box,
	Collapse,
	Divider,
	Drawer,
	IconButton,
	List,
	ListItemButton,
	ListItemIcon,
	ListItemText,
	ListSubheader,
	Toolbar,
	Tooltip,
	Typography,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import TableRowsIcon from '@mui/icons-material/TableRows';
import InsightsIcon from '@mui/icons-material/Insights';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import ScienceIcon from '@mui/icons-material/Science';
import UploadIcon from '@mui/icons-material/Upload';
import DownloadingIcon from '@mui/icons-material/Downloading';
import { useOverview } from '../hooks/useOverview';
import { fmtDateTime } from '../api/client';

const NAV = [
	{ to: '/', label: 'Ringkasan', icon: <DashboardIcon /> },
	{ to: '/runs', label: 'Runs', icon: <TableRowsIcon /> },
	{ to: '/analisis', label: 'Analisis', icon: <InsightsIcon /> },
	{ to: '/compare', label: 'Compare', icon: <CompareArrowsIcon /> },
	{ to: '/tests', label: 'Tests', icon: <ScienceIcon /> },
	{ to: '/import', label: 'Import', icon: <UploadIcon /> },
];

const DRAWER_WIDTH = 240;

export default function Layout() {
	const [open, setOpen] = useState(true);
	const { data } = useOverview();

	const counts = data?.counts;

	return (
		<Box sx={{ display: 'flex', minHeight: '100vh' }}>
			<AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
				<Toolbar>
					<IconButton edge="start" color="inherit" onClick={() => setOpen(!open)} sx={{ mr: 1 }}>
						<MenuIcon />
					</IconButton>
					<Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
						Dashboard Monitoring Riset — ze_json vs saq-baseline
					</Typography>
					{counts && (
						<Typography variant="body2" sx={{ opacity: 0.85 }}>
							{counts.runs} run · {counts.results} result · {counts.invalid_records} invalid
						</Typography>
					)}
				</Toolbar>
			</AppBar>

			<Drawer
				variant="permanent"
				sx={{
					width: open ? DRAWER_WIDTH : 73,
					flexShrink: 0,
					'& .MuiDrawer-paper': {
						width: open ? DRAWER_WIDTH : 73,
						boxSizing: 'border-box',
						overflowX: 'hidden',
						transition: 'width 0.2s',
					},
				}}
			>
				<Toolbar />
				<Box sx={{ overflow: 'auto' }}>
					<List>
						{NAV.map((item) => (
							<ListItemButton
								key={item.to}
								component={NavLink}
								to={item.to}
								end={item.to === '/'}
								sx={{
									minHeight: 48,
									px: 2.5,
									'&.active': { bgcolor: 'action.selected' },
								}}
							>
								<ListItemIcon sx={{ minWidth: 0, mr: open ? 2 : 'auto', justifyContent: 'center' }}>
									{item.icon}
								</ListItemIcon>
								<Collapse in={open} orientation="horizontal">
									<ListItemText primary={item.label} />
								</Collapse>
							</ListItemButton>
						))}
					</List>
					{open && (
						<>
							<Divider />
							<ListSubheader sx={{ lineHeight: '36px' }}>Sumber data</ListSubheader>
							<Box sx={{ px: 2, pb: 2 }}>
								<Typography variant="caption" display="block" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
									{data?.import.measurements_dir}
								</Typography>
								<Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
									Import terakhir: {fmtDateTime(data?.import.last_import_at)}
								</Typography>
								<Tooltip title="Data hanya masuk setelah Re-scan (halaman Import).">
									<IconButton size="small" sx={{ mt: 0.5 }} component={NavLink} to="/import">
										<DownloadingIcon fontSize="small" />
									</IconButton>
								</Tooltip>
							</Box>
						</>
					)}
				</Box>
			</Drawer>

			<Box component="main" sx={{ flexGrow: 1, p: 3, bgcolor: 'background.default' }}>
				<Toolbar />
				<Outlet />
			</Box>
		</Box>
	);
}