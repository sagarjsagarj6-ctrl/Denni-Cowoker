import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ConversationPanel from './components/ConversationPanel';
import AgentsRegisterPanel from './components/AgentsRegisterPanel';
import SetupPanel from './components/SetupPanel';
import DocumentPanel from './components/DocumentPanel';
import WorkflowVisualizer from './components/WorkflowVisualizer';
import { api } from './api/client';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'agents' | 'setup' | 'documents'
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isWorkflowOpen, setIsWorkflowOpen] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isWorkflowLoading, setIsWorkflowLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [currentInputText, setCurrentInputText] = useState('');
  const [currentAttachedFiles, setCurrentAttachedFiles] = useState([]);
  const [serverHealth, setServerHealth] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [availableCases, setAvailableCases] = useState([]);
  const workflowTimers = useRef([]);

  const clearWorkflowTimers = () => {
    workflowTimers.current.forEach((timer) => clearTimeout(timer));
    workflowTimers.current = [];
  };

  useEffect(() => () => clearWorkflowTimers(), []);

  // Check health and initial configuration
  useEffect(() => {
    async function init() {
      try {
        const health = await api.getHealth();
        setServerHealth(health.status === 'ok');

        const cfg = await api.getConfig();
        setHasApiKey(cfg.provider_configured);

        const casesData = await api.listCases();
        setAvailableCases(casesData.cases || []);

        // Load recent runs if any
        const runsData = await api.listRuns(5);
        if (runsData.runs?.length) {
          const latest = runsData.runs[0];
          // Pre-populate latest run
          setActiveRun({ run: latest });
        }
      } catch (err) {
        console.warn('Initial setup check warning:', err);
      }
    }
    init();
  }, []);

  // When a run starts in ConversationPanel:
  const handleRunStart = (text, files) => {
    clearWorkflowTimers();
    setCurrentInputText(text);
    setCurrentAttachedFiles(files);
    setIsWorkflowLoading(true);
    setCurrentStep(1);

    // Auto-adjust and display workflow panel on right with animation!
    setIsWorkflowOpen(true);

    // Step-by-step simulated pipeline progression
    workflowTimers.current = [
      setTimeout(() => setCurrentStep(2), 600),
      setTimeout(() => setCurrentStep(3), 1400),
      setTimeout(() => setCurrentStep(4), 2200),
      setTimeout(() => setCurrentStep(5), 3200),
      setTimeout(() => setCurrentStep(6), 4400),
      setTimeout(() => setCurrentStep(7), 5400),
    ];
  };

  // When run finishes
  const handleRunComplete = (runData) => {
    clearWorkflowTimers();
    setIsWorkflowLoading(false);
    setCurrentStep(7);
    setActiveRun(runData);
  };

  return (
    <div className="app-container">
      {/* Left Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        serverHealth={serverHealth}
        hasApiKey={hasApiKey}
      />

      {/* Main Canvas Area */}
      <main className="main-canvas">
        {/* Canvas Header */}
        <header className="canvas-header">
          <div className="canvas-title-group">
            <span className="canvas-title">
              {activeTab === 'chat' && 'Dynamic Case Conversation Canvas'}
              {activeTab === 'agents' && 'Specialist Agents Register & Roster'}
                {activeTab === 'setup' && 'LLM Provider Setup'}
              {activeTab === 'documents' && 'Company Knowledge Base for RAG Agents'}
            </span>
            <span className="canvas-subtitle">
              {activeTab === 'chat' && 'Multimodal Input & End-to-End Autonomous Orchestration'}
              {activeTab === 'agents' && 'Autonomous roles with scoped tool permissions & policies'}
              {activeTab === 'setup' && 'API Keys, provider endpoints, and model routing'}
              {activeTab === 'documents' && 'Chunked documents, policies, BOMs, and ground truth records'}
            </span>
          </div>

          <div className="canvas-actions">
            {/* Toggle Right Workflow Visualizer button */}
            <button
              className="tool-action-btn"
              onClick={() => setIsWorkflowOpen(!isWorkflowOpen)}
              style={{
                color: isWorkflowOpen ? 'var(--accent-primary)' : 'var(--text-secondary)',
                borderColor: isWorkflowOpen ? 'rgba(99,102,241,0.4)' : 'var(--border-subtle)',
                background: isWorkflowOpen ? 'rgba(99,102,241,0.08)' : 'rgba(15,23,42,0.03)',
              }}
              title="Toggle Live Workflow Visualizer Panel"
            >
              {isWorkflowOpen ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}
              <span>{isWorkflowOpen ? 'Hide Workflow Panel' : 'Show Workflow Panel'}</span>
            </button>
          </div>
        </header>

        {/* Canvas Body (renders one of the 4 details panels) */}
        <div className="canvas-content">
          {activeTab === 'chat' && (
            <ConversationPanel
              messages={messages}
              setMessages={setMessages}
              activeRun={activeRun}
              setActiveRun={handleRunComplete}
              onRunStart={handleRunStart}
              isWorkflowLoading={isWorkflowLoading}
              availableCases={availableCases}
              onOpenWorkflow={() => setIsWorkflowOpen(true)}
            />
          )}

          {activeTab === 'agents' && <AgentsRegisterPanel />}

          {activeTab === 'setup' && (
            <SetupPanel
              onConfigUpdated={(cfg) => {
                setHasApiKey(cfg.provider_configured);
              }}
            />
          )}

          {activeTab === 'documents' && <DocumentPanel />}
        </div>
      </main>

      {/* Dynamic Right Panel (Auto-adjusts & displays workflow animation) */}
      <WorkflowVisualizer
        isOpen={isWorkflowOpen}
        onClose={() => setIsWorkflowOpen(false)}
        activeRun={activeRun}
        isWorkflowLoading={isWorkflowLoading}
        currentStep={currentStep}
        inputText={currentInputText}
        attachedFiles={currentAttachedFiles}
      />
    </div>
  );
}
