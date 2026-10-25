import React from 'react';
import { 
  MessageSquare, 
  Users, 
  Settings, 
  FileText, 
  ChevronLeft, 
  ChevronRight
} from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  isCollapsed, 
  setIsCollapsed, 
  serverHealth,
  hasApiKey 
}) {
  const navItems = [
    { id: 'chat', label: 'Conversation', icon: MessageSquare, badge: null },
    { id: 'agents', label: 'Agents Register', icon: Users, badge: '10' },
    { id: 'setup', label: 'Setup & API Keys', icon: Settings, badge: hasApiKey ? 'Active' : 'Missing' },
    { id: 'documents', label: 'Company Documents', icon: FileText, badge: 'RAG' },
  ];

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <a href="#home" className="brand" onClick={(e) => { e.preventDefault(); setActiveTab('chat'); }}>
          <div className="brand-icon">
            <svg viewBox="0 0 36 36" aria-hidden="true" focusable="false">
              <path d="M18 18 9.5 9.5M18 18l8.5-8.5M18 18v9" />
              <circle cx="18" cy="18" r="4.2" />
              <circle cx="9" cy="9" r="2.5" />
              <circle cx="27" cy="9" r="2.5" />
              <circle cx="18" cy="27" r="2.5" />
            </svg>
          </div>
          {!isCollapsed && (
            <div className="brand-info">
              <span className="brand-title">Denni Coworker</span>
              <span className="brand-sub">Dynamic Multi-Agent</span>
            </div>
          )}
        </a>
        <button 
          className="collapse-btn" 
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {!isCollapsed && <div className="nav-label">Workspace Canvas</div>}
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon size={18} className="nav-icon" />
              {!isCollapsed && (
                <>
                  <span className="nav-text">{item.label}</span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                </>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {!isCollapsed && (
          <div className="system-status-chip">
            <span className={`status-dot ${serverHealth ? '' : 'warning'}`} />
            <span>Backend: {serverHealth ? 'FastAPI 0.1.0' : 'Reconnecting...'}</span>
          </div>
        )}
      </div>
    </aside>
  );
}
