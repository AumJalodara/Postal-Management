import React, { useState } from 'react';
import { MessageSquare, Send, BookOpen, AlertTriangle, Loader2, FileText, ChevronDown, ChevronUp, Shield, Globe, ExternalLink, Info } from 'lucide-react';
import api from '../services/api';

export default function PostalAssistant() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [expandedCitations, setExpandedCitations] = useState({});
  const [expandedText, setExpandedText] = useState({});
  const [showRawOcr, setShowRawOcr] = useState({});

  const toggleCitation = (id) => {
    setExpandedCitations(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleText = (id, e) => {
    e.stopPropagation();
    setExpandedText(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleRawOcr = (id, e) => {
    if (e) e.stopPropagation();
    setShowRawOcr(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await api.post('/postal/ask', {
        query: query.trim(),
        top_k: 5,
        retrieval_mode: 'hybrid',
      });

      if (response.data?.success && response.data?.data) {
        setResult(response.data.data);
      } else {
        setError('Unexpected response format from the server.');
      }
    } catch (err) {
      if (err.response?.data?.error?.message) {
        setError(err.response.data.error.message);
      } else if (err.response?.status === 503) {
        setError('The AI assistant service is temporarily unavailable. Please try again later.');
      } else {
        setError('Failed to connect to the postal assistant. Please check that the backend is running.');
      }
    } finally {
      setLoading(false);
    }
  };

  const exampleQuestions = [
    "What does Section 9 of the Post Office Act say?",
    "How to apply for passport in post office?",
    "What are the Post Office Savings Account & MIS interest rates?",
    "What are the conditions for Speed Post service?",
    "What is the procedure for delivering damaged items?",
    "What are the Smart Delivery Box regulations?",
  ];

  return (
    <div className="assistant-page">
      <div className="container" style={{ maxWidth: '860px', margin: '0 auto', padding: '32px 16px' }}>

        {/* Header */}
        <div className="assistant-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <div style={{ background: 'var(--accent-saffron)', padding: '10px', borderRadius: '10px', display: 'flex' }}>
              <MessageSquare size={24} color="#fff" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
                Postal Regulations Assistant
              </h1>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                Ask questions about official Indian postal laws and regulations
              </p>
            </div>
          </div>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSubmit} className="assistant-search-form">
          <div className="assistant-input-group">
            <input
              id="postal-question-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about postal regulations..."
              className="assistant-input"
              maxLength={1000}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn btn-primary assistant-submit-btn"
              disabled={loading || !query.trim()}
            >
              {loading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
              {loading ? 'Searching...' : 'Ask'}
            </button>
          </div>
        </form>

        {/* Example Questions */}
        {!result && !loading && !error && (
          <div className="assistant-examples">
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '10px', fontWeight: 500 }}>
              Try asking:
            </p>
            <div className="assistant-example-grid">
              {exampleQuestions.map((q, i) => (
                <button
                  key={i}
                  className="assistant-example-btn"
                  onClick={() => setQuery(q)}
                >
                  <MessageSquare size={14} />
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="assistant-error">
            <AlertTriangle size={18} />
            <div>
              <strong>Error</strong>
              <p style={{ margin: '4px 0 0' }}>{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="assistant-loading">
            <Loader2 size={24} className="spin" />
            <p>Searching official postal documents and generating a grounded answer...</p>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="assistant-result">

            {/* Insufficient Evidence */}
            {result.insufficient_evidence ? (
              <div className="assistant-insufficient">
                <AlertTriangle size={20} />
                <div>
                  <strong>Insufficient Evidence</strong>
                  <p style={{ margin: '6px 0 0' }}>{result.answer}</p>
                </div>
              </div>
            ) : (
              <>
                {/* Non-Statutory / Web-Enhanced Banner */}
                {result.not_in_docs && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    padding: '14px 16px',
                    backgroundColor: '#eff6ff',
                    border: '1px solid #bfdbfe',
                    borderLeft: '4px solid #3b82f6',
                    borderRadius: '8px',
                    marginBottom: '16px',
                    fontSize: '0.88rem',
                    color: '#1e40af'
                  }}>
                    <Info size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#2563eb' }} />
                    <div>
                      <strong style={{ display: 'block', marginBottom: '2px' }}>Operational / Citizen Service Inquiry</strong>
                      <span style={{ color: '#1e3a8a' }}>
                        This specific query is not addressed in the statutory postal legal acts. The answer below is synthesized from live verified India Post public guidelines and official portals.
                      </span>
                    </div>
                  </div>
                )}

                {/* AI-Generated Answer */}
                <div className="assistant-answer-section">
                  <div className="assistant-section-header">
                    <div className="ai-badge" style={result.web_search_used ? { backgroundColor: '#e0f2fe', color: '#0369a1', borderColor: '#bae6fd' } : undefined}>
                      {result.web_search_used ? <Globe size={14} /> : <MessageSquare size={14} />}
                      {result.not_in_docs ? 'Web-Enhanced Postal Information' : (result.web_search_used ? 'Statutory & Web-Grounded Answer' : 'AI-Generated Explanation')}
                    </div>
                    {result.has_invalid_citations && (
                      <span className="assistant-warning-badge">
                        ⚠ Some citation references could not be verified
                      </span>
                    )}
                  </div>
                  <div className="assistant-answer-text" style={{ whiteSpace: 'pre-line', lineHeight: '1.7' }}>
                    {result.answer}
                  </div>
                  <div className="assistant-meta">
                    <span>{result.retrieved_chunks} statutory source{result.retrieved_chunks !== 1 ? 's' : ''} retrieved</span>
                    {result.web_sources && result.web_sources.length > 0 && (
                      <span style={{ color: '#0284c7', fontWeight: 600 }}>
                        • {result.web_sources.length} web source{result.web_sources.length !== 1 ? 's' : ''} referenced
                      </span>
                    )}
                    <span>Mode: {result.retrieval_mode}</span>
                  </div>
                </div>

                {/* Verified Web Sources Section */}
                {result.web_sources && result.web_sources.length > 0 && (
                  <div className="assistant-sources-section" style={{ marginTop: '24px' }}>
                    <div className="assistant-section-header">
                      <div className="source-badge" style={{ backgroundColor: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' }}>
                        <Globe size={14} />
                        Verified Postal Web & Official Portal Sources
                      </div>
                    </div>
                    <div className="web-sources-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px', marginTop: '12px' }}>
                      {result.web_sources.map((ws) => (
                        <div key={ws.source_id} style={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: '8px',
                          padding: '14px',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                              <span style={{ fontSize: '0.75rem', fontWeight: 700, backgroundColor: '#0284c7', color: '#fff', padding: '2px 8px', borderRadius: '4px' }}>
                                [Web-{ws.source_id}]
                              </span>
                              <span style={{ fontSize: '0.72rem', backgroundColor: '#f1f5f9', color: '#475569', padding: '2px 6px', borderRadius: '4px', fontWeight: 500 }}>
                                {ws.source_type || 'Official Portal'}
                              </span>
                            </div>
                            <div style={{ fontWeight: 600, fontSize: '0.92rem', color: '#0f172a', marginBottom: '6px' }}>
                              {ws.title}
                            </div>
                            {ws.snippet && (
                              <p style={{ fontSize: '0.82rem', color: '#64748b', margin: '0 0 12px 0', lineHeight: '1.45' }}>
                                {ws.snippet}
                              </p>
                            )}
                          </div>
                          <a
                            href={ws.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              fontSize: '0.82rem',
                              color: '#0284c7',
                              fontWeight: 600,
                              textDecoration: 'none',
                              paddingTop: '8px',
                              borderTop: '1px solid #f1f5f9'
                            }}
                          >
                            Visit Official Portal <ExternalLink size={13} />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Official Statutory Source Citations */}
                {result.citations && result.citations.length > 0 && (
                  <div className="assistant-sources-section">
                    <div className="assistant-section-header">
                      <div className="source-badge">
                        <BookOpen size={14} />
                        Relevant Official Evidence
                      </div>
                    </div>
                    <div className="assistant-citations-list">
                      {result.citations.map((citation) => (
                        <div key={citation.citation_id} className="citation-card" style={{ marginBottom: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', backgroundColor: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                          <button
                            className="citation-header"
                            onClick={() => toggleCitation(citation.citation_id)}
                            style={{
                              width: '100%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '14px 16px',
                              border: 'none',
                              background: '#f8fafc',
                              borderBottom: expandedCitations[citation.citation_id] ? '1px solid #e2e8f0' : 'none',
                              cursor: 'pointer',
                              borderTopLeftRadius: '8px',
                              borderTopRightRadius: '8px',
                              borderBottomLeftRadius: expandedCitations[citation.citation_id] ? '0' : '8px',
                              borderBottomRightRadius: expandedCitations[citation.citation_id] ? '0' : '8px'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <div style={{ backgroundColor: 'var(--primary-navy)', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontWeight: 600, fontSize: '0.9rem' }}>[{citation.citation_id}]</div>
                              <div style={{ textAlign: 'left' }}>
                                <div style={{ fontWeight: 600, color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                  <span>{citation.document_title}</span>
                                  {citation.clean_text && (
                                    <span style={{ fontSize: '0.72rem', backgroundColor: '#e0f2fe', color: '#0369a1', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                      Official Text
                                    </span>
                                  )}
                                  {citation.ocr_anomaly && (
                                    <span style={{ fontSize: '0.72rem', backgroundColor: '#fef3c7', color: '#92400e', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                      Scanned Gazette
                                    </span>
                                  )}
                                </div>
                                <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '2px' }}>
                                  <strong>{citation.legal_reference}</strong>
                                  {citation.heading && <span style={{ color: '#1e293b' }}> — {citation.heading}</span>}
                                  <span style={{ color: '#94a3b8' }}> • Page {citation.page}</span>
                                </div>
                              </div>
                            </div>
                            {expandedCitations[citation.citation_id] ? <ChevronUp size={20} color="#64748b" /> : <ChevronDown size={20} color="#64748b" />}
                          </button>
                          
                          {expandedCitations[citation.citation_id] && (
                            <div className="citation-details" style={{ padding: '16px' }}>
                              <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                gap: '10px',
                                marginBottom: '14px',
                                padding: '12px',
                                backgroundColor: '#f8fafc',
                                borderRadius: '6px',
                                border: '1px solid #e2e8f0',
                                fontSize: '0.85rem',
                                color: '#475569'
                              }}>
                                <div><strong>Document ID:</strong> {citation.document_id}</div>
                                <div><strong>Regulation:</strong> {citation.legal_reference}</div>
                                {citation.heading && (
                                  <div style={{ gridColumn: '1 / -1' }}>
                                    <strong>Statutory Title:</strong> <span style={{ color: '#0f172a', fontWeight: 600 }}>{citation.heading}</span>
                                  </div>
                                )}
                                <div><strong>Page:</strong> {citation.page}</div>
                                {citation.source_pages && citation.source_pages.length > 1 && (
                                  <div><strong>Source Pages:</strong> {citation.source_pages.join(', ')}</div>
                                )}
                                <div><strong>Chunk ID:</strong> <code>{citation.chunk_id}</code></div>
                              </div>

                              {/* OCR Anomaly Informational Banner */}
                              {citation.ocr_anomaly && (
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'flex-start',
                                  gap: '8px',
                                  padding: '10px 14px',
                                  backgroundColor: '#fffbeb',
                                  border: '1px solid #fef3c7',
                                  borderLeft: '4px solid #f59e0b',
                                  borderRadius: '6px',
                                  marginBottom: '14px',
                                  fontSize: '0.82rem',
                                  color: '#92400e'
                                }}>
                                  <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px', color: '#f59e0b' }} />
                                  <div>
                                    <strong>Official Gazette Scanned Source:</strong> Authoritative clean statutory transcription is presented below for readability.
                                    {citation.anomaly_note && (
                                      <div style={{ marginTop: '2px', color: '#b45309', fontSize: '0.78rem' }}>
                                        Raw OCR Note: {citation.anomaly_note}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                              
                              {/* Main Statutory Text Container */}
                              <div className="evidence-text-container" style={{
                                backgroundColor: '#ffffff',
                                padding: '16px',
                                borderRadius: '6px',
                                border: '1px solid #e2e8f0',
                                borderLeft: '4px solid var(--primary-navy)',
                                marginBottom: '10px'
                              }}>
                                <div style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  marginBottom: '10px'
                                }}>
                                  <div style={{
                                    fontSize: '0.75rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                    color: 'var(--primary-navy)',
                                    fontWeight: 700,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px'
                                  }}>
                                    <Shield size={14} />
                                    {citation.clean_text ? 'Official Statutory Text' : 'Retrieved Evidence Text'}
                                  </div>
                                  {citation.ocr_anomaly && (
                                    <button
                                      onClick={(e) => toggleRawOcr(citation.citation_id, e)}
                                      style={{
                                        background: showRawOcr[citation.citation_id] ? '#e2e8f0' : '#f1f5f9',
                                        border: '1px solid #cbd5e1',
                                        color: '#334155',
                                        fontSize: '0.78rem',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                      }}
                                    >
                                      {showRawOcr[citation.citation_id] ? 'Hide Raw OCR Scan' : 'Inspect Raw OCR Scan'}
                                    </button>
                                  )}
                                </div>

                                <div style={{ 
                                  fontSize: '0.92rem', 
                                  color: '#1e293b', 
                                  lineHeight: '1.65',
                                  whiteSpace: 'pre-wrap',
                                  fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
                                }}>
                                  {citation.clean_text || citation.extracted_text || "No text available."}
                                </div>
                              </div>

                              {/* Collapsible Raw OCR View */}
                              {citation.ocr_anomaly && showRawOcr[citation.citation_id] && (
                                <div style={{
                                  backgroundColor: '#f8fafc',
                                  padding: '12px 14px',
                                  borderRadius: '6px',
                                  border: '1px dashed #cbd5e1',
                                  fontSize: '0.82rem',
                                  color: '#475569',
                                  marginTop: '8px'
                                }}>
                                  <div style={{ fontWeight: 600, color: '#64748b', marginBottom: '6px', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                                    Raw Tesseract Scanned Gazette OCR:
                                  </div>
                                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem', color: '#475569', lineHeight: '1.5' }}>
                                    {citation.extracted_text}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
