import React, { useState, useEffect } from 'react';
import { 
  Search, 
  ShieldCheck, 
  Cpu, 
  Wrench, 
  Sparkles, 
  BookOpen, 
  Check
} from 'lucide-react';
import { api } from '../api/client';

export default function AgentsRegisterPanel() {
  const [agents, setAgents] = useState([]);
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAgents() {
      try {
        const res = await api.getAgentsRegistry();
        setAgents(res.agents || []);
      } catch (err) {
        console.error('Failed to load agents:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAgents();
  }, []);

  const filteredAgents = agents.filter((agent) => {
    const matchesFilter = filterType === 'all' || agent.type === filterType;
    const matchesSearch = 
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.role.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Header and Controls */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Agents Register & Capability Catalog
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Registered autonomous roles ready for dynamic team orchestration and capability discovery.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Search */}
            <div style={{ position: 'relative', width: '220px' }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search agents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '30px', fontSize: '12px', height: '34px' }}
              />
            </div>

            {/* Filter Tabs */}
            <div style={{ display: 'flex', background: 'rgba(15,23,42,0.04)', padding: 3, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              {['all', 'coordinator', 'retriever', 'specialist', 'evaluator'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilterType(tab)}
                  style={{
                    background: filterType === tab ? 'var(--accent-primary)' : 'transparent',
                    color: filterType === tab ? '#fff' : 'var(--text-secondary)',
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: '11px',
                    fontWeight: 600,
                    textTransform: 'capitalize',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Agents Grid */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
            Loading agents registry...
          </div>
        ) : (
          <div className="agents-grid" style={{ padding: 0 }}>
            {filteredAgents.map((agent) => (
              <div key={agent.agent_id} className="agent-register-card">
                <div className="agent-card-top">
                  <div className="agent-card-info">
                    <div className={`agent-card-avatar ${agent.type}`}>
                      {agent.type === 'coordinator' && <Sparkles size={22} />}
                      {agent.type === 'retriever' && <BookOpen size={22} />}
                      {agent.type === 'specialist' && <Cpu size={22} />}
                      {agent.type === 'evaluator' && <ShieldCheck size={22} />}
                    </div>
                    <div>
                      <div className="agent-card-name">{agent.name}</div>
                      <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                        <span className="agent-card-role-badge">{agent.type}</span>
                        <span className="agent-card-role-badge" style={{ color: 'var(--accent-cyan)' }}>
                          {agent.role}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="agent-card-desc">{agent.description}</div>

                {/* Capabilities */}
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                    Capabilities & Signals
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {agent.capabilities?.map((cap, i) => (
                      <span
                        key={i}
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: 6,
                          background: 'rgba(99,102,241,0.08)',
                          border: '1px solid rgba(99,102,241,0.2)',
                          color: '#3730a3',
                        }}
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Assigned Tools */}
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                    Scoped Tools
                  </div>
                  <div className="agent-card-tools">
                    {agent.tools?.map((tool, i) => (
                      <span key={i} className="tool-chip">
                        <Wrench size={10} /> {tool}
                      </span>
                    ))}
                  </div>
                </div>

                {/* System Prompt & Model */}
                <div
                  style={{
                    background: 'var(--bg-secondary)',
                    padding: '8px 10px',
                    borderRadius: 8,
                    border: '1px solid rgba(15,23,42,0.04)',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span>Model: <strong style={{ color: 'var(--text-secondary)' }}>{agent.model}</strong></span>
                    <span style={{ color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Check size={10} /> Ready
                    </span>
                  </div>
                  <div style={{ fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    "{agent.system_instruction}"
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
