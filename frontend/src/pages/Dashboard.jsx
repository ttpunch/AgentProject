import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import MachineCard from '../components/MachineCard';
import AIReportModal from '../components/AIReportModal';

function Dashboard() {
    const [machines, setMachines] = useState([]);
    const [anomalies, setAnomalies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isAIModalOpen, setIsAIModalOpen] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchData = async () => {
            try {
                const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

                const [machinesRes, anomaliesRes] = await Promise.all([
                    axios.get(`${apiUrl}/machines`),
                    axios.get(`${apiUrl}/anomalies`)
                ]);

                setMachines(machinesRes.data);
                setAnomalies(anomaliesRes.data);
            } catch (error) {
                console.error("Error fetching dashboard data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return (
        <div className="dashboard-container">
            <header className="header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h1>CNC Predictive Maintenance</h1>
                    <button
                        onClick={() => setIsAIModalOpen(true)}
                        style={{
                            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                            border: 'none',
                            padding: '0.5rem 1rem',
                            borderRadius: '6px',
                            color: 'white',
                            cursor: 'pointer',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            boxShadow: '0 4px 6px -1px rgba(99, 102, 241, 0.4)'
                        }}
                    >
                        <span>✨</span> AI Insights
                    </button>
                    <button
                        onClick={() => navigate('/chat')}
                        style={{
                            background: 'rgba(255, 255, 255, 0.1)',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            padding: '0.5rem 1rem',
                            borderRadius: '6px',
                            color: 'white',
                            cursor: 'pointer',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                        }}
                    >
                        <span>💬</span> Chat Agent
                    </button>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <div className="card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Total Machines:</span>
                        <span style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>{machines.length}</span>
                    </div>
                    <div className="card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Active Anomalies:</span>
                        <span style={{ fontWeight: 'bold', color: anomalies.length > 0 ? 'var(--danger-color)' : 'var(--success-color)' }}>
                            {anomalies.length}
                        </span>
                    </div>
                </div>
            </header>

            {anomalies.length > 0 && (
                <section>
                    <h2 className="section-title" style={{ color: 'var(--danger-color)' }}>⚠️ Recent Anomalies</h2>
                    <div className="grid-container">
                        {anomalies.map((anomaly, idx) => (
                            <div key={idx} className="card" style={{ borderColor: 'var(--danger-color)' }}>
                                <div className="card-header">
                                    <h3 className="card-title">{anomaly.machine_id}</h3>
                                    <span className="status-badge status-error">ANOMALY DETECTED</span>
                                </div>
                                <div className="metric-row">
                                    <span>Time</span>
                                    <span className="metric-value">{new Date(anomaly.timestamp).toLocaleString()}</span>
                                </div>
                                <div className="metric-row">
                                    <span>Vibration</span>
                                    <span className="metric-value">{anomaly.vibration.toFixed(3)}</span>
                                </div>
                                <div className="metric-row">
                                    <span>Temperature</span>
                                    <span className="metric-value">{anomaly.temperature.toFixed(1)} °C</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            <section>
                <h2 className="section-title">Machine Status</h2>
                {loading ? (
                    <div className="loading">Loading dashboard...</div>
                ) : (
                    <div className="grid-container">
                        {machines.map(machine => (
                            <MachineCard key={machine.machine_id} machine={machine} />
                        ))}
                    </div>
                )}
            </section>

            <AIReportModal isOpen={isAIModalOpen} onClose={() => setIsAIModalOpen(false)} />
        </div>
    );
}

export default Dashboard;
