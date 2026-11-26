import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import OverviewPage from './pages/OverviewPage';
import RunsPage from './pages/RunsPage';
import RunDetailPage from './pages/RunDetailPage';
import AnalysisPage from './pages/AnalysisPage';
import ComparePage from './pages/ComparePage';
import TestsPage from './pages/TestsPage';
import ImportPage from './pages/ImportPage';

export default function App() {
	return (
		<Routes>
			<Route element={<Layout />}>
				<Route path="/" element={<OverviewPage />} />
				<Route path="/runs" element={<RunsPage />} />
				<Route path="/runs/:runId" element={<RunDetailPage />} />
				<Route path="/analisis" element={<AnalysisPage />} />
				<Route path="/compare" element={<ComparePage />} />
				<Route path="/tests" element={<TestsPage />} />
				<Route path="/import" element={<ImportPage />} />
				<Route path="*" element={<Navigate to="/" replace />} />
			</Route>
		</Routes>
	);
}