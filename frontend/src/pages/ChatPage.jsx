import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import html2pdf from 'html2pdf.js';
import KnowledgeBaseModal from '../components/KnowledgeBaseModal';

const ChatPage = () => {
    const [messages, setMessages] = useState([
        { role: 'agent', content: 'Hello! I am your AI Data Assistant. I can help you analyze machine performance, query databases, and troubleshoot anomalies.' }
    ]);
    const [showKB, setShowKB] = useState(false);
    const [llmProvider, setLlmProvider] = useState('local');
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState(''); // For intermediate steps
    const messagesEndRef = useRef(null);
    const navigate = useNavigate();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, status]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = input;
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setInput('');
        setLoading(true);
        setStatus('Starting...');

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

            // Prepare chat history (excluding the current user message which is passed as 'question')
            const chatHistory = messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await fetch(`${apiUrl}/agent/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: userMsg,
                    chat_history: chatHistory,
                    llm_provider: llmProvider
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep the last partial line in buffer

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.type === 'status') {
                            setStatus(data.content);
                        } else if (data.type === 'log') {
                            console.log("Agent Log:", data.content);
                        } else if (data.type === 'answer') {
                            setMessages(prev => [...prev, {
                                role: 'agent',
                                content: data.content,
                                chart_data: data.chart_data // Store chart data if present
                            }]);
                            setStatus('');
                        } else if (data.type === 'error') {
                            setMessages(prev => [...prev, { role: 'agent', content: `Error: ${data.content}` }]);
                            setStatus('');
                        }
                    } catch (e) {
                        console.error("Error parsing stream:", e);
                    }
                }
            }
        } catch (error) {
            console.error("Stream error:", error);
            setMessages(prev => [...prev, { role: 'agent', content: "Sorry, connection failed. Please try again." }]);
            setStatus('');
        } finally {
            setLoading(false);
            setStatus(''); // Ensure status is cleared
        }
    };

    const handleDownloadPDF = (elementId, userQuestion) => {
        const contentElement = document.getElementById(elementId);
        if (!contentElement) return;

        // Create a wrapper to hide the container from view but keep it in DOM
        const wrapper = document.createElement('div');
        wrapper.style.position = 'fixed';
        wrapper.style.top = '0';
        wrapper.style.left = '0';
        wrapper.style.width = '0';
        wrapper.style.height = '0';
        wrapper.style.overflow = 'hidden'; // Hide content
        document.body.appendChild(wrapper);

        // Create the actual container for the PDF content
        const container = document.createElement('div');
        container.style.width = '650px'; // Reduced width to fit A4 (approx 190mm printable)
        container.style.padding = '20px';
        container.style.fontFamily = 'Arial, sans-serif';
        container.style.color = '#000000';
        container.style.backgroundColor = '#ffffff';

        // Append container to wrapper
        wrapper.appendChild(container);

        // Header
        const header = document.createElement('div');
        header.innerHTML = `
            <h1 style="color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 10px; margin-bottom: 20px;">AI Analysis Report</h1>
            <p style="color: #666; font-size: 0.9rem; margin-bottom: 30px;">Generated on: ${new Date().toLocaleString()}</p>
        `;
        container.appendChild(header);

        // Question Section
        const questionSection = document.createElement('div');
        questionSection.style.marginBottom = '30px';
        questionSection.style.padding = '20px';
        questionSection.style.backgroundColor = '#f3f4f6';
        questionSection.style.borderRadius = '8px';
        questionSection.style.border = '1px solid #e5e7eb';
        questionSection.innerHTML = `
            <strong style="color: #374151; display: block; margin-bottom: 10px; font-size: 1.1rem;">Question:</strong>
            <div style="color: #1f2937; line-height: 1.5;">${userQuestion}</div>
        `;
        container.appendChild(questionSection);

        // Answer Section
        const answerSection = document.createElement('div');
        answerSection.innerHTML = `<strong style="color: #374151; display: block; margin-bottom: 15px; font-size: 1.1rem;">Analysis:</strong>`;

        // Clone the content
        const contentClone = contentElement.cloneNode(true);
        // Remove ID to avoid duplicates
        contentClone.removeAttribute('id');

        // Force styles on the clone to ensure visibility on white paper
        contentClone.style.color = '#000000';
        contentClone.style.background = 'transparent';
        contentClone.style.width = '100%';

        // Fix markdown tables in the clone
        const tables = contentClone.querySelectorAll('table');
        tables.forEach(table => {
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            table.style.marginBottom = '1rem';
            table.style.color = '#000';

            table.querySelectorAll('th, td').forEach(cell => {
                cell.style.border = '1px solid #cbd5e1';
                cell.style.padding = '8px';
                cell.style.color = '#000';
            });
            table.querySelectorAll('th').forEach(th => {
                th.style.backgroundColor = '#f1f5f9';
                th.style.fontWeight = 'bold';
            });
        });

        // Fix code blocks
        contentClone.querySelectorAll('pre, code').forEach(block => {
            block.style.backgroundColor = '#f8fafc';
            block.style.color = '#0f172a';
            block.style.border = '1px solid #e2e8f0';
            block.style.whiteSpace = 'pre-wrap'; // Ensure code wraps
            block.style.wordBreak = 'break-word';
        });

        answerSection.appendChild(contentClone);
        container.appendChild(answerSection);

        const opt = {
            margin: [10, 10, 10, 10],
            filename: `Analysis_Report_${new Date().toISOString().slice(0, 10)}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: {
                scale: 2,
                useCORS: true,
                logging: false,
                letterRendering: true
            },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
        };

        // Use a timeout to ensure DOM render before capture
        setTimeout(() => {
            html2pdf().set(opt).from(container).save().then(() => {
                document.body.removeChild(wrapper);
            });
        }, 500);
    };

    return (
        <div style={styles.container}>
            {/* Header */}
            <header style={styles.header}>
                <button onClick={() => navigate('/')} style={styles.backButton}>
                    ← Dashboard
                </button>
                <h1 style={styles.title}>AI Data Agent</h1>
                <div style={{ width: '200px', display: 'flex', gap: '10px', justifyContent: 'flex-end', alignItems: 'center' }}>
                    <select
                        value={llmProvider}
                        onChange={(e) => setLlmProvider(e.target.value)}
                        style={styles.select}
                    >
                        <option value="local">Local LLM</option>
                        <option value="openrouter">OpenRouter</option>
                    </select>
                    <button
                        onClick={() => setShowKB(true)}
                        style={styles.iconBtn}
                        title="Knowledge Base"
                    >
                        📚
                    </button>
                </div>
            </header>

            {/* Main Chat Area */}
            <div style={styles.chatArea}>
                <div style={styles.messagesContainer}>
                    {messages.map((msg, idx) => (
                        <div key={idx} style={{
                            ...styles.messageRow,
                            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                        }}>
                            {msg.role === 'agent' && (
                                <div style={styles.avatar}>AI</div>
                            )}
                            <div style={{
                                ...styles.bubble,
                                backgroundColor: msg.role === 'user' ? '#6366f1' : '#1e293b',
                                color: '#f8fafc',
                                borderBottomRightRadius: msg.role === 'user' ? '4px' : '16px',
                                borderBottomLeftRadius: msg.role === 'agent' ? '4px' : '16px',
                                marginLeft: msg.role === 'agent' ? '0.5rem' : '0',
                                marginRight: msg.role === 'user' ? '0' : '0',
                                whiteSpace: msg.role === 'user' ? 'pre-wrap' : 'normal', // Only pre-wrap user text
                            }}>
                                {msg.role === 'agent' ? (
                                    <div className="markdown-content" id={`msg-${idx}`}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                ) : (
                                    msg.content
                                )}

                                {/* Chart Rendering */}
                                {msg.chart_data && msg.chart_data.length > 0 && (
                                    <div style={{ marginTop: '1rem', width: '100%', height: '250px' }}>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={msg.chart_data}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                                <XAxis
                                                    dataKey="timestamp"
                                                    stroke="#94a3b8"
                                                    tick={{ fontSize: 12 }}
                                                    tickFormatter={(tick) => new Date(tick).toLocaleTimeString()}
                                                />
                                                <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                                                    itemStyle={{ color: '#f8fafc' }}
                                                />
                                                <Line type="monotone" dataKey="vibration" stroke="#8884d8" strokeWidth={2} dot={false} />
                                                <Line type="monotone" dataKey="temperature" stroke="#82ca9d" strokeWidth={2} dot={false} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}

                                {/* Download Button for Agent Messages */}
                                {msg.role === 'agent' && (
                                    <button
                                        onClick={() => {
                                            // Find the preceding user message
                                            const prevMsg = messages[idx - 1];
                                            const question = prevMsg && prevMsg.role === 'user' ? prevMsg.content : "Analysis Result";
                                            handleDownloadPDF(`msg-${idx}`, question);
                                        }}
                                        style={styles.downloadBtn}
                                        title="Download PDF Report"
                                    >
                                        📥 Download Report
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Status / Loading Indicator */}
                    {(loading || status) && (
                        <div style={styles.statusRow}>
                            <div style={styles.statusBubble}>
                                <span className="typing-dot"></span>
                                <span style={{ marginLeft: '8px' }}>{status || 'Processing...'}</span>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div style={styles.inputContainer}>
                <form onSubmit={handleSubmit} style={styles.inputWrapper}>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about machine status, anomalies, or sensor data..."
                        style={styles.input}
                        disabled={loading}
                    />
                    <button type="submit" style={styles.sendButton} disabled={loading || !input.trim()}>
                        ➤
                    </button>
                </form>
            </div>

            <style>{`
        .typing-dot {
          width: 8px;
          height: 8px;
          background-color: #94a3b8;
          border-radius: 50%;
          display: inline-block;
          animation: pulse 1.5s infinite ease-in-out;
        }
        @keyframes pulse {
          0% { transform: scale(0.8); opacity: 0.5; }
          50% { transform: scale(1.2); opacity: 1; }
          100% { transform: scale(0.8); opacity: 0.5; }
        }
        
        /* Markdown Styles */
        .markdown-content {
          font-size: 1rem;
          line-height: 1.5;
          text-align: left; /* Ensure left alignment */
        }
        .markdown-content p {
          margin: 0 0 0.75rem 0; /* Reduced margin */
        }
        .markdown-content p:last-child {
          margin-bottom: 0;
        }
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
          margin-top: 1rem; /* Reduced margin */
          margin-bottom: 0.5rem;
          font-weight: 600;
          color: #f1f5f9;
        }
        .markdown-content ul, .markdown-content ol {
          padding-left: 1.5rem;
          margin-bottom: 0.75rem; /* Reduced margin */
        }
        .markdown-content li {
          margin-bottom: 0.25rem;
        }
        .markdown-content code {
          background-color: rgba(0, 0, 0, 0.3);
          padding: 0.2rem 0.4rem;
          border-radius: 4px;
          font-family: monospace;
          font-size: 0.9em;
        }
        .markdown-content pre {
          background-color: rgba(0, 0, 0, 0.3);
          padding: 1rem;
          border-radius: 8px;
          overflow-x: auto;
          margin-bottom: 1rem;
        }
        .markdown-content pre code {
          background-color: transparent;
          padding: 0;
        }
        .markdown-content table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 1rem;
          font-size: 0.9rem;
        }
        .markdown-content th, .markdown-content td {
          border: 1px solid #334155;
          padding: 0.75rem;
          text-align: left;
        }
        .markdown-content th {
          background-color: rgba(255, 255, 255, 0.05);
          font-weight: 600;
        }
        .markdown-content tr:nth-child(even) {
          background-color: rgba(255, 255, 255, 0.02);
        }
        .markdown-content a {
          color: #38bdf8;
          text-decoration: none;
        }
        .markdown-content a:hover {
          text-decoration: underline;
        }
      `}</style>
            {showKB && <KnowledgeBaseModal onClose={() => setShowKB(false)} />}
        </div >
    );
};

const styles = {
    container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        backgroundColor: '#0f172a', // Dark slate background
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
    },
    header: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '70px',
        padding: '0 2rem',
        backgroundColor: 'rgba(30, 41, 59, 0.9)', // Semi-transparent
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid #334155',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 50,
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    },
    backButton: {
        background: 'transparent',
        border: '1px solid #475569',
        color: '#cbd5e1',
        padding: '0.5rem 1rem',
        borderRadius: '6px',
        cursor: 'pointer',
        transition: 'all 0.2s',
    },
    title: {
        fontSize: '1.25rem',
        fontWeight: '600',
        color: '#f8fafc',
        margin: 0,
    },
    chatArea: {
        flex: 1,
        overflowY: 'auto',
        padding: '100px 2rem 140px 2rem', // Large padding for top header and bottom input
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        height: '100vh', // Full height to allow scrolling
    },
    messagesContainer: {
        width: '100%',
        maxWidth: '1200px',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
    },
    messageRow: {
        display: 'flex',
        width: '100%',
        alignItems: 'flex-start', // Align avatars to top
    },
    avatar: {
        width: '36px',
        height: '36px',
        borderRadius: '50%',
        backgroundColor: '#6366f1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '0.8rem',
        fontWeight: 'bold',
        color: 'white',
        flexShrink: 0,
        marginTop: '4px',
    },
    bubble: {
        padding: '1rem 1.5rem',
        borderRadius: '16px',
        maxWidth: '85%',
        fontSize: '1rem',
        lineHeight: '1.5', // Slightly tighter line height
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        wordBreak: 'break-word',
    },
    statusRow: {
        display: 'flex',
        justifyContent: 'flex-start',
        marginTop: '0.5rem',
    },
    statusBubble: {
        display: 'flex',
        alignItems: 'center',
        padding: '0.5rem 1rem',
        backgroundColor: 'rgba(30, 41, 59, 0.5)',
        borderRadius: '20px',
        border: '1px solid #334155',
        color: '#94a3b8',
        fontSize: '0.875rem',
    },
    inputContainer: {
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '2rem',
        backgroundColor: '#1e293b',
        borderTop: '1px solid #334155',
        display: 'flex',
        justifyContent: 'center',
        zIndex: 50,
    },
    inputWrapper: {
        width: '100%',
        maxWidth: '1200px',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
    },
    input: {
        width: '100%',
        padding: '1rem 3.5rem 1rem 1.5rem',
        borderRadius: '12px',
        border: '1px solid #475569',
        backgroundColor: '#0f172a',
        color: 'white',
        fontSize: '1rem',
        outline: 'none',
        transition: 'border-color 0.2s',
    },
    sendButton: {
        position: 'absolute',
        right: '10px',
        background: '#6366f1',
        border: 'none',
        width: '40px',
        height: '40px',
        borderRadius: '8px',
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        transition: 'background 0.2s',
    },
    iconBtn: {
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        fontSize: '1.5rem',
    },
    select: {
        backgroundColor: '#1e293b',
        color: '#f8fafc',
        border: '1px solid #475569',
        borderRadius: '6px',
        padding: '0.25rem 0.5rem',
        fontSize: '0.9rem',
        outline: 'none',
    },
    downloadBtn: {
        background: 'rgba(99, 102, 241, 0.2)',
        border: '1px solid #6366f1',
        color: '#a5b4fc',
        padding: '6px 12px',
        borderRadius: '6px',
        cursor: 'pointer',
        fontSize: '0.8rem',
        marginTop: '12px',
        transition: 'all 0.2s',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginLeft: 'auto',
        fontWeight: '500'
    }
};

export default ChatPage;
