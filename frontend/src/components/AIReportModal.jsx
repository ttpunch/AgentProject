import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AIReportModal = ({ isOpen, onClose }) => {
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [typedSummary, setTypedSummary] = useState('');

    useEffect(() => {
        if (isOpen) {
            generateReport();
        } else {
            setReport(null);
            setTypedSummary('');
        }
    }, [isOpen]);

    useEffect(() => {
        if (report && report.summary) {
            let i = 0;
            const speed = 30;
            const typeWriter = () => {
                if (i < report.summary.length) {
                    setTypedSummary((prev) => prev + report.summary.charAt(i));
                    i++;
                    setTimeout(typeWriter, speed);
                }
            };
            setTypedSummary('');
            typeWriter();
        }
    }, [report]);

    const generateReport = async () => {
        setLoading(true);
        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await axios.get(`${apiUrl}/ai/report`);
            // Simulate "thinking" time for effect
            setTimeout(() => {
                setReport(response.data);
                setLoading(false);
            }, 1500);
        } catch (error) {
            console.error("Error generating report:", error);
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={styles.overlay}>
            <div style={styles.modal}>
                <button style={styles.closeButton} onClick={onClose}>×</button>

                <div style={styles.header}>
                    <h2 style={styles.title}>✨ AI Maintenance Insights</h2>
                </div>

                <div style={styles.content}>
                    {loading ? (
                        <div style={styles.loadingContainer}>
                            <div className="spinner"></div>
                            <p style={{ marginTop: '1rem', color: '#a0aec0' }}>Analyzing system telemetry...</p>
                        </div>
                    ) : report ? (
                        <>
                            <div style={styles.riskSection}>
                                <span style={{ color: '#a0aec0', fontSize: '0.9rem' }}>RISK LEVEL</span>
                                <div style={{
                                    ...styles.riskBadge,
                                    backgroundColor: getRiskColor(report.risk_level),
                                    boxShadow: `0 0 20px ${getRiskColor(report.risk_level)}40`
                                }}>
                                    {report.risk_level}
                                </div>
                            </div>

                            <div style={styles.summaryBox}>
                                <p style={styles.summaryText}>{typedSummary}<span className="cursor">|</span></p>
                            </div>

                            <div style={styles.grid}>
                                <div style={styles.card}>
                                    <h4 style={styles.cardTitle}>System Health</h4>
                                    <div style={styles.score}>{report.risk_score}<span style={{ fontSize: '1rem' }}>/100</span></div>
                                </div>
                                <div style={styles.card}>
                                    <h4 style={styles.cardTitle}>Key Insights</h4>
                                    <ul style={styles.list}>
                                        {report.insights.map((insight, idx) => (
                                            <li key={idx} style={styles.listItem}>• {insight}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            <div style={styles.recommendations}>
                                <h4 style={styles.cardTitle}>Recommended Actions</h4>
                                <ul style={styles.list}>
                                    {report.recommendations.map((rec, idx) => (
                                        <li key={idx} style={styles.listItem}>→ {rec}</li>
                                    ))}
                                </ul>
                            </div>
                        </>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '2rem' }}>Failed to load report.</div>
                    )}
                </div>
            </div>
            <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .spinner { border: 4px solid rgba(255,255,255,0.1); border-left-color: #6366f1; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }
        .cursor { animation: blink 1s step-end infinite; }
        @keyframes blink { 50% { opacity: 0; } }
      `}</style>
        </div>
    );
};

const getRiskColor = (level) => {
    switch (level) {
        case 'LOW': return '#10b981'; // Emerald
        case 'MODERATE': return '#f59e0b'; // Amber
        case 'CRITICAL': return '#ef4444'; // Red
        default: return '#6366f1';
    }
};

const styles = {
    overlay: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
    },
    modal: {
        backgroundColor: '#1a1b26',
        width: '90%',
        maxWidth: '600px',
        borderRadius: '16px',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        overflow: 'hidden',
        position: 'relative',
        color: '#fff',
        fontFamily: "'Inter', sans-serif",
    },
    closeButton: {
        position: 'absolute',
        top: '1rem',
        right: '1rem',
        background: 'none',
        border: 'none',
        color: '#a0aec0',
        fontSize: '1.5rem',
        cursor: 'pointer',
        zIndex: 10,
    },
    header: {
        padding: '1.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        background: 'linear-gradient(to right, rgba(99, 102, 241, 0.1), transparent)',
    },
    title: {
        margin: 0,
        fontSize: '1.25rem',
        fontWeight: 600,
        background: 'linear-gradient(to right, #fff, #a5b4fc)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
    },
    content: {
        padding: '1.5rem',
    },
    loadingContainer: {
        textAlign: 'center',
        padding: '3rem 0',
    },
    riskSection: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        marginBottom: '1.5rem',
    },
    riskBadge: {
        marginTop: '0.5rem',
        padding: '0.5rem 1.5rem',
        borderRadius: '9999px',
        fontWeight: 'bold',
        fontSize: '1.2rem',
        letterSpacing: '0.05em',
    },
    summaryBox: {
        backgroundColor: 'rgba(255,255,255,0.03)',
        padding: '1rem',
        borderRadius: '8px',
        marginBottom: '1.5rem',
        borderLeft: '3px solid #6366f1',
        minHeight: '60px',
    },
    summaryText: {
        margin: 0,
        lineHeight: 1.6,
        color: '#e2e8f0',
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: '1fr 1.5fr',
        gap: '1rem',
        marginBottom: '1.5rem',
    },
    card: {
        backgroundColor: 'rgba(255,255,255,0.03)',
        padding: '1rem',
        borderRadius: '8px',
    },
    cardTitle: {
        margin: '0 0 0.75rem 0',
        fontSize: '0.9rem',
        color: '#a0aec0',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
    },
    score: {
        fontSize: '2.5rem',
        fontWeight: 'bold',
        color: '#fff',
    },
    list: {
        margin: 0,
        padding: 0,
        listStyle: 'none',
    },
    listItem: {
        marginBottom: '0.5rem',
        fontSize: '0.9rem',
        color: '#cbd5e1',
    },
    recommendations: {
        backgroundColor: 'rgba(16, 185, 129, 0.05)',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid rgba(16, 185, 129, 0.1)',
    }
};

export default AIReportModal;
