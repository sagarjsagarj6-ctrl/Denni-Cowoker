import React, { useState, useEffect, useRef } from 'react';
import { 
  FileText, 
  Upload, 
  Search, 
  BookOpen, 
  RefreshCw
} from 'lucide-react';
import { api } from '../api/client';

export default function DocumentPanel() {
  const [documents, setDocuments] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [companyId, setCompanyId] = useState('Apex-Mobility');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const fileInputRef = useRef(null);

  const loadDocuments = async () => {
    setLoading(true);
    await fetchDocuments();
  };

  const fetchDocuments = async () => {
    try {
      const res = await api.getKnowledgeDocuments();
      setDocuments(res.documents || []);
      setTotalChunks(res.total_chunks || 0);
    } catch (err) {
      console.error('Failed to load knowledge documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    setUploading(true);
    try {
      for (const file of files) {
        await api.uploadKnowledgeDoc(file, companyId);
      }
      await loadDocuments();
    } catch (err) {
      alert(`Knowledge document upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const handleSearchKnowledge = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    try {
      const res = await api.searchKnowledge(searchQuery.trim(), companyId);
      setSearchResults(res.results || []);
    } catch (err) {
      alert(`Knowledge search failed: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <div className="documents-container">
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
              Company Document Ingestion for RAG Agents
            </h2>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              Upload internal company policies, engineering requirements, BOMs, and contracts for retrieval-augmented agent reasoning.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              className="icon-btn"
              onClick={loadDocuments}
              title="Refresh document store"
            >
              <RefreshCw size={14} className={loading ? 'spinning' : ''} />
            </button>
          </div>
        </div>

        {/* Company Scope & Dropzone */}
        <div style={{ display: 'flex', gap: 16, alignItems: 'stretch' }}>
          <div style={{ width: '220px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label className="form-label">
              <span>Company Scope ID</span>
            </label>
            <input
              type="text"
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              className="form-input"
              placeholder="e.g. Apex-Mobility"
            />
            <div className="form-hint">
              Used by RAG agent to isolate cross-company evidence scopes.
            </div>
          </div>

          <div 
            className="dropzone-card" 
            style={{ flex: 1 }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              multiple
              accept=".pdf,.docx,.xlsx,.csv,.md,.txt,.json"
              onChange={handleFileUpload}
            />
            <div className="dropzone-icon">
              {uploading ? <RefreshCw size={26} className="spinning" /> : <Upload size={26} />}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
                {uploading ? 'Processing & chunking documents...' : 'Click to Upload or Drag & Drop Documents'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                Supports PDF, Word (.docx), Excel (.xlsx), CSV, Markdown (.md), JSON, TXT
              </div>
            </div>
          </div>
        </div>

        {/* Test RAG Search Tool */}
        <div className="documents-list-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Search size={16} color="var(--accent-cyan)" />
              <span>Test Live RAG Semantic & Text Search</span>
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Top K: 8 Chunks
            </span>
          </div>

          <form onSubmit={handleSearchKnowledge} style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              placeholder="Search company knowledge (e.g. thermal runaway 105C, BOM piece price, supplier lead time)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-input"
              style={{ flex: 1 }}
            />
            <button type="submit" className="send-btn" disabled={searching || !searchQuery.trim()}>
              {searching ? 'Querying...' : 'Query RAG'}
            </button>
          </form>

          {searchResults.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>
                Retrieved {searchResults.length} Grounded Evidence Chunks:
              </div>
              {searchResults.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(15,23,42,0.03)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 10,
                    padding: '10px 14px',
                    fontSize: 12,
                    lineHeight: 1.5,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                      {item.source_name || 'Document Chunk'}
                    </span>
                    <span className="evidence-tag">{item.evidence_id || item.chunk_id}</span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)' }}>{item.text}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Ingested Documents List */}
        <div className="documents-list-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <BookOpen size={16} color="var(--accent-emerald)" />
              <span>Indexed Company Knowledge Base</span>
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 12 }}>
              <span>Total Documents: <strong style={{ color: 'var(--text-primary)' }}>{documents.length}</strong></span>
              <span>Total Chunks: <strong style={{ color: 'var(--accent-cyan)' }}>{totalChunks}</strong></span>
            </div>
          </div>

          {documents.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: 13 }}>
              No company documents ingested yet. Upload files above to add evidence for retrieval.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="doc-table">
                <thead>
                  <tr>
                    <th>Source Document</th>
                    <th>Scope ID</th>
                    <th>Indexed Chunks</th>
                    <th>Content Preview</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <FileText size={14} color="var(--accent-cyan)" />
                          <span>{doc.source_name}</span>
                        </div>
                      </td>
                      <td>
                        <span className="agent-card-role-badge">
                          {doc.company_id || 'Global'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>
                          {doc.chunk_count} chunk(s)
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {doc.preview}...
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
