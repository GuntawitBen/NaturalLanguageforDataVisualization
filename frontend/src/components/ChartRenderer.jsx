import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Pin, PinOff, Table } from 'lucide-react';
import './ChartRenderer.css';

// Professional chart color palette
const CHART_COLORS = {
    primary: '#ffffff',      // White - clean chart color
    primaryLight: '#e5e5e5',
    secondary: '#d4d4d4',    // Light gray
    tertiary: '#a3a3a3',     // Gray
    quaternary: '#737373',   // Dark gray
    background: '#0c0c0c',
    text: '#fafafa',
    textSecondary: 'rgba(250, 250, 250, 0.7)',
    textMuted: 'rgba(250, 250, 250, 0.5)',
    axis: '#525252',
    grid: 'rgba(250, 250, 250, 0.08)',
};

// Multi-color palette for grouped/categorical charts
const CATEGORY_PALETTE = [
    '#3B82F6', // blue
    '#F59E0B', // amber
    '#10B981', // green
    '#EF4444', // red
    '#8B5CF6', // purple
    '#06B6D4', // cyan
    '#EC4899', // pink
    '#84CC16', // lime
    '#F97316', // orange
    '#6366F1', // indigo
];

export default function ChartRenderer({ data, suggestion, onAdd, onRemove, isPinned }) {
    const svgRef = useRef(null);
    const MAX_TABLE_ROWS = 10;

    // Handle table type separately
    if (suggestion?.chart_type === 'table') {
        const columns = data && data.length > 0 ? Object.keys(data[0]) : [];
        const displayData = data ? data.slice(0, MAX_TABLE_ROWS) : [];
        const hasMoreRows = data && data.length > MAX_TABLE_ROWS;

        return (
            <div className="chart-container-root table-visualization">
                <div className="table-wrapper">
                    <div className="table-header-bar">
                        <Table size={16} />
                        <span className="table-title">{suggestion.title || 'Data Table'}</span>
                        <span className="table-row-count">{data?.length || 0} rows</span>
                    </div>
                    <div className="table-scroll-container">
                        <table className="viz-table">
                            <thead>
                                <tr>
                                    {columns.map((col, idx) => (
                                        <th key={idx}>{col}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {displayData.map((row, rowIdx) => (
                                    <tr key={rowIdx}>
                                        {columns.map((col, colIdx) => (
                                            <td key={colIdx}>
                                                {row[col] !== null && row[col] !== undefined
                                                    ? String(row[col])
                                                    : '—'}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {hasMoreRows && (
                        <div className="table-more-rows">
                            +{data.length - MAX_TABLE_ROWS} more rows
                        </div>
                    )}
                </div>
                <button
                    className={`pin-btn ${isPinned ? 'pinned' : ''}`}
                    onClick={isPinned ? onRemove : onAdd}
                    title={isPinned ? 'Unpin from Dashboard' : 'Pin to Dashboard'}
                >
                    {isPinned ? <PinOff size={16} /> : <Pin size={16} />}
                </button>
            </div>
        );
    }

    useEffect(() => {
        if (!data || !suggestion || !svgRef.current) return;

        // Clear existing content
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const width = svgRef.current.clientWidth || 600;
        const height = 420;
        const margin = { top: 50, right: 40, bottom: 80, left: 80 };
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const xKey = suggestion.x_axis;
        const yKey = suggestion.y_axis;

        // Filter out null/undefined values for safety
        const cleanData = data.filter(d => d[xKey] != null && d[yKey] != null);

        if (cleanData.length === 0) {
            g.append('text')
                .attr('x', innerWidth / 2)
                .attr('y', innerHeight / 2)
                .attr('text-anchor', 'middle')
                .style('fill', CHART_COLORS.textSecondary)
                .style('font-size', '14px')
                .text('No data available for these axes');
            return;
        }

        // Helper function to add axis titles
        const addAxisTitles = () => {
            // X-axis title
            g.append('text')
                .attr('x', innerWidth / 2)
                .attr('y', innerHeight + 60)
                .attr('text-anchor', 'middle')
                .style('font-size', '13px')
                .style('font-weight', '500')
                .style('fill', CHART_COLORS.textSecondary)
                .style('font-family', "'Plus Jakarta Sans', sans-serif")
                .text(xKey);

            // Y-axis title
            g.append('text')
                .attr('transform', 'rotate(-90)')
                .attr('x', -innerHeight / 2)
                .attr('y', -55)
                .attr('text-anchor', 'middle')
                .style('font-size', '13px')
                .style('font-weight', '500')
                .style('fill', CHART_COLORS.textSecondary)
                .style('font-family', "'Plus Jakarta Sans', sans-serif")
                .text(yKey);
        };

        // Style axes function
        const styleAxes = (xAxisG, yAxisG) => {
            // Style x-axis
            xAxisG.selectAll('text')
                .style('font-size', '12px')
                .style('fill', CHART_COLORS.textSecondary)
                .style('font-family', "'Plus Jakarta Sans', sans-serif");

            xAxisG.select('.domain')
                .style('stroke', CHART_COLORS.axis);

            xAxisG.selectAll('.tick line')
                .style('stroke', CHART_COLORS.axis);

            // Style y-axis
            yAxisG.selectAll('text')
                .style('font-size', '12px')
                .style('fill', CHART_COLORS.textSecondary)
                .style('font-family', "'Plus Jakarta Sans', sans-serif");

            yAxisG.select('.domain')
                .style('stroke', CHART_COLORS.axis);

            yAxisG.selectAll('.tick line')
                .style('stroke', CHART_COLORS.axis);
        };

        // Add grid lines function
        const addGridLines = (yScale) => {
            g.append('g')
                .attr('class', 'grid')
                .selectAll('line')
                .data(yScale.ticks(5))
                .enter()
                .append('line')
                .attr('x1', 0)
                .attr('x2', innerWidth)
                .attr('y1', d => yScale(d))
                .attr('y2', d => yScale(d))
                .style('stroke', CHART_COLORS.grid)
                .style('stroke-dasharray', '3,3');
        };

        if (suggestion.chart_type === 'bar') {
            const groupKey = suggestion.group_by || suggestion.color_by;

            if (groupKey && cleanData.some(d => d[groupKey] != null)) {
                // Grouped bar chart
                const groups = [...new Set(cleanData.map(d => String(d[groupKey])))];
                const xCategories = [...new Set(cleanData.map(d => String(d[xKey])))];

                const colorScale = d3.scaleOrdinal()
                    .domain(groups)
                    .range(CATEGORY_PALETTE);

                const x0 = d3.scaleBand()
                    .domain(xCategories)
                    .range([0, innerWidth])
                    .padding(0.2);

                const x1 = d3.scaleBand()
                    .domain(groups)
                    .range([0, x0.bandwidth()])
                    .padding(0.05);

                const y = d3.scaleLinear()
                    .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                    .range([innerHeight, 0]);

                // Add grid lines
                addGridLines(y);

                const xAxisG = g.append('g')
                    .attr('transform', `translate(0,${innerHeight})`)
                    .call(d3.axisBottom(x0));

                xAxisG.selectAll('text')
                    .attr('transform', 'rotate(-45)')
                    .style('text-anchor', 'end');

                const yAxisG = g.append('g')
                    .call(d3.axisLeft(y).ticks(6));

                styleAxes(xAxisG, yAxisG);

                // Create grouped bars
                xCategories.forEach(category => {
                    const categoryData = cleanData.filter(d => String(d[xKey]) === category);

                    g.selectAll(`.bar-${category.replace(/\s+/g, '-')}`)
                        .data(categoryData)
                        .enter().append('rect')
                        .attr('class', 'bar')
                        .attr('x', d => x0(String(d[xKey])) + x1(String(d[groupKey])))
                        .attr('y', d => y(+d[yKey]))
                        .attr('width', x1.bandwidth())
                        .attr('height', d => innerHeight - y(+d[yKey]))
                        .attr('fill', d => colorScale(String(d[groupKey])))
                        .attr('rx', 2);
                });

                // Add legend
                const legend = svg.append('g')
                    .attr('transform', `translate(${width - margin.right - 100}, ${margin.top})`);

                groups.forEach((group, i) => {
                    const legendRow = legend.append('g')
                        .attr('transform', `translate(0, ${i * 22})`);

                    legendRow.append('rect')
                        .attr('width', 14)
                        .attr('height', 14)
                        .attr('rx', 2)
                        .attr('fill', colorScale(group));

                    legendRow.append('text')
                        .attr('x', 20)
                        .attr('y', 11)
                        .style('font-size', '11px')
                        .style('fill', CHART_COLORS.textSecondary)
                        .style('font-family', "'Plus Jakarta Sans', sans-serif")
                        .text(group);
                });

            } else {
                // Simple bar chart (no grouping)
                const x = d3.scaleBand()
                    .domain(cleanData.map(d => String(d[xKey])))
                    .range([0, innerWidth])
                    .padding(0.25);

                const y = d3.scaleLinear()
                    .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                    .range([innerHeight, 0]);

                // Add grid lines
                addGridLines(y);

                const xAxisG = g.append('g')
                    .attr('transform', `translate(0,${innerHeight})`)
                    .call(d3.axisBottom(x));

                xAxisG.selectAll('text')
                    .attr('transform', 'rotate(-45)')
                    .style('text-anchor', 'end');

                const yAxisG = g.append('g')
                    .call(d3.axisLeft(y).ticks(6));

                styleAxes(xAxisG, yAxisG);

                g.selectAll('.bar')
                    .data(cleanData)
                    .enter().append('rect')
                    .attr('class', 'bar')
                    .attr('x', d => x(String(d[xKey])))
                    .attr('y', d => y(+d[yKey]))
                    .attr('width', x.bandwidth())
                    .attr('height', d => innerHeight - y(+d[yKey]))
                    .attr('fill', CHART_COLORS.primary)
                    .attr('rx', 4);
            }

            addAxisTitles();

        } else if (suggestion.chart_type === 'line') {
            const x = d3.scalePoint()
                .domain(cleanData.map(d => String(d[xKey])))
                .range([0, innerWidth]);

            const y = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                .range([innerHeight, 0]);

            // Add grid lines
            addGridLines(y);

            const xAxisG = g.append('g')
                .attr('transform', `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x));

            xAxisG.selectAll('text')
                .attr('transform', 'rotate(-45)')
                .style('text-anchor', 'end');

            const yAxisG = g.append('g')
                .call(d3.axisLeft(y).ticks(6));

            styleAxes(xAxisG, yAxisG);

            // Area fill under line
            const area = d3.area()
                .x(d => x(String(d[xKey])))
                .y0(innerHeight)
                .y1(d => y(+d[yKey]))
                .curve(d3.curveMonotoneX);

            g.append('path')
                .datum(cleanData)
                .attr('fill', CHART_COLORS.primary)
                .attr('fill-opacity', 0.1)
                .attr('d', area);

            const line = d3.line()
                .x(d => x(String(d[xKey])))
                .y(d => y(+d[yKey]))
                .curve(d3.curveMonotoneX);

            g.append('path')
                .datum(cleanData)
                .attr('fill', 'none')
                .attr('stroke', CHART_COLORS.primary)
                .attr('stroke-width', 2.5)
                .attr('d', line);

            g.selectAll('.dot')
                .data(cleanData)
                .enter().append('circle')
                .attr('cx', d => x(String(d[xKey])))
                .attr('cy', d => y(+d[yKey]))
                .attr('r', 5)
                .attr('fill', CHART_COLORS.primary)
                .attr('stroke', CHART_COLORS.background)
                .attr('stroke-width', 2);

            addAxisTitles();

        } else if (suggestion.chart_type === 'scatter') {
            const x = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[xKey]) * 1.1])
                .range([0, innerWidth]);

            const y = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                .range([innerHeight, 0]);

            // Add grid lines
            addGridLines(y);

            const xAxisG = g.append('g')
                .attr('transform', `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x).ticks(6));

            const yAxisG = g.append('g')
                .call(d3.axisLeft(y).ticks(6));

            styleAxes(xAxisG, yAxisG);

            g.selectAll('.dot')
                .data(cleanData)
                .enter().append('circle')
                .attr('cx', d => x(+d[xKey]))
                .attr('cy', d => y(+d[yKey]))
                .attr('r', 7)
                .attr('fill', CHART_COLORS.primary)
                .attr('fill-opacity', 0.7)
                .attr('stroke', CHART_COLORS.primaryLight)
                .attr('stroke-width', 1.5);

            addAxisTitles();

        } else if (suggestion.chart_type === 'pie') {
            const radius = Math.min(innerWidth, innerHeight) / 2;
            const pieG = g.append('g')
                .attr('transform', `translate(${innerWidth / 2},${innerHeight / 2})`);

            const color = d3.scaleOrdinal(CATEGORY_PALETTE);
            const pie = d3.pie().value(d => +d[yKey]).sort(null);
            const arc = d3.arc().innerRadius(0).outerRadius(radius - 10);
            const labelArc = d3.arc().innerRadius(radius * 0.6).outerRadius(radius * 0.6);

            const arcs = pieG.selectAll('arc')
                .data(pie(cleanData))
                .enter()
                .append('g');

            arcs.append('path')
                .attr('d', arc)
                .attr('fill', (d, i) => color(i))
                .attr('stroke', CHART_COLORS.background)
                .style('stroke-width', '2px');

            // Add labels for larger slices
            arcs.append('text')
                .attr('transform', d => `translate(${labelArc.centroid(d)})`)
                .attr('text-anchor', 'middle')
                .style('font-size', '11px')
                .style('fill', CHART_COLORS.text)
                .style('font-weight', '500')
                .text(d => {
                    const percent = (d.endAngle - d.startAngle) / (2 * Math.PI) * 100;
                    return percent > 5 ? `${percent.toFixed(0)}%` : '';
                });
        }

        // Add Chart Title
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', 28)
            .attr('text-anchor', 'middle')
            .style('font-size', '15px')
            .style('font-weight', '600')
            .style('fill', CHART_COLORS.text)
            .style('font-family', "'JetBrains Mono', monospace")
            .text(suggestion.title);

    }, [data, suggestion]);

    return (
        <div className="chart-container-root">
            <div className="svg-wrapper">
                <svg
                    ref={svgRef}
                    width="100%"
                    height={420}
                    className="d3-svg"
                />
            </div>
            <button
                className={`pin-btn ${isPinned ? 'pinned' : ''}`}
                onClick={isPinned ? onRemove : onAdd}
                title={isPinned ? 'Unpin from Dashboard' : 'Pin to Dashboard'}
            >
                {isPinned ? <PinOff size={16} /> : <Pin size={16} />}
            </button>
        </div>
    );
}
