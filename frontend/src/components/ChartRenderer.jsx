import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Plus, Trash2, Check, ExternalLink } from 'lucide-react';
import './ChartRenderer.css';

export default function ChartRenderer({ data, suggestion, onAdd, onRemove, isPinned }) {
    const svgRef = useRef(null);

    useEffect(() => {
        if (!data || !suggestion || !svgRef.current) return;

        // Clear existing content
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const width = svgRef.current.clientWidth || 600;
        const height = suggestion.priority === 'high' ? 500 : (suggestion.priority === 'medium' ? 400 : 300);
        const margin = { top: 40, right: 30, bottom: 60, left: 60 };
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
                .text('No data available for these axes');
            return;
        }

        if (suggestion.chart_type === 'bar') {
            const x = d3.scaleBand()
                .domain(cleanData.map(d => String(d[xKey])))
                .range([0, innerWidth])
                .padding(0.2);

            const y = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                .range([innerHeight, 0]);

            g.append('g')
                .attr('transform', `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x))
                .selectAll('text')
                .attr('transform', 'rotate(-45)')
                .style('text-anchor', 'end');

            g.append('g')
                .call(d3.axisLeft(y));

            g.selectAll('.bar')
                .data(cleanData)
                .enter().append('rect')
                .attr('class', 'bar')
                .attr('x', d => x(String(d[xKey])))
                .attr('y', d => y(+d[yKey]))
                .attr('width', x.bandwidth())
                .attr('height', d => innerHeight - y(+d[yKey]))
                .attr('fill', '#3182ce')
                .attr('rx', 4);

        } else if (suggestion.chart_type === 'line') {
            const x = d3.scalePoint()
                .domain(cleanData.map(d => String(d[xKey])))
                .range([0, innerWidth]);

            const y = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                .range([innerHeight, 0]);

            g.append('g')
                .attr('transform', `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x))
                .selectAll('text')
                .attr('transform', 'rotate(-45)')
                .style('text-anchor', 'end');

            g.append('g')
                .call(d3.axisLeft(y));

            const line = d3.line()
                .x(d => x(String(d[xKey])))
                .y(d => y(+d[yKey]))
                .curve(d3.curveMonotoneX);

            g.append('path')
                .datum(cleanData)
                .attr('fill', 'none')
                .attr('stroke', '#3182ce')
                .attr('stroke-width', 3)
                .attr('d', line);

            g.selectAll('.dot')
                .data(cleanData)
                .enter().append('circle')
                .attr('cx', d => x(String(d[xKey])))
                .attr('cy', d => y(+d[yKey]))
                .attr('r', 5)
                .attr('fill', '#3182ce')
                .attr('stroke', '#fff')
                .attr('stroke-width', 2);

        } else if (suggestion.chart_type === 'scatter') {
            const x = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[xKey]) * 1.1])
                .range([0, innerWidth]);

            const y = d3.scaleLinear()
                .domain([0, d3.max(cleanData, d => +d[yKey]) * 1.1])
                .range([innerHeight, 0]);

            g.append('g')
                .attr('transform', `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x));

            g.append('g')
                .call(d3.axisLeft(y));

            g.selectAll('.dot')
                .data(cleanData)
                .enter().append('circle')
                .attr('cx', d => x(+d[xKey]))
                .attr('cy', d => y(+d[yKey]))
                .attr('r', 6)
                .attr('fill', '#3182ce')
                .style('opacity', 0.7);

        } else if (suggestion.chart_type === 'pie') {
            const radius = Math.min(innerWidth, innerHeight) / 2;
            const pieG = g.append('g')
                .attr('transform', `translate(${innerWidth / 2},${innerHeight / 2})`);

            const color = d3.scaleOrdinal(d3.schemeCategory10);
            const pie = d3.pie().value(d => +d[yKey]);
            const arc = d3.arc().innerRadius(0).outerRadius(radius);

            const arcs = pieG.selectAll('arc')
                .data(pie(cleanData))
                .enter()
                .append('g');

            arcs.append('path')
                .attr('d', arc)
                .attr('fill', (d, i) => color(i))
                .attr('stroke', '#fff')
                .style('stroke-width', '2px');
        }

        // Add Titles/Labels
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', 25)
            .attr('text-anchor', 'middle')
            .style('font-size', '16px')
            .style('font-weight', 'bold')
            .text(suggestion.title);

    }, [data, suggestion]);

    const height = suggestion.priority === 'high' ? 500 : (suggestion.priority === 'medium' ? 400 : 300);

    return (
        <div className={`chart-container-root ${suggestion.priority}`}>
            <div className="chart-info">
                <div className="chart-header-row">
                    <h3>{suggestion.title}</h3>
                    <span className={`priority-badge ${suggestion.priority}`}>
                        {suggestion.priority.toUpperCase()}
                    </span>
                </div>
                <p className="chart-explanation">{suggestion.explanation}</p>
            </div>
            <div className="svg-wrapper">
                <svg
                    ref={svgRef}
                    width="100%"
                    height={height}
                    className="d3-svg"
                />
            </div>
            <div className="chart-footer">
                <span className="reasoning-bubble">{suggestion.reasoning}</span>
                <div className="chart-actions">
                    {isPinned ? (
                        <button className="action-btn pinned" onClick={onRemove} title="Remove from Dashboard">
                            <Check size={14} />
                            <span>Pinned</span>
                            <span className="remove-label"><Trash2 size={12} /> Remove</span>
                        </button>
                    ) : (
                        <button className="action-btn add" onClick={onAdd} title="Add to Dashboard">
                            <Plus size={14} />
                            <span>Add to Dashboard</span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
