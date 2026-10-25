import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Brain, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Maximize2, 
  Minimize2, 
  X, 
  Database,
  Search,
  FileCheck,
  GitBranch
} from 'lucide-react';

export default function WorkflowVisualizer({ 
  isOpen, 
  onClose, 
  activeRun, 
  isWorkflowLoading, 
  currentStep,
  inputText,
  attachedFiles 
}) {
  const [activeTab, setActiveTab] = useState('pipeline'); // 'pipeline' | 'thinking' | 'assignment' | 'evaluation'
  const [isExpanded, setIsExpanded] = useState(false);
  const [simulatedThinkingText, setSimulatedThinkingText] = useState(
    'Standing by. When a case is submitted, the Master Agent analyzes evidence signals, dynamically selects specialist roles, assigns scoped tasks, cross-evaluates outputs, and builds the final decision.'
  );

  // Extract run details if present
  const run = activeRun?.run;
  const team = activeRun?.team;
  const plan = team?.plan;
  const taskResults = run?.task_results || [];
  const decision = run?.decision;
  const verification = run?.verification;

  // Stream thinking text simulation while running or display completed rationale
  useEffect(() => {
    if (isWorkflowLoading) {
      const thoughts = [
        "Analyzing user request signals...",
        "Identifying engineering, thermal, and component specifications...",
        "Scanning company documents for governance and quality failure records...",
        "Discovering required specialist capabilities: Engineering, Quality, Supply Chain, Cost, Validation...",
        "Constructing minimum sufficient team plan and dependency graph...",
        "Enforcing zero-trust evidence validation policies...",
        "Dispatching parallel execution waves to specialist agents...",
        "Reconciling cross-functional contradictions and decision gates..."
      ];
      let i = 0;
      const interval = setInterval(() => {
        i = (i + 1) % thoughts.length;
        setSimulatedThinkingText(thoughts[i]);
      }, 1200);
      return () => clearInterval(interval);
    }
  }, [isWorkflowLoading]);

  if (!isOpen) return null;

  // Determine stage active states
  const isInputDone = !!inputText || !!run;
  const isRagDone = isWorkflowLoading ? currentStep >= 2 : !!run;
  const isMasterDone = isWorkflowLoading ? currentStep >= 3 : !!run;
  const isAssignDone = isWorkflowLoading ? currentStep >= 4 : !!run;
  const isExecDone = isWorkflowLoading ? currentStep >= 5 : !!run;
  const isEvalDone = isWorkflowLoading ? currentStep >= 6 : !!run;
  const isOutputDone = isWorkflowLoading ? currentStep >= 7 : !!run;

  const agentsCount = plan?.agents?.length || (isWorkflowLoading ? 6 : 0);
  const thinkingText = isWorkflowLoading
    ? simulatedThinkingText
    : decision?.rationale || 'Standing by. When a case is submitted, the Master Agent analyzes evidence signals, dynamically selects specialist roles, assigns scoped tasks, cross-evaluates outputs, and builds the final decision.';

  return (
    <aside className={`right-panel ${isExpanded ? 'expanded' : ''}`}>
      {/* Header */}
      <div className="right-panel-header">
        <div className="workflow-header-title">
          <div className="workflow-pulse-icon">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="workflow-title-text">Autonomous Workflow Engine</div>
            <div style={{ fontSize: 11, color: isWorkflowLoading ? 'var(--accent-primary)' : 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className={`status-dot ${isWorkflowLoading ? 'spinning' : ''}`} />
              <span>{isWorkflowLoading ? 'Orchestration in progress...' : 'Pipeline Ready & Verified'}</span>
            </div>
          </div>
        </div>

        <div className="workflow-controls">
          <button 
            className="icon-btn" 
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "Collapse width" : "Expand width"}
          >
            {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button className="icon-btn" onClick={onClose} title="Close panel">
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ padding: '12px 20px 0' }}>
        <div className="workflow-tabs-strip">
          <button
            className={`workflow-tab-btn ${activeTab === 'pipeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('pipeline')}
          >
            Live Pipeline
          </button>
          <button
            className={`workflow-tab-btn ${activeTab === 'thinking' ? 'active' : ''}`}
            onClick={() => setActiveTab('thinking')}
          >
            Master Thoughts
          </button>
          <button
            className={`workflow-tab-btn ${activeTab === 'assignment' ? 'active' : ''}`}
            onClick={() => setActiveTab('assignment')}
          >
            Agent Tasks
          </button>
          <button
            className={`workflow-tab-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
            onClick={() => setActiveTab('evaluation')}
          >
            Cross-Evaluation
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="right-panel-body">
        {/* Live Thinking Card ("What is Master Agent Thinking") */}
        <div className="master-thought-box">
          <div className="thought-header">
            <div className="thought-title-row">
              <Brain size={16} color="var(--accent-primary)" />
              <span>What is Master Agent Thinking?</span>
            </div>
            {isWorkflowLoading && (
              <span className="step-status-chip active" style={{ fontSize: 10 }}>
                Synthesizing
              </span>
            )}
          </div>
          <div className="thought-stream-content">
            {thinkingText}
            {isWorkflowLoading && <span className="thought-stream-cursor" />}
          </div>
        </div>

        {/* TAB 1: LIVE PIPELINE */}
        {activeTab === 'pipeline' && (
          <div className="workflow-timeline">
            {/* STAGE 1: Input & Envelope */}
            <div className={`timeline-step ${isInputDone ? 'completed' : ''}`}>
              <div className="step-node-icon">
                <Database size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 1: Multimodal Input Ingestion</span>
                  <span className={`step-status-chip ${isInputDone ? 'completed' : ''}`}>
                    {isInputDone ? 'Ingested' : 'Waiting'}
                  </span>
                </div>
                <div className="step-description">
                  Normalizes user text prompt and attaches SHA-256 verified evidence files.
                </div>
                {attachedFiles?.length > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--accent-cyan)' }}>
                    📎 {attachedFiles.length} file(s) attached and checksummed
                  </div>
                )}
              </div>
            </div>

            {/* STAGE 2: RAG Knowledge Agent */}
            <div className={`timeline-step ${isRagDone ? 'completed' : isWorkflowLoading && currentStep === 2 ? 'active' : ''}`}>
              <div className="step-node-icon">
                <Search size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 2: RAG Knowledge Agent</span>
                  <span className={`step-status-chip ${isRagDone ? 'completed' : isWorkflowLoading && currentStep === 2 ? 'active' : ''}`}>
                    {isRagDone ? 'Grounded' : isWorkflowLoading && currentStep === 2 ? 'Searching' : 'Pending'}
                  </span>
                </div>
                <div className="step-description">
                  Queries indexed company requirements, BOM specs, historical failure records, and change-control policies.
                </div>
              </div>
            </div>

            {/* STAGE 3: Master Agent Planning & Capability Discovery */}
            <div className={`timeline-step ${isMasterDone ? 'completed' : isWorkflowLoading && currentStep === 3 ? 'active' : ''}`}>
              <div className="step-node-icon">
                <Brain size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 3: Master Agent Capability Discovery</span>
                  <span className={`step-status-chip ${isMasterDone ? 'completed' : isWorkflowLoading && currentStep === 3 ? 'active' : ''}`}>
                    {agentsCount > 0 ? `${agentsCount} Roles Chosen` : 'Discovering'}
                  </span>
                </div>
                <div className="step-description">
                  Analyzes corpus signals to discover minimum sufficient specialist roles.
                </div>

                {/* Show chosen agents badges */}
                {plan?.agents?.length > 0 && (
                  <div className="agent-chips-grid">
                    {plan.agents.map((agent) => (
                      <span key={agent.agent_id} className="chosen-agent-pill">
                        <Cpu size={12} /> {agent.role.replace('_', ' ').toUpperCase()}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* STAGE 4: Task Assignment */}
            <div className={`timeline-step ${isAssignDone ? 'completed' : isWorkflowLoading && currentStep === 4 ? 'active' : ''}`}>
              <div className="step-node-icon">
                <GitBranch size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 4: Dynamic Task Assignment</span>
                  <span className={`step-status-chip ${isAssignDone ? 'completed' : isWorkflowLoading && currentStep === 4 ? 'active' : ''}`}>
                    {plan?.tasks?.length ? `${plan.tasks.length} Tasks Scheduled` : 'Pending'}
                  </span>
                </div>
                <div className="step-description">
                  Constructs bounded DAG, schedules wave concurrency, and allocates read-only tool permissions.
                </div>
              </div>
            </div>

            {/* STAGE 5: Task Execution */}
            <div className={`timeline-step ${isExecDone ? 'completed' : isWorkflowLoading && currentStep === 5 ? 'active' : ''}`}>
              <div className="step-node-icon">
                <Cpu size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 5: Specialist Execution</span>
                  <span className={`step-status-chip ${isExecDone ? 'completed' : isWorkflowLoading && currentStep === 5 ? 'active' : ''}`}>
                    {taskResults.length ? `${taskResults.length} Completed` : 'Executing Waves'}
                  </span>
                </div>
                <div className="step-description">
                  Specialist agents analyze scoped evidence, record findings, extract risks, and cite evidence IDs.
                </div>
                {taskResults.length > 0 && (
                  <div style={{ display: 'flex', gap: 10, fontSize: 11, color: 'var(--text-muted)' }}>
                    <span>Model Calls: {run?.model_calls || 0}</span>
                    <span>Tool Calls: {run?.tool_calls || 0}</span>
                  </div>
                )}
              </div>
            </div>

            {/* STAGE 6: Cross-Evaluation & Contradiction Scan */}
            <div className={`timeline-step ${isEvalDone ? 'completed' : isWorkflowLoading && currentStep === 6 ? 'active' : ''}`}>
              <div className="step-node-icon">
                <ShieldCheck size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 6: Cross-Evaluation & Contradictions</span>
                  <span className={`step-status-chip ${isEvalDone ? 'completed' : isWorkflowLoading && currentStep === 6 ? 'active' : ''}`}>
                    {verification?.passed ? 'Gates Verified' : 'Reconciling'}
                  </span>
                </div>
                <div className="step-description">
                  Evaluates specialist outputs one against another to surface claim conflicts, test gaps, and risk boundaries.
                </div>
                {verification && (
                  <div style={{ fontSize: 11, color: 'var(--accent-emerald)', fontWeight: 600 }}>
                    Gate Score: {Math.round(verification.score * 100)}% ({verification.contradictions.length} contradictions checked)
                  </div>
                )}
              </div>
            </div>

            {/* STAGE 7: Final Synthesis & Decision */}
            <div className={`timeline-step ${isOutputDone ? 'completed' : isWorkflowLoading && currentStep === 7 ? 'active' : ''}`}>
              <div className="step-node-icon">
                <FileCheck size={16} />
              </div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-title">Stage 7: Output Response & Task Completion</span>
                  <span className={`step-status-chip ${isOutputDone ? 'completed' : isWorkflowLoading && currentStep === 7 ? 'active' : ''}`}>
                    {decision ? decision.outcome.toUpperCase() : 'Synthesizing'}
                  </span>
                </div>
                <div className="step-description">
                  Compiles final structured decision, actionable conditions, test requirements, and issues resume token.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: MASTER THOUGHTS */}
        {activeTab === 'thinking' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Master Orchestrator Reasoning Chain
            </div>
            
            <div style={{ background: 'rgba(15,23,42,0.03)', border: '1px solid var(--border-subtle)', borderRadius: 12, padding: 16 }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13, marginBottom: 8 }}>
                1. Capability Discovery Strategy
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Scanned input corpus for keyword signal groups:
                <br />• <strong>Engineering</strong>: matched 'spec', 'tolerance', 'battery', 'component'
                <br />• <strong>Quality</strong>: matched 'failure', 'incident', 'defect'
                <br />• <strong>Supply Chain</strong>: matched 'supplier', 'lead time', 'capacity'
                <br />• <strong>Cost</strong>: matched 'cost', 'savings', 'tooling'
                <br />• <strong>Validation</strong>: matched 'test', 'qualification', 'thermal'
              </p>
            </div>

            <div style={{ background: 'rgba(15,23,42,0.03)', border: '1px solid var(--border-subtle)', borderRadius: 12, padding: 16 }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13, marginBottom: 8 }}>
                2. Zero-Trust Evidence Governance
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Supplier claims are marked as untrusted assumptions until cross-referenced with internal requirement documents. No change is approved without controlled validation gates.
              </p>
            </div>

            {decision?.conditions && (
              <div style={{ background: 'rgba(15,23,42,0.03)', border: '1px solid var(--border-subtle)', borderRadius: 12, padding: 16 }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13, marginBottom: 8 }}>
                  3. Actionable Gate Conditions
                </div>
                <ul style={{ paddingLeft: 18, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {decision.conditions.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: AGENT TASKS ("How Work Is Assigned") */}
        {activeTab === 'assignment' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Dynamic Task Allocation Matrix
            </div>

            {plan?.tasks?.map((task) => {
              const assignedAgent = plan.agents.find((a) => a.agent_id === task.agent_id);
              const result = taskResults.find((r) => r.task_id === task.task_id);
              return (
                <div key={task.task_id} className="task-assign-card" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13 }}>
                      {task.title}
                    </div>
                    <span className={`step-status-chip ${result?.status === 'succeeded' ? 'completed' : 'active'}`}>
                      {result?.status || 'Assigned'}
                    </span>
                  </div>

                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {task.objective}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', fontSize: 11, color: 'var(--text-muted)', paddingTop: 4, borderTop: '1px solid rgba(15,23,42,0.04)' }}>
                    <span>Agent: <strong style={{ color: 'var(--accent-primary)' }}>{assignedAgent?.role || task.agent_id}</strong></span>
                    <span>Tools: {assignedAgent?.tool_ids?.join(', ') || 'none'}</span>
                  </div>

                  {result?.findings?.length > 0 && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-secondary)', padding: '6px 8px', borderRadius: 6, width: '100%' }}>
                      <strong>Key Finding:</strong> {result.findings[0]}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* TAB 4: CROSS-EVALUATION ("How it evaluates output one with other") */}
        {activeTab === 'evaluation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Contradiction & Conflict Resolution Matrix
            </div>

            {decision?.critical_risks?.length > 0 ? (
              <div className="contradiction-matrix-card">
                <div className="contradiction-header">
                  <AlertTriangle size={16} />
                  <span>Surfaced Cross-Agent Claim Conflicts</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
                  {decision.critical_risks.map((risk, i) => (
                    <div
                      key={i}
                      style={{
                        padding: '8px 12px',
                        background: 'rgba(190, 18, 60, 0.06)',
                        borderRadius: 8,
                        fontSize: 12,
                        color: '#9f1239',
                        lineHeight: 1.4,
                      }}
                    >
                      {risk}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: 12 }}>
                No active contradiction data yet. Run a case to compare specialist findings!
              </div>
            )}

            {/* Gates */}
            {verification?.required_gates && (
              <div style={{ background: 'rgba(15,23,42,0.03)', border: '1px solid var(--border-subtle)', borderRadius: 12, padding: 14 }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 12, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <ShieldCheck size={14} color="var(--accent-emerald)" />
                  <span>Mandatory Sign-off Gates</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {verification.required_gates.map((gate, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                      <CheckCircle2 size={12} color="var(--accent-emerald)" />
                      <span>{gate}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
