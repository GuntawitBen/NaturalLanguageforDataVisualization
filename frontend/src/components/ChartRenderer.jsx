import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Pin, PinOff, Table, X, Check, Palette } from 'lucide-react';
import './ChartRenderer.css';

// Professional chart color palette
const CHART_COLORS = {
    primary: '#3B82F6',      // Blue - default chart color
    primaryLight: '#60A5FA',
    secondary: '#d4d4d4',    // Light gray
    tertiary: '#a3a3a3',     // Gray
    quaternary: '#737373',   // Dark gray
    background: '#131a24',
    text: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.7)',
    textMuted: 'rgba(255, 255, 255, 0.5)',
    axis: '#525252',
    grid: 'rgba(255, 255, 255, 0.08)',
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

export default function ChartRenderer({ data, suggestion, onAdd, onRemove, isPinned, onUpdate }) {
    const svgRef = useRef(null);
    const tooltipRef = useRef(null);
    const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, content: '' });
    const [showSettings, setShowSettings] = useState(false);
    // Initialize colors from suggestion or defaults
    const [customColors, setCustomColors] = useState(suggestion.color_mapping || {});
    const MAX_TABLE_ROWS = 10;

    // Save changes when customColors change (debounce if needed, but simple for now)
    const handleColorChange = (category, color) => {
        const newColors = { ...customColors, [category]: color };
        setCustomColors(newColors);
    };

    const saveSettings = () => {
        if (onUpdate) {
            onUpdate({
                ...suggestion,
                color_mapping: customColors
            });
        }
        setShowSettings(false);
    };

    // Extract unique categories for color picking
    const getCategories = () => {
        if (!data || data.length === 0) return [];
        // For tables, use column names as categories
        if (suggestion.chart_type === 'table') {
            return Object.keys(data[0]);
        }
        const groupKey = suggestion.group_by || suggestion.color_by || suggestion.x_axis;
        // For scatter plots, we might want to color by a third dimension if it exists
        if (suggestion.chart_type === 'scatter') return ['Default'];
        if (suggestion.chart_type === 'line' || suggestion.chart_type === 'area') return ['Primary'];

        // For bar/pie/histogram
        return [...new Set(data.map(d => String(d[groupKey])))].sort();
    };

    const categories = getCategories();

    // Tooltip helper functions
    const showTooltip = (event, content) => {
        const svgRect = svgRef.current.getBoundingClientRect();
        const x = event.clientX - svgRect.left;
        const y = event.clientY - svgRect.top;

        setTooltip({
            visible: true,
            x: x + 15,
            y: y - 10,
            content
        });
    };

    const hideTooltip = () => {
        setTooltip({ ...tooltip, visible: false });
    };

    // Handle table type separately
    if (suggestion?.chart_type === 'table') {
        const columns = data && data.length > 0 ? Object.keys(data[0]) : [];
        const displayData = data ? data.slice(0, MAX_TABLE_ROWS) : [];
        const hasMoreRows = data && data.length > MAX_TABLE_ROWS;
        const isSingleRow = data && data.length === 1;

        // Format value for display
        const formatStatValue = (val) => {
            if (val === null || val === undefined) return '—';
            const num = Number(val);
            if (!isNaN(num) && String(val).trim() !== '') {
                if (Number.isInteger(num)) return num.toLocaleString();
                return num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
            }
            return String(val);
        };

        // Format column name for display
        const formatColumnName = (col) => {
            return col
                .replace(/_/g, ' ')
                .replace(/([a-z])([A-Z])/g, '$1 $2')
                .replace(/\b\w/g, c => c.toUpperCase());
        };

        return (
            <div className="chart-container-root table-visualization">
                {isPinned && (
                    <div className="chart-drag-handle" title="Drag to reposition">
                        <div className="drag-grip">
                            <div className="grip-dot"></div>
                            <div className="grip-dot"></div>
                            <div className="grip-dot"></div>
                            <div className="grip-dot"></div>
                            <div className="grip-dot"></div>
                            <div className="grip-dot"></div>
                        </div>
                    </div>
                )}
                {isSingleRow ? (
                    <div className="stat-cards-wrapper">
                        <div className="stat-cards-grid">
                            {columns.map((col, idx) => {
                                const cardColor = customColors[col] || CATEGORY_PALETTE[idx % CATEGORY_PALETTE.length];
                                return (
                                    <div key={idx} className="stat-card" style={{ borderTopColor: cardColor }}>
                                        <span className="stat-card-label">{formatColumnName(col)}</span>
                                        <span className="stat-card-value" style={{ color: cardColor }}>
                                            {formatStatValue(data[0][col])}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ) : (
                    <div className="table-wrapper">
                        {suggestion.title && (
                            <div className="table-header-bar">
                                <span className="table-title">{suggestion.title}</span>
                            </div>
                        )}
                        <div className="table-scroll-container">
                            <table className="viz-table">
                                <thead>
                                    <tr>
                                        {columns.map((col, idx) => (
                                            <th key={idx} style={{ borderBottomColor: customColors[col] || CATEGORY_PALETTE[idx % CATEGORY_PALETTE.length] }}>{col}</th>
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
                )}
                {isPinned && onUpdate && (
                    <button
                        className={`settings-btn ${showSettings ? 'active' : ''}`}
                        onClick={() => setShowSettings(!showSettings)}
                        title="Customize Colors"
                    >
                        <Palette size={16} />
                    </button>
                )}
                <button
                    className={`pin-btn ${isPinned ? 'pinned' : ''}`}
                    onClick={isPinned ? onRemove : onAdd}
                    title={isPinned ? 'Unpin from Dashboard' : 'Pin to Dashboard'}
                >
                    {isPinned ? <PinOff size={16} /> : <Pin size={16} />}
                </button>
                {showSettings && (
                    <div className="chart-settings-panel">
                        <div className="settings-header">
                            <div className="settings-title">
                                <Palette size={14} />
                                <span>Chart Colors</span>
                            </div>
                            <button className="close-settings" onClick={() => setShowSettings(false)}>
                                <X size={14} />
                            </button>
                        </div>
                        <div className="settings-content">
                            {categories.map((category, idx) => (
                                <div key={idx} className="color-setting-item">
                                    <span className="category-label">{category}</span>
                                    <input
                                        type="color"
                                        value={customColors[category] || CATEGORY_PALETTE[idx % CATEGORY_PALETTE.length]}
                                        onChange={(e) => handleColorChange(category, e.target.value)}
                                    />
                                </div>
                            ))}
                        </div>
                        <div className="settings-footer">
                            <button className="save-settings-btn" onClick={saveSettings}>
                                <Check size={14} />
                                Save Changes
                            </button>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    useEffect(() => {
        if (!data || !suggestion || !svgRef.current) return;

        // Clear existing content
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const width = svgRef.current.clientWidth || 600;
        const height = svgRef.current.clientHeight || 400;
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

        // Add zoom behavior (except for pie charts)
        if (suggestion.chart_type !== 'pie') {
            const zoom = d3.zoom()
                .scaleExtent([0.5, 3])
                .on('zoom', (event) => {
                    g.attr('transform', `translate(${margin.left},${margin.top}) ${event.transform}`);
                });

            svg.call(zoom);
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

        if (suggestion.chart_type === 'bar' || suggestion.chart_type === 'histogram') {
            const groupKey = suggestion.group_by || suggestion.color_by;

            if (groupKey && cleanData.some(d => d[groupKey] != null)) {
                // Grouped bar chart
                const groups = [...new Set(cleanData.map(d => String(d[groupKey])))];
                const xCategories = [...new Set(cleanData.map(d => String(d[xKey])))];

                const colorScale = d3.scaleOrdinal()
                    .domain(groups)
                    .range(groups.map((g, i) => customColors[g] || CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]));

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
                xCategories.forEach((category, catIdx) => {
                    const categoryData = cleanData.filter(d => String(d[xKey]) === category);

                    g.selectAll(`.bar-cat-${catIdx}`)
                        .data(categoryData)
                        .enter().append('rect')
                        .attr('class', `bar bar-cat-${catIdx}`)
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

                // Build color scale for bars - each category gets a distinct color
                const xCategories = [...new Set(cleanData.map(d => String(d[xKey])))];
                const barColorScale = d3.scaleOrdinal()
                    .domain(xCategories)
                    .range(xCategories.map((cat, i) => customColors[cat] || CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]));

                const bars = g.selectAll('.bar')
                    .data(cleanData)
                    .enter().append('rect')
                    .attr('class', 'bar')
                    .attr('x', d => x(String(d[xKey])))
                    .attr('y', innerHeight)
                    .attr('width', x.bandwidth())
                    .attr('height', 0)
                    .attr('fill', d => barColorScale(String(d[xKey])))
                    .attr('rx', 6)
                    .style('filter', 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.3))')
                    .style('cursor', 'pointer');

                // Entrance animation with stagger
                bars.transition()
                    .duration(800)
                    .delay((d, i) => i * 50)
                    .ease(d3.easeCubicOut)
                    .attr('y', d => y(+d[yKey]))
                    .attr('height', d => innerHeight - y(+d[yKey]));

                // Interactive hover effects
                bars.on('mouseenter', function (event, d) {
                    // Brighten hovered bar
                    d3.select(this)
                        .transition().duration(200)
                        .style('filter', 'brightness(1.2) drop-shadow(0 6px 12px rgba(255, 255, 255, 0.3))');

                    // Dim other bars
                    bars.filter(function () { return this !== event.currentTarget; })
                        .transition().duration(200)
                        .style('opacity', 0.6);

                    // Show tooltip
                    showTooltip(event, `${String(d[xKey])}: ${(+d[yKey]).toLocaleString()}`);
                })
                    .on('mousemove', (event) => {
                        const svgRect = svgRef.current.getBoundingClientRect();
                        const x = event.clientX - svgRect.left;
                        const y = event.clientY - svgRect.top;
                        setTooltip(prev => ({ ...prev, x: x + 15, y: y - 10 }));
                    })
                    .on('mouseleave', function () {
                        // Reset all bars
                        bars.transition().duration(200)
                            .style('filter', 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.3))')
                            .style('opacity', 1);

                        hideTooltip();
                    });
            }

            addAxisTitles();

        } else if (suggestion.chart_type === 'line' || suggestion.chart_type === 'area') {
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
                .attr('fill', customColors['Primary'] || CHART_COLORS.primary)
                .attr('fill-opacity', 0)
                .attr('d', area)
                .transition()
                .duration(800)
                .attr('fill-opacity', 0.1);

            const line = d3.line()
                .x(d => x(String(d[xKey])))
                .y(d => y(+d[yKey]))
                .curve(d3.curveMonotoneX);

            const path = g.append('path')
                .datum(cleanData)
                .attr('fill', 'none')
                .attr('stroke', customColors['Primary'] || CHART_COLORS.primary)
                .attr('stroke-width', 2.5)
                .attr('d', line);

            // Entrance animation - draw line from left to right
            const totalLength = path.node().getTotalLength();
            path.attr('stroke-dasharray', totalLength + ' ' + totalLength)
                .attr('stroke-dashoffset', totalLength)
                .transition()
                .duration(1200)
                .ease(d3.easeCubicOut)
                .attr('stroke-dashoffset', 0);

            // Crosshair group
            const crosshair = g.append('g')
                .style('display', 'none');

            crosshair.append('line')
                .attr('class', 'chart-crosshair')
                .attr('y1', 0)
                .attr('y2', innerHeight);

            const points = g.selectAll('.dot')
                .data(cleanData)
                .enter().append('circle')
                .attr('class', 'dot')
                .attr('cx', d => x(String(d[xKey])))
                .attr('cy', d => y(+d[yKey]))
                .attr('r', 0)
                .attr('fill', customColors['Primary'] || CHART_COLORS.primary)
                .attr('stroke', CHART_COLORS.background)
                .attr('stroke-width', 2)
                .style('cursor', 'pointer');

            // Points fade in after line draws
            points.transition()
                .delay(1000)
                .duration(400)
                .attr('r', 5);

            // Interactive points
            points.on('mouseenter', function (event, d) {
                d3.select(this)
                    .transition().duration(200)
                    .attr('r', 7)
                    .style('filter', 'drop-shadow(0 0 8px rgba(255, 255, 255, 0.8))');

                // Show crosshair
                crosshair.style('display', null)
                    .select('line')
                    .attr('x1', x(String(d[xKey])))
                    .attr('x2', x(String(d[xKey])));

                showTooltip(event, `${String(d[xKey])}: ${(+d[yKey]).toLocaleString()}`);
            })
                .on('mousemove', (event) => {
                    const svgRect = svgRef.current.getBoundingClientRect();
                    const xPos = event.clientX - svgRect.left;
                    const yPos = event.clientY - svgRect.top;
                    setTooltip(prev => ({ ...prev, x: xPos + 15, y: yPos - 10 }));
                })
                .on('mouseleave', function () {
                    d3.select(this)
                        .transition().duration(200)
                        .attr('r', 5)
                        .style('filter', 'none');

                    crosshair.style('display', 'none');
                    hideTooltip();
                });

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

            const dots = g.selectAll('.dot')
                .data(cleanData)
                .enter().append('circle')
                .attr('class', 'dot')
                .attr('cx', d => x(+d[xKey]))
                .attr('cy', d => y(+d[yKey]))
                .attr('r', 0)
                .attr('fill', customColors['Default'] || CHART_COLORS.primary)
                .attr('fill-opacity', 0.7)
                .attr('stroke', customColors['Default'] || CHART_COLORS.primaryLight)
                .attr('stroke-width', 1.5)
                .style('cursor', 'pointer');

            // Entrance animation - fade in and grow
            dots.transition()
                .duration(600)
                .delay((d, i) => i * 30)
                .ease(d3.easeCubicOut)
                .attr('r', 7);

            // Interactive dots
            dots.on('mouseenter', function (event, d) {
                d3.select(this)
                    .transition().duration(200)
                    .attr('r', 9)
                    .style('filter', 'drop-shadow(0 0 12px rgba(255, 255, 255, 0.8))');

                // Dim other dots
                dots.filter(function () { return this !== event.currentTarget; })
                    .transition().duration(200)
                    .style('opacity', 0.4);

                showTooltip(event, `X: ${(+d[xKey]).toLocaleString()}, Y: ${(+d[yKey]).toLocaleString()}`);
            })
                .on('mousemove', (event) => {
                    const svgRect = svgRef.current.getBoundingClientRect();
                    const xPos = event.clientX - svgRect.left;
                    const yPos = event.clientY - svgRect.top;
                    setTooltip(prev => ({ ...prev, x: xPos + 15, y: yPos - 10 }));
                })
                .on('mouseleave', function () {
                    dots.transition().duration(200)
                        .attr('r', 7)
                        .style('filter', 'none')
                        .style('opacity', 1);

                    hideTooltip();
                });

            addAxisTitles();

        } else if (suggestion.chart_type === 'pie') {
            const radius = Math.min(innerWidth, innerHeight) / 2;
            const pieG = g.append('g')
                .attr('transform', `translate(${innerWidth / 2},${innerHeight / 2})`);

            const color = d3.scaleOrdinal()
                .domain(cleanData.map(d => String(d[xKey]))) // Ensure domain matches categories
                .range(cleanData.map((d, i) => customColors[String(d[xKey])] || CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]));
            const pie = d3.pie().value(d => +d[yKey]).sort(null).padAngle(0.01);
            const arc = d3.arc().innerRadius(0).outerRadius(radius - 10).cornerRadius(2);
            const hoverArc = d3.arc().innerRadius(0).outerRadius(radius - 5).cornerRadius(2);
            const labelArc = d3.arc().innerRadius(radius * 0.6).outerRadius(radius * 0.6);

            const arcs = pieG.selectAll('arc')
                .data(pie(cleanData))
                .enter()
                .append('g')
                .attr('class', 'arc');

            const paths = arcs.append('path')
                .attr('fill', (d, i) => color(i))
                .attr('stroke', CHART_COLORS.background)
                .style('stroke-width', '2px')
                .style('filter', 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))')
                .style('cursor', 'pointer');

            // Entrance animation - arc tween
            paths.transition()
                .duration(800)
                .ease(d3.easeCubicOut)
                .attrTween('d', function (d) {
                    const interpolate = d3.interpolate(
                        { startAngle: d.startAngle, endAngle: d.startAngle, padAngle: d.padAngle },
                        d
                    );
                    return function (t) {
                        return arc(interpolate(t));
                    };
                });

            // Interactive slices
            const arcGroups = pieG.selectAll('.arc');
            arcGroups.on('mouseenter', function (event, d) {
                const currentArc = d3.select(this).select('path');

                // Pull out and scale slice
                d3.select(this)
                    .transition().duration(200)
                    .attr('transform', function (d) {
                        const [x, y] = arc.centroid(d);
                        return `translate(${x * 0.1},${y * 0.1}) scale(1.05)`;
                    });

                currentArc.transition().duration(200)
                    .attr('d', hoverArc)
                    .style('filter', 'drop-shadow(0 6px 16px rgba(0, 0, 0, 0.5))');

                const percent = ((d.endAngle - d.startAngle) / (2 * Math.PI) * 100).toFixed(1);
                const value = d.data[yKey];
                showTooltip(event, `${String(d.data[xKey])}: ${(+value).toLocaleString()} (${percent}%)`);
            })
                .on('mousemove', (event) => {
                    const svgRect = svgRef.current.getBoundingClientRect();
                    const xPos = event.clientX - svgRect.left;
                    const yPos = event.clientY - svgRect.top;
                    setTooltip(prev => ({ ...prev, x: xPos + 15, y: yPos - 10 }));
                })
                .on('mouseleave', function () {
                    d3.select(this)
                        .transition().duration(200)
                        .attr('transform', 'translate(0,0) scale(1)');

                    d3.select(this).select('path')
                        .transition().duration(200)
                        .attr('d', arc)
                        .style('filter', 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))');

                    hideTooltip();
                });

            // Add labels for larger slices
            arcs.append('text')
                .attr('transform', d => `translate(${labelArc.centroid(d)})`)
                .attr('text-anchor', 'middle')
                .style('font-size', '11px')
                .style('fill', CHART_COLORS.text)
                .style('font-weight', '500')
                .style('opacity', 0)
                .text(d => {
                    const percent = (d.endAngle - d.startAngle) / (2 * Math.PI) * 100;
                    return percent > 5 ? `${percent.toFixed(0)}%` : '';
                })
                .transition()
                .delay(800)
                .duration(400)
                .style('opacity', 1);
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
            {isPinned && (
                <div className="chart-drag-handle" title="Drag to reposition">
                    <div className="drag-grip">
                        <div className="grip-dot"></div>
                        <div className="grip-dot"></div>
                        <div className="grip-dot"></div>
                        <div className="grip-dot"></div>
                        <div className="grip-dot"></div>
                        <div className="grip-dot"></div>
                    </div>
                </div>
            )}
            <div className="svg-wrapper">
                <svg
                    ref={svgRef}
                    width="100%"
                    height="100%"
                    className="d3-svg"
                    style={{ minHeight: '300px', maxHeight: '500px' }}
                />
                {/* Tooltip overlay */}
                {tooltip.visible && (
                    <div
                        ref={tooltipRef}
                        className="chart-tooltip visible"
                        style={{
                            left: `${tooltip.x}px`,
                            top: `${tooltip.y}px`,
                        }}
                    >
                        <div className="chart-tooltip-value">{tooltip.content}</div>
                    </div>
                )}
            </div>
            {isPinned && onUpdate && (
                <button
                    className={`settings-btn ${showSettings ? 'active' : ''}`}
                    onClick={() => setShowSettings(!showSettings)}
                    title="Customize Colors"
                >
                    <Palette size={16} />
                </button>
            )}
            <button
                className={`pin-btn ${isPinned ? 'pinned' : ''}`}
                onClick={isPinned ? onRemove : onAdd}
                title={isPinned ? 'Unpin from Dashboard' : 'Pin to Dashboard'}
            >
                {isPinned ? <PinOff size={16} /> : <Pin size={16} />}
            </button>

            {/* Settings Components */}
            {showSettings && (
                <div className="chart-settings-panel">
                    <div className="settings-header">
                        <div className="settings-title">
                            <Palette size={14} />
                            <span>Chart Colors</span>
                        </div>
                        <button className="close-settings" onClick={() => setShowSettings(false)}>
                            <X size={14} />
                        </button>
                    </div>
                    <div className="settings-content">
                        {categories.map((category, idx) => (
                            <div key={idx} className="color-setting-item">
                                <span className="category-label">{category}</span>
                                <input
                                    type="color"
                                    value={customColors[category] || (category === 'Primary' || category === 'Default' ? CHART_COLORS.primary : CATEGORY_PALETTE[idx % CATEGORY_PALETTE.length])}
                                    onChange={(e) => handleColorChange(category, e.target.value)}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="settings-footer">
                        <button className="save-settings-btn" onClick={saveSettings}>
                            <Check size={14} />
                            Save Changes
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
