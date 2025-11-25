import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import KnowledgeBaseModal from './KnowledgeBaseModal';
import { AnomalyChart, ForecastChart } from './AnalyticsCharts';
import html2pdf from 'html2pdf.js';

const AgentChat = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [showKB, setShowKB] = useState(false);
    const [llmProvider, setLlmProvider] = useState('local');
    const [messages, setMessages] = useState([
        { role: 'agent', content: 'Hello! I am your AI Data Assistant. Ask me anything about your machines or sensor data.' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = input;
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setInput('');
        setLoading(true);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

            // Prepare chat history
            const history = messages.map(msg => ({
                role: msg.role === 'agent' ? 'assistant' : msg.role,
                content: msg.content
            })).filter(msg => msg.role !== 'system');

            // Use fetch for streaming
            const response = await fetch(`${apiUrl}/agent/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: userMsg,
                    chat_history: history,
                    llm_provider: llmProvider
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                console.log("Stream chunk received:", chunk);
                buffer += chunk;

                let lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine) continue;
                    try {
                        const data = JSON.parse(trimmedLine);
                        processStreamData(data);
                    } catch (e) {
                        console.error("Error parsing stream line:", trimmedLine, e);
                    }
                }
            }

            // Process remaining buffer
            if (buffer.trim()) {
                console.log("Processing remaining buffer:", buffer);
                try {
                    const data = JSON.parse(buffer.trim());
                    processStreamData(data);
                } catch (e) {
                    console.error("Error parsing remaining buffer:", buffer, e);
                }
            }

        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, { role: 'agent', content: "Sorry, I couldn't process that request." }]);
        } finally {
            setLoading(false);
        }
    };

    const processStreamData = (data) => {
        if (data.type === 'answer') {
            setMessages(prev => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg && lastMsg.role === 'agent' && !lastMsg.isStatus) {
                    return [...prev, {
                        role: 'agent',
                        content: data.content,
                        chart_data: data.chart_data,
                        chart_type: data.chart_type
                    }];
                }
                return [...prev, {
                    role: 'agent',
                    content: data.content,
                    chart_data: data.chart_data,
                    chart_type: data.chart_type
                }];
            });
        } else if (data.type === 'status') {
            setMessages(prev => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg && lastMsg.isStatus) {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1] = { ...lastMsg, content: data.content };
                    return newMsgs;
                }
                return [...prev, { role: 'system', content: data.content, isStatus: true }];
            });
        } else if (data.type === 'error') {
            setMessages(prev => [...prev, { role: 'agent', content: `Error: ${data.content}` }]);
        }
    };

    const handleDownloadPDF = (elementId, userQuestion) => {
        const contentElement = document.getElementById(elementId);
        if (!contentElement) return;

        // Create a temporary container for the PDF
        const container = document.createElement('div');
        container.style.padding = '20px';
        container.style.fontFamily = 'Arial, sans-serif';
        container.style.color = '#000';
        container.style.background = '#fff';

        // Header
        const header = document.createElement('div');
        header.innerHTML = `
            <h1 style="color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 10px;">AI Analysis Report</h1>
            <p style="color: #666; font-size: 0.9rem;">Generated on: ${new Date().toLocaleString()}</p>
        `;
        container.appendChild(header);

        // Question Section
        const questionSection = document.createElement('div');
        questionSection.style.marginTop = '20px';
        questionSection.style.marginBottom = '20px';
        questionSection.style.padding = '15px';
        questionSection.style.backgroundColor = '#f3f4f6';
        questionSection.style.borderRadius = '8px';
        questionSection.innerHTML = `
            <strong style="color: #374151; display: block; margin-bottom: 5px;">Question:</strong>
            <div style="color: #1f2937;">${userQuestion}</div>
        `;
        container.appendChild(questionSection);

        // Answer Section
        const answerSection = document.createElement('div');
        answerSection.style.marginTop = '20px';
        answerSection.innerHTML = `<strong style="color: #374151; display: block; margin-bottom: 10px;">Analysis:</strong>`;

        // Clone the content to avoid messing up the UI
        const contentClone = contentElement.cloneNode(true);
        // Fix colors for PDF (since UI is dark mode)
        contentClone.style.color = '#000';
        const markdownContent = contentClone.querySelector('.markdown-content');
        if (markdownContent) {
            const tables = markdownContent.querySelectorAll('table');
            tables.forEach(table => {
                table.style.borderCollapse = 'collapse';
                table.style.width = '100%';
                table.querySelectorAll('th, td').forEach(cell => {
                    cell.style.border = '1px solid #ddd';
                    cell.style.padding = '8px';
                    cell.style.color = '#000';
                });
                table.querySelectorAll('th').forEach(th => {
                    th.style.backgroundColor = '#f3f4f6';
                    th.style.fontWeight = 'bold';
                });
            });
        }

        answerSection.appendChild(contentClone);
        container.appendChild(answerSection);

        // Append to body (hidden) to allow html2pdf to render it
        container.style.position = 'absolute';
        container.style.left = '-9999px';
        document.body.appendChild(container);

        const opt = {
            margin: 10,
            filename: `Analysis_Report_${new Date().toISOString().slice(0, 10)}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(container).save().then(() => {
            document.body.removeChild(container);
        });
    };

    return (
        <>
            {/* Floating Action Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={styles.fab}
            >
                {isOpen ? '✕' : '💬'}
            </button>

            {/* Chat Window */}
            {isOpen && (
                <div style={styles.chatWindow}>
                    <div style={styles.header}>
                        <h3 style={{ margin: 0, fontSize: '1rem' }}>AI Data Agent</h3>
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                            <button
                                onClick={() => setShowKB(true)}
                                style={styles.iconBtn}
                                title="Knowledge Base"
                            >
                                📚
                            </button>
                            <select
                                value={llmProvider}
                                onChange={(e) => setLlmProvider(e.target.value)}
                                style={styles.select}
                            >
                                <option value="local">Local</option>
                                <option value="openrouter">Cloud</option>
                            </select>
                        </div>
                    </div>

                    <div style={styles.messagesArea}>
                        {messages.map((msg, idx) => (
                            <div key={idx} style={{
                                ...styles.messageRow,
                                justifyContent: msg.role === 'user' ? 'flex-end' : (msg.role === 'system' ? 'center' : 'flex-start')
                            }}>
                                <div style={
                                    msg.role === 'system'
                                        ? styles.systemBubble
                                        : {
                                            ...styles.bubble,
                                            backgroundColor: msg.role === 'user' ? '#6366f1' : 'rgba(255,255,255,0.1)',
                                            color: '#fff',
                                            borderBottomRightRadius: msg.role === 'user' ? '4px' : '16px',
                                            borderBottomLeftRadius: msg.role === 'agent' ? '4px' : '16px',
                                            position: 'relative'
                                        }
                                }>
                                    {msg.role === 'agent' && (
                                        <div id={`msg-${idx}`}>
                                            <div className="markdown-content">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {msg.content}
                                                </ReactMarkdown>
                                            </div>
                                            {msg.chart_data && msg.chart_type === 'scatter_anomaly' && (
                                                <div style={{ marginTop: '10px', height: '200px', width: '100%' }}>
                                                    <AnomalyChart data={msg.chart_data} />
                                                </div>
                                            )}
                                            {msg.chart_data && msg.chart_type === 'forecast' && (
                                                <div style={{ marginTop: '10px', height: '200px', width: '100%' }}>
                                                    <ForecastChart data={msg.chart_data} />
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {msg.role === 'user' && msg.content}

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

                        {loading && (
                            <div style={styles.messageRow}>
                                <div style={{ ...styles.bubble, backgroundColor: 'rgba(255,255,255,0.1)' }}>
                                    <span className="typing-dot">.</span><span className="typing-dot">.</span><span className="typing-dot">.</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <form onSubmit={handleSubmit} style={styles.inputArea}>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about machines..."
                            style={styles.input}
                        />
                        <button type="submit" style={styles.sendButton} disabled={loading}>
                            ➤
                        </button>
                    </form>
                </div>
            )}
            <style>{`
        .typing-dot { animation: typing 1.4s infinite ease-in-out both; margin: 0 2px; }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes typing { 0%, 80%, 100% { opacity: 0; } 40% { opacity: 1; } }
        
        /* Markdown Styles */
        .markdown-content p { margin: 0 0 10px 0; }
        .markdown-content p:last-child { margin: 0; }
        .markdown-content ul, .markdown-content ol { margin: 0 0 10px 0; padding-left: 20px; }
        .markdown-content li { margin-bottom: 5px; }
        .markdown-content code { background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 4px; font-family: monospace; }
        .markdown-content pre { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; overflow-x: auto; }
        .markdown-content pre code { background: none; padding: 0; }
        .markdown-content table { border-collapse: collapse; width: 100%; margin-bottom: 10px; font-size: 0.85rem; }
        .markdown-content th, .markdown-content td { border: 1px solid rgba(255,255,255,0.2); padding: 6px; text-align: left; }
        .markdown-content th { background: rgba(255,255,255,0.1); font-weight: bold; }
      `}</style>
            {showKB && <KnowledgeBaseModal onClose={() => setShowKB(false)} />}
        </>
    );
};

const styles = {
    fab: {
        position: 'fixed',
        bottom: '2rem',
        right: '2rem',
        width: '60px',
        height: '60px',
        borderRadius: '50%',
        backgroundColor: '#6366f1',
        color: 'white',
        border: 'none',
        fontSize: '1.5rem',
        cursor: 'pointer',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    chatWindow: {
        position: 'fixed',
        bottom: '7rem',
        right: '2rem',
        width: '350px',
        height: '500px',
        backgroundColor: '#1a1b26',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 2000,
        overflow: 'hidden',
    },
    header: {
        padding: '1rem',
        backgroundColor: '#6366f1',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    messagesArea: {
        flex: 1,
        padding: '1rem',
        paddingTop: '2.5rem', // Increased top padding for clear gap
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem', // Increased gap between messages
    },
    messageRow: {
        display: 'flex',
        width: '100%',
    },
    bubble: {
        padding: '0.75rem 1rem',
        borderRadius: '16px',
        maxWidth: '80%',
        fontSize: '0.9rem',
        lineHeight: '1.4',
    },
    systemBubble: {
        padding: '0.5rem 1rem',
        borderRadius: '8px',
        maxWidth: '90%',
        fontSize: '0.8rem',
        backgroundColor: 'rgba(255,255,255,0.05)',
        color: '#aaa',
        margin: '0 auto',
        textAlign: 'center',
        fontStyle: 'italic',
    },
    inputArea: {
        padding: '1rem',
        borderTop: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        gap: '0.5rem',
    },
    input: {
        flex: 1,
        padding: '0.75rem',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.2)',
        backgroundColor: 'rgba(0,0,0,0.2)',
        color: 'white',
        outline: 'none',
    },
    sendButton: {
        background: 'none',
        border: 'none',
        color: '#6366f1',
        fontSize: '1.2rem',
        cursor: 'pointer',
        padding: '0 0.5rem',
    },
    iconBtn: {
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        fontSize: '1.2rem',
    },
    select: {
        backgroundColor: 'rgba(255,255,255,0.1)',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        fontSize: '0.8rem',
        padding: '2px 4px',
        outline: 'none',
    },
    actionBtn: {
        border: 'none',
        color: 'white',
        padding: '5px 10px',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.9rem',
        fontWeight: 'bold',
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

export default AgentChat;
