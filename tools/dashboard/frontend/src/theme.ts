import { createTheme } from '@mui/material/styles';

const theme = createTheme({
	palette: {
		mode: 'light',
		primary: { main: '#3949ab' },
		secondary: { main: '#00838f' },
		success: { main: '#2e7d32' },
		warning: { main: '#ed6c02' },
		error: { main: '#c62828' },
		background: { default: '#f5f6fa', paper: '#ffffff' },
	},
	typography: {
		fontFamily: '"Segoe UI", "Inter", Roboto, "Helvetica Neue", Arial, sans-serif',
		h5: { fontWeight: 600 },
		h6: { fontWeight: 600 },
	},
	components: {
		MuiCard: { defaultProps: { elevation: 1 } },
	},
});

export default theme;