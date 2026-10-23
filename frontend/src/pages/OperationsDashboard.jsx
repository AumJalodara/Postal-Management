import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { 
  Users, Truck, MapPin, Clock, History, AlertCircle, RefreshCw, Send,
  MessageSquare, UserCheck, Search, Activity, Package, DollarSign,
  Eye, X, CheckCircle2, ExternalLink, Calendar, ShieldCheck, ArrowRight
} from 'lucide-react';
import { getAgentByPin } from '../data/stateAgents';

export default function OperationsDashboard() {
  const [activeTab, setActiveTab] = useState('fleet'); // 'fleet' or 'citizens'

  // Fleet & Agent State
  const [agents, setAgents] = useState([]);
  const [agentFilter, setAgentFilter] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [agentDetails, setAgentDetails] = useState(null);
  const [pickups, setPickups] = useState([]);
  const [history, setHistory] = useState([]);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loadingPickups, setLoadingPickups] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState(null);

  // Citizen Registry State
  const [citizens, setCitizens] = useState([]);
  const [citizenMetrics, setCitizenMetrics] = useState(null);
  const [loadingCitizens, setLoadingCitizens] = useState(false);
  const [citizenSearch, setCitizenSearch] = useState('');
  const [citizenBookingFilter, setCitizenBookingFilter] = useState('all'); // 'all', 'with_bookings', 'no_bookings'
  const [selectedCitizen, setSelectedCitizen] = useState(null);
  const [citizenParcels, setCitizenParcels] = useState([]);
  const [loadingCitizenParcels, setLoadingCitizenParcels] = useState(false);

  // AI Assistant State
  const [aiQuery, setAiQuery] = useState('');
  const [aiMessages, setAiMessages] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  const aiChatEndRef = useRef(null);

  useEffect(() => {
    fetchAgents();
    fetchPickups();
    fetchHistory();
    fetchCitizens();
  }, []);

  useEffect(() => {
    if (selectedAgentId) {
      fetchAgentDetails(selectedAgentId);
    } else {
      setAgentDetails(null);
    }
  }, [selectedAgentId]);

  useEffect(() => {
    if (aiChatEndRef.current) {
      aiChatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [aiMessages, aiLoading]);

  const fetchAgents = async () => {
    setLoadingAgents(true);
    try {
      const res = await api.get('/operations/agents');
      const loaded = res.data.data || [];
      setAgents(loaded);
      if (loaded.length > 0 && !selectedAgentId) {
        setSelectedAgentId(loaded[0].agent_id);
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to fetch agents');
    } finally {
      setLoadingAgents(false);
    }
  };

  const fetchAgentDetails = async (agentId) => {
    setLoadingDetails(true);
    try {
      const res = await api.get(`/operations/agents/${agentId}`);
      setAgentDetails(res.data.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to fetch agent details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const fetchPickups = async () => {
    setLoadingPickups(true);
    try {
      const res = await api.get('/operations/pickups');
      setPickups(res.data.data || []);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to fetch pickups');
    } finally {
      setLoadingPickups(false);
    }
  };

  const fetchHistory = async (page = 1) => {
    setLoadingHistory(true);
    try {
      const res = await api.get(`/operations/history?page=${page}&page_size=20`);
      if (page === 1) {
        setHistory(res.data.data.items || []);
      } else {
        setHistory(prev => [...prev, ...(res.data.data.items || [])]);
      }
      setHistoryTotal(res.data.data.total_count || 0);
      setHistoryPage(page);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to fetch history');
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchCitizens = async () => {
    setLoadingCitizens(true);
    try {
      const res = await api.get('/operations/citizens');
      const data = res.data?.data;
      if (data) {
        setCitizens(data.citizens || []);
        setCitizenMetrics(data.metrics || null);
      }
    } catch (err) {
      console.warn('Failed to fetch citizens:', err);
    } finally {
      setLoadingCitizens(false);
    }
  };

  const handleViewCitizenParcels = async (cit) => {
    setSelectedCitizen(cit);
    setLoadingCitizenParcels(true);
    try {
      const res = await api.get(`/operations/citizens/${cit.citizen_id}/parcels`);
      setCitizenParcels(res.data?.data || []);
    } catch (err) {
      console.error('Failed to load citizen parcels:', err);
      setCitizenParcels([]);
    } finally {
      setLoadingCitizenParcels(false);
    }
  };

  const askAssistant = async (e) => {
    e.preventDefault();
    if (!aiQuery.trim() || aiLoading) return;

    const userText = aiQuery.trim();
    setAiQuery('');
    setAiMessages(prev => [...prev, { role: 'user', content: userText }]);
    setAiLoading(true);
    setAiError(null);

    try {
      const res = await api.post('/operations/assistant', { query: userText });
      const answer = res.data.data.answer;
      setAiMessages(prev => [...prev, { role: 'assistant', content: answer }]);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'AI request failed.';
      setAiMessages(prev => [...prev, { role: 'error', content: `Error: ${msg}` }]);
    } finally {
      setAiLoading(false);
    }
  };

  const handleRefresh = () => {
    setError(null);
    fetchAgents();
    fetchPickups();
    fetchHistory(1);
    fetchCitizens();
    if (selectedAgentId) fetchAgentDetails(selectedAgentId);
  };

  // Filter citizens based on search term and booking filter
  const filteredCitizens = citizens.filter((cit) => {
    const term = citizenSearch.toLowerCase().trim();
    const matchesSearch =
      !term ||
      (cit.name && cit.name.toLowerCase().includes(term)) ||
      (cit.email && cit.email.toLowerCase().includes(term)) ||
      (cit.phone && cit.phone.includes(term));

    if (!matchesSearch) return false;

    if (citizenBookingFilter === 'with_bookings') {
      return cit.parcels_booked_count > 0 || cit.pickups_requested_count > 0;
    }
    if (citizenBookingFilter === 'no_bookings') {
      return cit.parcels_booked_count === 0 && cit.pickups_requested_count === 0;
    }
    return true;
  });

  return (
    <div className="container" style={{ marginTop: '2rem', maxWidth: '1420px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
        <div>
          <h2>Operations &amp; Admin Portal</h2>
          <p style={{ color: '#666', fontSize: '0.9rem' }}>
            Comprehensive management of delivery agents, citizen bookings, consignments, and operational AI.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-outline" onClick={handleRefresh} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <RefreshCw size={16} /> Refresh Data
          </button>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          borderBottom: '2px solid #e2e8f0',
          marginBottom: '1.8rem',
        }}
      >
        <button
          onClick={() => setActiveTab('fleet')}
          style={{
            padding: '10px 20px',
            fontSize: '0.96rem',
            fontWeight: 700,
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'fleet' ? '3px solid #2563eb' : '3px solid transparent',
            color: activeTab === 'fleet' ? '#1e40af' : '#64748b',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Truck size={18} /> Delivery Operations &amp; Fleet
        </button>

        <button
          onClick={() => setActiveTab('citizens')}
          style={{
            padding: '10px 20px',
            fontSize: '0.96rem',
            fontWeight: 700,
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'citizens' ? '3px solid #2563eb' : '3px solid transparent',
            color: activeTab === 'citizens' ? '#1e40af' : '#64748b',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Users size={18} /> Citizen Registry &amp; Consignments
          {citizenMetrics?.total_registered_citizens > 0 && (
            <span
              style={{
                background: '#dcfce7',
                color: '#166534',
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '0.75rem',
                fontWeight: 700,
              }}
            >
              {citizenMetrics.total_registered_citizens} Registered
            </span>
          )}
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 1: FLEET & DELIVERY OPERATIONS */}
      {/* ======================================================== */}
      {activeTab === 'fleet' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr', gap: '1.5rem' }}>
          {/* LEFT COLUMN: Agents */}
          <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', maxHeight: '820px' }}>
            <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Users size={18} /> Active Agents
              </span>
              <span className="badge" style={{ background: '#dbeafe', color: '#1e40af', fontSize: '0.75rem' }}>
                {agents.length} Registered
              </span>
            </h3>

            {/* Quick Search / State Filter */}
            <div style={{ marginBottom: '0.8rem', position: 'relative' }}>
              <input
                type="text"
                placeholder="🔍 Filter by state, name, or PIN..."
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value)}
                className="form-input"
                style={{ fontSize: '0.82rem', padding: '6px 10px', width: '100%' }}
              />
            </div>
            
            {loadingAgents ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>Loading agents...</div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
                {(() => {
                  const filteredAgents = agents.filter(ag => {
                    if (!agentFilter) return true;
                    const term = agentFilter.toLowerCase().trim();
                    const meta = getAgentByPin(ag.service_area);
                    return (
                      (ag.name && ag.name.toLowerCase().includes(term)) ||
                      (ag.service_area && ag.service_area.includes(term)) ||
                      (meta && meta.state.toLowerCase().includes(term)) ||
                      (meta && meta.hub.toLowerCase().includes(term))
                    );
                  });

                  if (filteredAgents.length === 0) {
                    return (
                      <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                        No agents match "{agentFilter}"
                      </div>
                    );
                  }

                  return (
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                      {filteredAgents.map(ag => {
                        const meta = getAgentByPin(ag.service_area);
                        const stateLabel = meta ? meta.state : null;
                        const cityLabel = meta ? meta.hub : ag.service_area;
                        const isSelected = selectedAgentId === ag.agent_id;

                        return (
                          <li
                            key={ag.agent_id}
                            onClick={() => setSelectedAgentId(ag.agent_id)}
                            style={{
                              padding: '0.75rem',
                              borderBottom: '1px solid #f1f5f9',
                              cursor: 'pointer',
                              background: isSelected ? '#eff6ff' : 'transparent',
                              borderRadius: '6px',
                              marginBottom: '4px',
                              borderLeft: isSelected ? '4px solid #3b82f6' : '4px solid transparent',
                              transition: 'all 0.1s ease'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <strong style={{ fontSize: '0.9rem', color: isSelected ? '#1e40af' : '#0f172a' }}>
                                {ag.name}
                              </strong>
                              <span style={{ fontSize: '0.75rem', color: ag.is_available ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
                                {ag.is_available ? '● Available' : '○ Busy'}
                              </span>
                            </div>

                            {stateLabel && (
                              <div style={{ fontSize: '0.75rem', color: '#0369a1', fontWeight: 600, marginTop: '2px' }}>
                                🏛️ {stateLabel}
                              </div>
                            )}

                            <div style={{ fontSize: '0.78rem', color: '#475569', display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
                              <span>📍 {cityLabel} ({ag.service_area})</span>
                              {ag.phone && <span style={{ color: '#64748b' }}>📞 {ag.phone}</span>}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  );
                })()}
              </div>
            )}
          </div>

          {/* MIDDLE COLUMN: Agent Detail / Route / ETA & Pickups */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Agent Route & ETA */}
            <div className="card" style={{ padding: '1.5rem' }}>
              {selectedAgentId ? (
                loadingDetails ? (
                  <div style={{ textAlign: 'center', padding: '2rem' }}>Loading details...</div>
                ) : agentDetails ? (
                  <div>
                    <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <MapPin size={18} /> Route &amp; ETA for Agent #{selectedAgentId}
                    </h3>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                      <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#0f172a' }}>
                          <Truck size={15} /> Route Details
                        </h4>
                        <p style={{ margin: '0 0 0.4rem 0', fontSize: '0.9rem' }}><strong>Distance:</strong> {agentDetails.route.total_distance_km?.toFixed(2) ?? '0.00'} km</p>
                        <p style={{ margin: '0 0 0.4rem 0', fontSize: '0.9rem' }}><strong>Stops:</strong> {agentDetails.route.stops?.length ?? 0}</p>
                        <p style={{ margin: 0, fontSize: '0.9rem' }}><strong>Unresolved:</strong> {Array.isArray(agentDetails.route.unresolved_stops) ? agentDetails.route.unresolved_stops.length : (agentDetails.route.unresolved_stops ?? 0)}</p>
                      </div>
                      <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#0f172a' }}>
                          <Clock size={15} /> ETA Estimation
                        </h4>
                        <p style={{ margin: '0 0 0.4rem 0', fontSize: '0.9rem' }}><strong>Total ETA:</strong> {Math.round(agentDetails.eta.total_eta_minutes ?? 0)} min</p>
                        <p style={{ margin: '0 0 0.4rem 0', fontSize: '0.9rem' }}><strong>Travel Time:</strong> {Math.round(agentDetails.eta.travel_time_minutes ?? agentDetails.eta.breakdown?.travel_time_minutes ?? 0)} min</p>
                        <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>Assumptions: {agentDetails.eta.average_speed_kmph ?? agentDetails.eta.assumptions?.average_speed_kmph ?? 30} km/h, {agentDetails.eta.assumptions?.service_time_minutes_per_stop ?? 5} min/stop</p>
                      </div>
                    </div>

                    <h4 style={{ marginBottom: '0.5rem' }}>Ordered Stops</h4>
                    {agentDetails.route.stops && agentDetails.route.stops.length > 0 ? (
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {agentDetails.route.stops.map((stop, index) => (
                          <li key={index} style={{ padding: '0.75rem', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span style={{ background: '#3b82f6', color: '#fff', borderRadius: '50%', width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', fontWeight: 'bold' }}>
                              {index + 1}
                            </span>
                            <div>
                              <strong>{stop.stop_type || stop.type || 'Stop'} #{stop.pickup_id || stop.id || stop.stop_id}</strong>
                              <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{stop.address ? `${stop.address}, ` : ''}PIN {stop.pin}</div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ fontSize: '0.9rem', color: '#64748b' }}>No stops assigned to this agent.</p>
                    )}
                  </div>
                ) : (
                  <p>Failed to load agent details.</p>
                )
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                  <Search size={48} style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p>Select an agent from the list to view route and ETA</p>
                </div>
              )}
            </div>

            {/* Active Pickups */}
            <div className="card" style={{ padding: '1.5rem', flex: 1, overflowY: 'auto' }}>
              <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Package size={18} /> Active Pickups
              </h3>
              {loadingPickups ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>Loading pickups...</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left' }}>
                      <th style={{ padding: '0.5rem' }}>ID</th>
                      <th style={{ padding: '0.5rem' }}>PIN</th>
                      <th style={{ padding: '0.5rem' }}>Status</th>
                      <th style={{ padding: '0.5rem' }}>Agent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pickups.slice(0, 10).map((p, idx) => (
                      <tr key={p.id || p.pickup_id || idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.9rem' }}>#{p.id || p.pickup_id}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.9rem' }}>{p.pickup_pin || p.pin}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.9rem' }}>
                          <span className={`badge ${p.status === 'PENDING' ? 'badge-warning' : p.status === 'COMPLETED' ? 'badge-success' : 'badge-primary'}`}>
                            {p.status}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.9rem' }}>{p.assigned_agent_id || p.agent_id ? `#${p.assigned_agent_id || p.agent_id}` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: History & AI */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Operations AI */}
            <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', height: '400px' }}>
              <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#10b981' }}>
                <MessageSquare size={18} /> Operations AI
              </h3>
              
              <div style={{ flex: 1, overflowY: 'auto', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {aiMessages.length === 0 ? (
                  <p style={{ textAlign: 'center', color: '#94a3b8', marginTop: 'auto', marginBottom: 'auto' }}>
                    Ask me about workloads, ETA, citizen bookings, or recent history.
                  </p>
                ) : (
                  aiMessages.map((msg, idx) => (
                    <div key={idx} style={{ 
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      background: msg.role === 'user' ? '#3b82f6' : msg.role === 'error' ? '#fee2e2' : '#f1f5f9',
                      color: msg.role === 'user' ? '#fff' : msg.role === 'error' ? '#ef4444' : '#0f172a',
                      padding: '0.75rem 1rem',
                      borderRadius: '12px',
                      maxWidth: '85%',
                      fontSize: '0.9rem',
                      lineHeight: '1.4'
                    }}>
                      {msg.content}
                    </div>
                  ))
                )}
                {aiLoading && (
                  <div style={{ alignSelf: 'flex-start', background: '#f1f5f9', padding: '0.75rem 1rem', borderRadius: '12px', fontSize: '0.9rem' }}>
                    Thinking...
                  </div>
                )}
                <div ref={aiChatEndRef} />
              </div>

              <form onSubmit={askAssistant} style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ask Operations Assistant..."
                  value={aiQuery}
                  onChange={e => setAiQuery(e.target.value)}
                  disabled={aiLoading}
                  style={{ flex: 1 }}
                />
                <button type="submit" className="btn btn-primary" disabled={aiLoading || !aiQuery.trim()} style={{ padding: '0 0.75rem' }}>
                  <Send size={16} />
                </button>
              </form>
            </div>

            {/* Operational History */}
            <div className="card" style={{ padding: '1.5rem', flex: 1, overflowY: 'auto' }}>
              <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <History size={18} /> Event History
              </h3>
              
              {loadingHistory && history.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>Loading history...</div>
              ) : (
                <>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {history.map(item => (
                      <div key={item.id} style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '6px', borderLeft: '3px solid #3b82f6' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                          <strong style={{ fontSize: '0.85rem', color: '#0f172a' }}>{item.event_type}</strong>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#475569', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span>{item.entity_type} #{item.entity_id}</span>
                          {item.agent_id && <span>• Agent #{item.agent_id}</span>}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem', fontStyle: 'italic' }}>
                          {item.description}
                        </div>
                      </div>
                    ))}
                  </div>
                  {history.length < historyTotal && (
                    <button 
                      className="btn btn-outline" 
                      style={{ width: '100%', marginTop: '1rem', fontSize: '0.85rem' }}
                      onClick={() => fetchHistory(historyPage + 1)}
                      disabled={loadingHistory}
                    >
                      {loadingHistory ? 'Loading...' : 'Load More'}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 2: CITIZEN REGISTRY & CONSIGNMENTS */}
      {/* ======================================================== */}
      {activeTab === 'citizens' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* KPI Metrics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.2rem' }}>
            <div className="card" style={{ padding: '1.2rem', display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '4px solid #2563eb' }}>
              <div style={{ background: '#eff6ff', padding: '12px', borderRadius: '10px', color: '#2563eb' }}>
                <Users size={24} />
              </div>
              <div>
                <span style={{ fontSize: '0.82rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                  Registered Citizens
                </span>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '1.6rem', color: '#0f172a' }}>
                  {citizenMetrics?.total_registered_citizens ?? citizens.length}
                </h3>
              </div>
            </div>

            <div className="card" style={{ padding: '1.2rem', display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '4px solid #10b981' }}>
              <div style={{ background: '#f0fdf4', padding: '12px', borderRadius: '10px', color: '#10b981' }}>
                <UserCheck size={24} />
              </div>
              <div>
                <span style={{ fontSize: '0.82rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                  Active Bookers
                </span>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '1.6rem', color: '#0f172a' }}>
                  {citizenMetrics?.citizens_with_bookings ?? 0}
                  <span style={{ fontSize: '0.8rem', color: '#16a34a', marginLeft: '6px', fontWeight: 500 }}>
                    ({citizenMetrics?.total_registered_citizens ? Math.round((citizenMetrics.citizens_with_bookings / citizenMetrics.total_registered_citizens) * 100) : 0}%)
                  </span>
                </h3>
              </div>
            </div>

            <div className="card" style={{ padding: '1.2rem', display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '4px solid #f59e0b' }}>
              <div style={{ background: '#fffbeb', padding: '12px', borderRadius: '10px', color: '#d97706' }}>
                <Package size={24} />
              </div>
              <div>
                <span style={{ fontSize: '0.82rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                  Total Parcels Booked
                </span>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '1.6rem', color: '#0f172a' }}>
                  {citizenMetrics?.total_parcels_booked ?? 0}
                  <span style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '6px', fontWeight: 500 }}>
                    ({citizenMetrics?.average_parcels_per_citizen ?? 0} avg/citizen)
                  </span>
                </h3>
              </div>
            </div>

            <div className="card" style={{ padding: '1.2rem', display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '4px solid #8b5cf6' }}>
              <div style={{ background: '#f5f3ff', padding: '12px', borderRadius: '10px', color: '#8b5cf6' }}>
                <DollarSign size={24} />
              </div>
              <div>
                <span style={{ fontSize: '0.82rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                  Total Booking Tariff
                </span>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '1.6rem', color: '#0f172a' }}>
                  ₹{(citizenMetrics?.total_revenue ?? 0).toFixed(2)}
                </h3>
              </div>
            </div>
          </div>

          {/* Citizen Search & Filter Bar */}
          <div className="card" style={{ padding: '1.2rem' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '280px' }}>
                <input
                  type="text"
                  placeholder="🔍 Search citizen by name, email, or mobile..."
                  value={citizenSearch}
                  onChange={(e) => setCitizenSearch(e.target.value)}
                  className="form-input"
                  style={{ width: '100%', fontSize: '0.9rem', padding: '8px 12px' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label style={{ fontSize: '0.85rem', color: '#475569', fontWeight: 600 }}>
                  Filter Activity:
                </label>
                <select
                  value={citizenBookingFilter}
                  onChange={(e) => setCitizenBookingFilter(e.target.value)}
                  className="form-select"
                  style={{ padding: '7px 12px', fontSize: '0.85rem' }}
                >
                  <option value="all">All Registered Citizens ({citizens.length})</option>
                  <option value="with_bookings">With Bookings Only ({citizens.filter(c => c.parcels_booked_count > 0 || c.pickups_requested_count > 0).length})</option>
                  <option value="no_bookings">No Bookings Yet ({citizens.filter(c => c.parcels_booked_count === 0 && c.pickups_requested_count === 0).length})</option>
                </select>
              </div>
            </div>

            {/* Citizens Table */}
            {loadingCitizens ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                Loading Citizen Registry from Database...
              </div>
            ) : filteredCitizens.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                <Users size={40} style={{ margin: '0 auto 0.8rem auto', opacity: 0.4 }} />
                <p>No citizens match the selected filter criteria.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0', background: '#f8fafc', fontSize: '0.82rem', color: '#475569' }}>
                      <th style={{ padding: '12px 14px' }}>CITIZEN</th>
                      <th style={{ padding: '12px 14px' }}>REGISTERED ON</th>
                      <th style={{ padding: '12px 14px' }}>PARCELS BOOKED</th>
                      <th style={{ padding: '12px 14px' }}>ACTIVE / DELIVERED</th>
                      <th style={{ padding: '12px 14px' }}>PICKUPS</th>
                      <th style={{ padding: '12px 14px' }}>TOTAL SPENT</th>
                      <th style={{ padding: '12px 14px' }}>STATUS</th>
                      <th style={{ padding: '12px 14px', textAlign: 'center' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCitizens.map((cit) => (
                      <tr
                        key={cit.citizen_id}
                        style={{
                          borderBottom: '1px solid #f1f5f9',
                          transition: 'background 0.1s ease',
                        }}
                      >
                        <td style={{ padding: '12px 14px' }}>
                          <div style={{ fontWeight: 600, color: '#0f172a' }}>{cit.name}</div>
                          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{cit.email}</div>
                          <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>📞 {cit.phone}</div>
                        </td>
                        <td style={{ padding: '12px 14px', fontSize: '0.85rem', color: '#475569' }}>
                          {cit.registered_at ? new Date(cit.registered_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              padding: '4px 10px',
                              borderRadius: '12px',
                              fontSize: '0.85rem',
                              fontWeight: 700,
                              background: cit.parcels_booked_count > 0 ? '#dbeafe' : '#f1f5f9',
                              color: cit.parcels_booked_count > 0 ? '#1d4ed8' : '#64748b',
                            }}
                          >
                            📦 {cit.parcels_booked_count}
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', fontSize: '0.85rem' }}>
                          <span style={{ color: '#0284c7', fontWeight: 600 }}>{cit.active_parcels_count} active</span>
                          {' / '}
                          <span style={{ color: '#16a34a', fontWeight: 600 }}>{cit.delivered_parcels_count} delivered</span>
                        </td>
                        <td style={{ padding: '12px 14px', fontSize: '0.85rem', color: '#475569' }}>
                          {cit.pickups_requested_count > 0 ? `🚚 ${cit.pickups_requested_count}` : '-'}
                        </td>
                        <td style={{ padding: '12px 14px', fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                          ₹{cit.total_spent.toFixed(2)}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span
                            style={{
                              padding: '3px 8px',
                              borderRadius: '10px',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              background: cit.is_active ? '#dcfce7' : '#fee2e2',
                              color: cit.is_active ? '#15803d' : '#b91c1c',
                            }}
                          >
                            {cit.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleViewCitizenParcels(cit)}
                            className="btn btn-outline btn-sm"
                            style={{
                              fontSize: '0.78rem',
                              padding: '5px 10px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Eye size={13} /> View Bookings
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Citizen Consignment Modal / Drilldown */}
          {selectedCitizen && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(15, 23, 42, 0.6)',
                zIndex: 1000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
              }}
              onClick={() => setSelectedCitizen(null)}
            >
              <div
                style={{
                  background: '#ffffff',
                  borderRadius: '12px',
                  width: '100%',
                  maxWidth: '860px',
                  maxHeight: '90vh',
                  overflowY: 'auto',
                  padding: '24px',
                  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e2e8f0', paddingBottom: '16px', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#0f172a' }}>
                      Consignments for {selectedCitizen.name}
                    </h3>
                    <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                      {selectedCitizen.email} • {selectedCitizen.phone} • Total Spent: ₹{selectedCitizen.total_spent.toFixed(2)}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedCitizen(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
                  >
                    <X size={20} />
                  </button>
                </div>

                {loadingCitizenParcels ? (
                  <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                    Loading parcels for {selectedCitizen.name}...
                  </div>
                ) : citizenParcels.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                    <Package size={40} style={{ margin: '0 auto 0.8rem auto', opacity: 0.3 }} />
                    <p>No parcels have been booked by this citizen yet.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {citizenParcels.map((parcel) => (
                      <div
                        key={parcel.id}
                        style={{
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '8px',
                          padding: '14px 18px',
                          display: 'flex',
                          flexWrap: 'wrap',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: '12px',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <span style={{ fontFamily: 'monospace', fontWeight: 800, fontSize: '1rem', color: '#1d4ed8' }}>
                              {parcel.tracking_id}
                            </span>
                            <span className={`badge ${parcel.status === 'DELIVERED' ? 'badge-success' : parcel.status === 'BOOKED' ? 'badge-primary' : 'badge-warning'}`} style={{ fontSize: '0.72rem' }}>
                              {parcel.status}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.85rem', color: '#334155' }}>
                            <strong>To:</strong> {parcel.receiver_name} ({parcel.destination_city}, {parcel.destination_state} - {parcel.destination_pin})
                          </div>
                          <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                            {parcel.weight} kg • {parcel.parcel_type} • {parcel.priority} • Booked on {new Date(parcel.created_at).toLocaleDateString()}
                          </div>
                        </div>

                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#d97706' }}>
                            ₹{parcel.price.toFixed(2)}
                          </div>
                          <a
                            href={`/track/${parcel.tracking_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-outline btn-sm"
                            style={{ fontSize: '0.75rem', padding: '4px 8px', marginTop: '6px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          >
                            <ExternalLink size={12} /> Track Parcel
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
