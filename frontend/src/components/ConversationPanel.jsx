import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Paperclip, 
  Image as ImageIcon, 
  X, 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  FileCheck, 
  RotateCcw
} from 'lucide-react';
import { api } from '../api/client';

export default function ConversationPanel({ 
  messages, 
  setMessages, 
  setActiveRun, 
  onRunStart, 
  isWorkflowLoading, 
  availableCases,
  onOpenWorkflow 
}) {
  const [inputText, setInputText] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const [isConversationLoading, setIsConversationLoading] = useState(false);
  const [resumeContext, setResumeContext] = useState(null);
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWorkflowLoading, isConversationLoading]);

  // Handle file uploads (Images & Documents)
  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    setUploadingFiles(true);
    try {
      for (const file of files) {
        const uploaded = await api.uploadFile(file);
        setAttachments((prev) => [
          ...prev,
          {
            name: uploaded.filename,
            path: uploaded.path,
            size: uploaded.size,
            type: uploaded.content_type,
            preview: uploaded.preview_url,
            isImage: uploaded.content_type?.startsWith('image/'),
          },
        ]);
      }
    } catch (err) {
      alert(`File upload failed: ${err.message}`);
    } finally {
      setUploadingFiles(false);
      event.target.value = '';
    }
  };

  const removeAttachment = (index) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  // Talk through a request first, then start the review once its objective is clear.
  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (
      (!inputText.trim() && attachments.length === 0) ||
      isWorkflowLoading ||
      isConversationLoading
    ) return;

    const userText = inputText.trim() || 'Analyze attached evidence and provide cross-functional recommendation.';
    const filePaths = attachments.map((a) => a.path);

    const userMsg = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: userText,
      attachments: [...attachments],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setAttachments([]);

    try {
      let taskText = userText;
      const shouldStartWorkflowDirectly =
        filePaths.length > 0 || Boolean(resumeContext) || userText.length > 8_000;

      if (!shouldStartWorkflowDirectly) {
        setIsConversationLoading(true);
        const conversationHistory = [
          ...messages
            .filter((message) => ['user', 'assistant'].includes(message.sender) && message.text)
            .slice(-19)
            .map((message) => ({
              role: message.sender,
              content: message.text,
            })),
          { role: 'user', content: userText },
        ];
        const intake = await api.respondToConversation(conversationHistory);

        if (intake.message) {
          setMessages((prev) => [
            ...prev,
            {
              id: `assistant_${Date.now()}`,
              sender: 'assistant',
              text: intake.message,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }

        if (intake.action === 'reply') return;
        taskText = intake.task?.trim() || userText;
      }

      // Signal parent only after the user has provided enough detail to process the task.
      onRunStart(taskText, filePaths);

      const response = resumeContext
        ? await api.resumeRun(resumeContext.runId, {
            resume_token: resumeContext.token,
            new_request: taskText,
            files: filePaths,
          })
        : await api.createRun({
            text: taskText,
            files: filePaths,
            company_id: 'Apex-Mobility',
          });

      const runRecord = response.run;
      const token = response.resume_token;
      setResumeContext(null);

      const agentMsg = {
        id: runRecord.run_id,
        sender: 'agent',
        run: runRecord,
        team: response.team,
        snapshot: response.snapshot,
        resume_token: token,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, agentMsg]);
      setActiveRun({
        run: runRecord,
        team: response.team,
        snapshot: response.snapshot,
        resume_token: token,
      });
    } catch (err) {
      setActiveRun(null);
      const errorMsg = {
        id: `err_${Date.now()}`,
        sender: 'error',
        text: `I couldn't continue: ${err.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsConversationLoading(false);
    }
  };

  // Load preset sample case
  const handleLoadCase = async (caseId) => {
    try {
      const caseData = await api.getCase(caseId);
      setInputText(caseData.prompt);
      // Pre-attach files
      if (caseData.files?.length) {
        setAttachments(
          caseData.files.map((f) => ({
            name: f.name,
            path: f.path,
            size: f.size,
            type: 'text/markdown',
            isImage: false,
          }))
        );
      }
    } catch (err) {
      console.error('Failed to load case:', err);
    }
  };

  const handleResumeClick = (runId, token) => {
    setResumeContext({ runId, token });
    setInputText(`Follow-up inquiry on previous verification gates: `);
  };

  return (
    <div className="chat-container">
      {/* Messages Feed */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', margin: 'auto', maxWidth: '600px', padding: '32px 16px' }}>
            <div style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(6,182,212,0.2))',
              color: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 0 24px var(--accent-glow)'
            }}>
              <Sparkles size={28} />
            </div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
              Dynamic Multi-Agent Case Workspace
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6, marginBottom: 24 }}>
              Tell me what you want to change or ask a question. I’ll clarify any missing details, then send a clear request to the specialist team. You can attach company documents whenever you’re ready.
            </p>

          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message-item ${msg.sender}`}>
            <div className={`avatar-circle ${msg.sender === 'assistant' ? 'agent' : msg.sender}`}>
              {msg.sender === 'user' ? 'U' : <Sparkles size={18} />}
            </div>

            <div className="message-bubble">
              {msg.sender === 'user' && (
                <div className="user-bubble-content">
                  <div>{msg.text}</div>
                  {msg.attachments?.length > 0 && (
                    <div className="user-files-grid">
                      {msg.attachments.map((att, i) => (
                        <div key={i} className="user-file-item">
                          {att.preview ? (
                            <img src={att.preview} alt={att.name} style={{ width: 18, height: 18, borderRadius: 3 }} />
                          ) : (
                            <Paperclip size={12} />
                          )}
                          <span>{att.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'right', marginTop: 4 }}>
                    {msg.timestamp}
                  </div>
                </div>
              )}

              {msg.sender === 'assistant' && (
                <div className="assistant-bubble-content">
                  <div>{msg.text}</div>
                  <div className="assistant-message-time">{msg.timestamp}</div>
                </div>
              )}

              {msg.sender === 'agent' && msg.run && (
                <div className="run-response-card">
                  {/* Decision Banner */}
                  <div className={`decision-banner ${msg.run.decision?.outcome || 'insufficient_evidence'}`}>
                    <div className="decision-title-row">
                      <ShieldAlert size={20} />
                      <span>
                        Outcome:{' '}
                        <strong>
                          {msg.run.decision?.outcome?.replace('_', ' ').toUpperCase() || 'INSUFFICIENT EVIDENCE'}
                        </strong>
                      </span>
                    </div>
                    {msg.run.verification && (
                      <div className="decision-score-badge">
                        Verification Gate Score: {Math.round(msg.run.verification.score * 100)}%
                      </div>
                    )}
                  </div>

                  {/* Rationale */}
                  {msg.run.decision?.rationale && (
                    <div className="card-section">
                      <div className="card-section-title">Master Orchestrator Rationale</div>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        {msg.run.decision.rationale}
                      </p>
                    </div>
                  )}

                  {/* Critical Risks Detected */}
                  {msg.run.decision?.critical_risks?.length > 0 && (
                    <div className="card-section">
                      <div className="card-section-title" style={{ color: 'var(--accent-amber)' }}>
                        <AlertTriangle size={14} /> Contradictions & Critical Risks Surfaced
                      </div>
                      <ul className="risks-list">
                        {msg.run.decision.critical_risks.map((risk, idx) => (
                          <li key={idx} className="risk-item">
                            <AlertTriangle size={14} />
                            <span>{risk}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Conditions & Actionable Tests */}
                  {msg.run.decision?.conditions?.length > 0 && (
                    <div className="card-section">
                      <div className="card-section-title">Mandatory Approval Conditions</div>
                      <ul className="conditions-list">
                        {msg.run.decision.conditions.map((cond, idx) => (
                          <li key={idx} className="condition-item">
                            <CheckCircle2 size={14} color="var(--accent-emerald)" />
                            <span>{cond}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Required Validation Tests */}
                  {msg.run.decision?.required_tests?.length > 0 && (
                    <div className="card-section">
                      <div className="card-section-title">Required Gated Qualification Tests</div>
                      <ul className="conditions-list">
                        {msg.run.decision.required_tests.map((test, idx) => (
                          <li key={idx} className="condition-item">
                            <FileCheck size={14} color="var(--accent-cyan)" />
                            <span>{test}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Evidence Refs */}
                  {msg.run.decision?.evidence_refs?.length > 0 && (
                    <div className="card-section">
                      <div className="card-section-title">Cited Evidence IDs</div>
                      <div className="evidence-tags-row">
                        {msg.run.decision.evidence_refs.map((ref, idx) => (
                          <span key={idx} className="evidence-tag">{ref}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Footer & Resume Token */}
                  <div className="card-footer-bar">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span title="Unique Run ID">Run: {msg.run.run_id?.slice(0, 14)}...</span>
                      <span>Model Calls: {msg.run.model_calls}</span>
                      <span>Tool Calls: {msg.run.tool_calls}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {msg.resume_token && (
                        <button
                          className="tool-action-btn"
                          onClick={() => handleResumeClick(msg.run.run_id, msg.resume_token)}
                          title="Continue investigation from this exact state"
                        >
                          <RotateCcw size={12} /> Follow-up with Resume Token
                        </button>
                      )}
                      <button 
                        className="tool-action-btn"
                        onClick={() => {
                          setActiveRun(msg);
                          onOpenWorkflow();
                        }}
                        style={{ color: 'var(--accent-primary)', borderColor: 'rgba(99,102,241,0.3)' }}
                      >
                        Inspect Live Flow →
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {msg.sender === 'error' && (
                <div style={{
                  padding: '12px 16px',
                  borderRadius: 12,
                  background: 'rgba(244,63,94,0.1)',
                  border: '1px solid rgba(244,63,94,0.3)',
                  color: '#9f1239',
                  fontSize: 13
                }}>
                  {msg.text}
                </div>
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Clean Text & Image Input Bar */}
      <div className="chat-input-wrapper">
        {/* Preset pill bar */}
        <div className="case-presets-bar">
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>Quick Cases:</span>
          {availableCases?.map((c) => (
            <button
              key={c.case_id}
              className="preset-chip"
              onClick={() => handleLoadCase(c.case_id)}
            >
              {c.title} ({c.file_count} files)
            </button>
          ))}
        </div>

        <div className="chat-input-card">
          {/* Attachment Preview Strip */}
          {attachments.length > 0 && (
            <div className="attachments-preview-strip">
              {attachments.map((att, i) => (
                <div key={i} className="attachment-chip">
                  {att.preview ? (
                    <img src={att.preview} alt={att.name} className="attachment-thumb" />
                  ) : (
                    <Paperclip size={14} color="var(--accent-cyan)" />
                  )}
                  <span className="attachment-name">{att.name}</span>
                  <button className="attachment-remove" onClick={() => removeAttachment(i)}>
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Main Input Row */}
          <div className="input-main-row">
            <textarea
              className="chat-textarea"
              placeholder="Tell me what you want to change or ask a question..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              rows={1}
            />
          </div>

          {/* Tools & Submit Row */}
          <div className="input-actions-row">
            <div className="input-left-tools">
              {/* Image Input */}
              <button 
                type="button" 
                className="tool-action-btn"
                onClick={() => imageInputRef.current?.click()}
                title="Attach Image (.png, .jpg, .webp)"
              >
                <ImageIcon size={14} /> Attach Image
              </button>
              <input 
                type="file" 
                ref={imageInputRef} 
                style={{ display: 'none' }} 
                accept="image/*" 
                multiple
                onChange={(e) => handleFileUpload(e, true)}
              />

              {/* Document / Any File Input */}
              <button 
                type="button" 
                className="tool-action-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Attach Documents (.pdf, .docx, .xlsx, .csv, .md, .txt)"
              >
                <Paperclip size={14} /> Attach Documents
              </button>
              <input 
                type="file" 
                ref={fileInputRef} 
                style={{ display: 'none' }} 
                multiple
                onChange={(e) => handleFileUpload(e, false)}
              />

              {uploadingFiles && (
                <span style={{ fontSize: 11, color: 'var(--accent-cyan)' }}>Uploading files...</span>
              )}
            </div>

            <button 
              className="send-btn" 
              onClick={handleSubmit}
              disabled={
                isWorkflowLoading ||
                isConversationLoading ||
                (!inputText.trim() && attachments.length === 0)
              }
            >
              {isWorkflowLoading || isConversationLoading ? (
                <>
                  <div className="status-dot spinning" />
                  <span>{isConversationLoading ? 'Thinking...' : 'Orchestrating...'}</span>
                </>
              ) : (
                <>
                  <span>Send</span>
                  <Send size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
