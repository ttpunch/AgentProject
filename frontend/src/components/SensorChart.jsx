import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

const SensorChart = ({ data, label, color, valueKey }) => {
    // Auto-detect value column if not specified
    // Exclude common metadata keys and find the first numeric column
    const metadataKeys = ['timestamp', 'datetime', 'id', '_id', 'machine_id'];

    const detectValueKey = () => {
        if (valueKey) return valueKey;
        if (!data || data.length === 0) return 'value';

        const firstRow = data[0];
        const numericKey = Object.keys(firstRow).find(key => {
            if (metadataKeys.includes(key.toLowerCase())) return false;
            return typeof firstRow[key] === 'number';
        });
        return numericKey || 'value';
    };

    const actualValueKey = detectValueKey();

    // Detect timestamp key
    const detectTimestampKey = () => {
        if (!data || data.length === 0) return 'timestamp';
        const firstRow = data[0];
        if (firstRow.timestamp) return 'timestamp';
        if (firstRow.datetime) return 'datetime';
        return Object.keys(firstRow).find(k => k.toLowerCase().includes('time')) || 'timestamp';
    };

    const timestampKey = detectTimestampKey();

    const chartData = {
        labels: data.map(d => {
            const ts = d[timestampKey];
            if (!ts) return '';
            try {
                return new Date(ts).toLocaleTimeString();
            } catch {
                return String(ts);
            }
        }),
        datasets: [
            {
                label: label || actualValueKey,
                data: data.map(d => d[actualValueKey]),
                borderColor: color,
                backgroundColor: color + '20', // Add transparency
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: '#1e293b',
                titleColor: '#f8fafc',
                bodyColor: '#cbd5e1',
                borderColor: '#475569',
                borderWidth: 1,
            },
        },
        scales: {
            x: {
                display: false, // Hide x-axis labels for cleaner look
                grid: {
                    display: false,
                }
            },
            y: {
                grid: {
                    color: '#334155',
                },
                ticks: {
                    color: '#94a3b8',
                    font: {
                        size: 10
                    }
                }
            },
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };

    return <Line data={chartData} options={options} />;
};

export default SensorChart;
