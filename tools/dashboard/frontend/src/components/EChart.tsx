import { useEffect, useRef } from 'react';
import Box from '@mui/material/Box';
import * as echarts from 'echarts/core';
import { LineChart, BarChart } from 'echarts/charts';
import {
	GridComponent,
	TooltipComponent,
	LegendComponent,
	TitleComponent,
	DataZoomComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, DataZoomComponent, CanvasRenderer]);

export interface EChartProps {
	option: echarts.EChartsCoreOption;
	height?: number | string;
	loading?: boolean;
}

/** Wrapper ECharts (tree-shaken) dengan resize otomatis. */
export default function EChart({ option, height = 360, loading = false }: EChartProps) {
	const ref = useRef<HTMLDivElement>(null);
	const chartRef = useRef<echarts.ECharts | null>(null);

	useEffect(() => {
		if (!ref.current) return;
		chartRef.current = echarts.init(ref.current);
		const onResize = () => chartRef.current?.resize();
		window.addEventListener('resize', onResize);
		return () => {
			window.removeEventListener('resize', onResize);
			chartRef.current?.dispose();
			chartRef.current = null;
		};
	}, []);

	useEffect(() => {
		chartRef.current?.setOption(option, { notMerge: true });
	}, [option]);

	useEffect(() => {
		if (loading) chartRef.current?.showLoading();
		else chartRef.current?.hideLoading();
	}, [loading]);

	return <Box ref={ref} sx={{ width: '100%', height }} />;
}