import React, { useEffect, useState } from 'react';
import axios from 'axios';
import SensorChart from './SensorChart';

const MachineCard = ({ machine }) => {
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState('running'); // Default to running

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                // Use environment variable for API URL
                const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const response = await axios.get(`${apiUrl}/machines/${machine.machine_id}/metrics?limit=50`);
                setMetrics(response.data);

                // Determine status based on latest metric
                if (response.data.length > 0) {
                    const latest = response.data[response.data.length - 1];
                    // Simple logic: if vibration > 0.8, warning. If > 1.0, error.
                    if (latest.vibration > 1.0) setStatus('error');
                    else if (latest.vibration > 0.8) setStatus('warning');
                    else setStatus('running');
                }
            } catch (error) {
                console.error(`Error fetching metrics for ${machine.machine_id}:`, error);
            } finally {
                setLoading(false);
            }
        };

        fetchMetrics();
        // Poll every 5 seconds
        const interval = setInterval(fetchMetrics, 5000);
        return () => clearInterval(interval);
    }, [machine.machine_id]);

    const getStatusClass = (s) => {
        switch (s) {
            case 'running': return 'status-running';
            case 'warning': return 'status-warning';
            case 'error': return 'status-error';
            default: return '';
        }
    };

    return (
        <div className="card">
            <div className="card-header">
                <h3 className="card-title">{machine.machine_id}</h3>
                <span className={`status-badge ${getStatusClass(status)}`}>
                    {status.toUpperCase()}
                </span>
            </div>

            <div className="metric-row">
                <span>Model</span>
                <span className="metric-value">{machine.model}</span>
            </div>
            <div className="metric-row">
                <span>Location</span>
                <span className="metric-value">{machine.location}</span>
            </div>

            {loading ? (
                <div className="loading">Loading metrics...</div>
            ) : (
                <>
                    <div className="chart-container">
                        <div className="metric-row">
                            <span>Vibration</span>
                            <span className="metric-value">
                                {metrics.length > 0 ? metrics[metrics.length - 1].vibration.toFixed(3) : '-'}
                            </span>
                        </div>
                        <SensorChart
                            data={metrics.map(m => ({ timestamp: m.timestamp, value: m.vibration }))}
                            label="Vibration"
                            color="#38bdf8"
                        />
                    </div>

                    <div className="chart-container" style={{ marginTop: '1.5rem' }}>
                        <div className="metric-row">
                            <span>Temperature</span>
                            <span className="metric-value">
                                {metrics.length > 0 ? metrics[metrics.length - 1].temperature.toFixed(1) : '-'} °C
                            </span>
                        </div>
                        <SensorChart
                            data={metrics.map(m => ({ timestamp: m.timestamp, value: m.temperature }))}
                            label="Temp"
                            color="#facc15"
                        />
                    </div>
                </>
            )}
        </div>
    );
};

export default MachineCard;
