import React, { useState, useEffect } from 'react';
import axios from 'axios';

const KnowledgeBaseModal = ({ onClose }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [documents, setDocuments] = useState([]);
    const [vectors, setVectors] = useState([]);
    const [showVectors, setShowVectors] = useState(false);
    const [message, setMessage] = useState('');

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = async () => {
        try {
            const res = await axios.get(`${apiUrl}/documents`);
            setDocuments(res.data);
        } catch (err) {
            console.error("Error fetching documents", err);
        }
    };

    const fetchVectors = async () => {
        try {
            const res = await axios.get(`${apiUrl}/vectors`);
            setVectors(res.data);
            setShowVectors(true);
        } catch (err) {
            console.error("Error fetching vectors", err);
        }
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setMessage('');

        const formData = new FormData();
        formData.append('file', file);

        try {
            await axios.post(`${apiUrl}/upload-doc`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setMessage('Upload successful!');
            setFile(null);
            fetchDocuments();
        } catch (err) {
            setMessage('Upload failed.');
            console.error(err);
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (filename) => {
        if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

        try {
            await axios.delete(`${apiUrl}/delete-doc`, { params: { filename } });
            setMessage(`Deleted ${filename}`);
            fetchDocuments();
            // Optionally refresh vectors if they are being viewed
            if (showVectors) fetchVectors();
        } catch (err) {
            console.error("Error deleting document", err);
            setMessage("Failed to delete document.");
        }
    };

    return (
        <div style={styles.overlay}>
            <div style={styles.modal}>
                <div style={styles.header}>
                    <h2>Knowledge Base</h2>
                    <button onClick={onClose} style={styles.closeBtn}>✕</button>
                </div>

                <div style={styles.content}>
                    {/* Upload Section */}
                    <div style={styles.section}>
                        <h3>Upload Document</h3>
                        <div style={styles.uploadRow}>
                            <input type="file" onChange={handleFileChange} style={styles.fileInput} />
                            <button
                                onClick={handleUpload}
                                disabled={!file || uploading}
                                style={styles.uploadBtn}
                            >
                                {uploading ? 'Uploading...' : 'Upload'}
                            </button>
                        </div>
                        {message && <p style={styles.statusMsg}>{message}</p>}
                    </div>

                    {/* Documents List */}
                    <div style={styles.section}>
                        <h3>Indexed Documents</h3>
                        {documents.length === 0 ? (
                            <p style={{ opacity: 0.5 }}>No documents indexed.</p>
                        ) : (
                            <ul style={styles.list}>
                                {documents.map((doc, idx) => (
                                    <li key={idx} style={styles.listItem}>
                                        <span>📄 {doc}</span>
                                        <button
                                            onClick={() => handleDelete(doc)}
                                            style={styles.deleteBtn}
                                            title="Delete Document"
                                        >
                                            🗑️
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {/* Vector Inspection */}
                    <div style={styles.section}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h3>Vector Store</h3>
                            <button onClick={fetchVectors} style={styles.inspectBtn}>
                                🔍 Inspect Vectors
                            </button>
                        </div>

                        {showVectors && (
                            <div style={styles.vectorView}>
                                {vectors.map((v, idx) => (
                                    <div key={idx} style={styles.vectorCard}>
                                        <div style={styles.vectorMeta}>
                                            <strong>Source:</strong> {v.source}
                                        </div>
                                        <div style={styles.vectorContent}>
                                            "{v.content_preview}"
                                        </div>
                                        <div style={styles.vectorArray}>
                                            Vector: [{v.embedding_preview.join(', ')}]
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

const styles = {
    overlay: {
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 3000,
    },
    modal: {
        backgroundColor: '#1a1b26',
        width: '600px',
        maxHeight: '80vh',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        flexDirection: 'column',
        color: 'white',
        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
    },
    header: {
        padding: '1.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    closeBtn: {
        background: 'none',
        border: 'none',
        color: 'white',
        fontSize: '1.5rem',
        cursor: 'pointer',
    },
    content: {
        padding: '1.5rem',
        overflowY: 'auto',
    },
    section: {
        marginBottom: '2rem',
    },
    uploadRow: {
        display: 'flex',
        gap: '1rem',
        marginTop: '1rem',
    },
    fileInput: {
        flex: 1,
        padding: '0.5rem',
        backgroundColor: 'rgba(255,255,255,0.05)',
        borderRadius: '6px',
        color: 'white',
    },
    uploadBtn: {
        backgroundColor: '#6366f1',
        color: 'white',
        border: 'none',
        padding: '0.5rem 1.5rem',
        borderRadius: '6px',
        cursor: 'pointer',
        fontWeight: 'bold',
    },
    statusMsg: {
        marginTop: '0.5rem',
        color: '#4ade80',
        fontSize: '0.9rem',
    },
    list: {
        listStyle: 'none',
        padding: 0,
        margin: '1rem 0',
    },
    listItem: {
        padding: '0.5rem',
        backgroundColor: 'rgba(255,255,255,0.05)',
        marginBottom: '0.5rem',
        borderRadius: '4px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    deleteBtn: {
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        fontSize: '1rem',
        opacity: 0.7,
        transition: 'opacity 0.2s',
    },
    inspectBtn: {
        backgroundColor: 'transparent',
        border: '1px solid #6366f1',
        color: '#6366f1',
        padding: '0.3rem 1rem',
        borderRadius: '4px',
        cursor: 'pointer',
    },
    vectorView: {
        marginTop: '1rem',
        backgroundColor: 'rgba(0,0,0,0.3)',
        padding: '1rem',
        borderRadius: '8px',
        maxHeight: '300px',
        overflowY: 'auto',
    },
    vectorCard: {
        marginBottom: '1rem',
        padding: '1rem',
        backgroundColor: 'rgba(255,255,255,0.05)',
        borderRadius: '6px',
        fontSize: '0.9rem',
    },
    vectorMeta: {
        color: '#a5b4fc',
        marginBottom: '0.5rem',
    },
    vectorContent: {
        fontStyle: 'italic',
        opacity: 0.8,
        marginBottom: '0.5rem',
    },
    vectorArray: {
        fontFamily: 'monospace',
        fontSize: '0.8rem',
        color: '#4ade80',
    }
};

export default KnowledgeBaseModal;
