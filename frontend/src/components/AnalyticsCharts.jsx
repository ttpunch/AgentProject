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
import { Line, Scatter } from 'react-chartjs-2';

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

export const AnomalyChart = ({ data }) => {
    // Data preparation
    // We expect data to have 'timestamp', 'vibration', and 'anomaly' (-1 or 1)

    const normalPoints = data.map(d => ({
        x: new Date(d.timestamp).toLocaleTimeString(),
        y: d.vibration,
        isAnomaly: d.anomaly === -1
    }));

    const chartData = {
        labels: data.map(d => new Date(d.timestamp).toLocaleTimeString()),
        datasets: [
            {
                label: 'Vibration Signal',
                data: normalPoints.map(d => d.y),
                borderColor: '#3b82f6', // Blue
                backgroundColor: '#3b82f6',
                pointBackgroundColor: normalPoints.map(d => d.isAnomaly ? '#ef4444' : '#3b82f6'), // Red for anomaly
                pointRadius: normalPoints.map(d => d.isAnomaly ? 6 : 2),
                borderWidth: 1,
                tension: 0.4
            }
        ]
    };

    const options = {
        responsive: true,
        plugins: {
            title: {
                display: true,
                text: 'Anomaly Detection (Red = Anomaly)',
                color: '#e2e8f0'
            },
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                display: false
            },
            y: {
                grid: { color: '#334155' },
                ticks: { color: '#94a3b8' }
            }
        }
    };

    return <Line data={chartData} options={options} />;
};

export const ForecastChart = ({ data }) => {
    // Data has 'timestamp', 'vibration', 'type' ('history' or 'forecast')

    const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());

    // Split data into two datasets for styling
    // Chart.js requires matching indices for labels.
    // We'll create a single dataset but use segment styling for dashed lines

    const values = data.map(d => d.vibration);

    const chartData = {
        labels: labels,
        datasets: [
            {
                label: 'Vibration Forecast',
                data: values,
                borderColor: '#10b981', // Emerald
                segment: {
                    borderDash: ctx => ctx.p0.parsed.x > data.findIndex(d => d.type === 'forecast') ? [6, 6] : undefined,
                    borderColor: ctx => ctx.p0.parsed.x > data.findIndex(d => d.type === 'forecast') ? '#f59e0b' : '#10b981', // Amber for forecast
                },
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 2
            }
        ]
    };

    const options = {
        responsive: true,
        plugins: {
            title: {
                display: true,
                text: 'Forecast (Amber = Prediction)',
                color: '#e2e8f0'
            },
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                display: false
            },
            y: {
                grid: { color: '#334155' },
                ticks: { color: '#94a3b8' }
            }
        }
    };

    return <Line data={chartData} options={options} />;
};
