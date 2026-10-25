import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Save,
  Eye,
  EyeOff,
  RefreshCw,
  Zap,
  Cloud,
  Cpu
} from 'lucide-react';
import { api } from '../api/client';

export default function SetupPanel({ onConfigUpdated }) {
  const [provider, setProvider] = useState('openrouter');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [maskedKey, setMaskedKey] = useState('');
  const [model, setModel] = useState('google/gemma-4-31b-it:free');
  const [baseUrl, setBaseUrl] = useState('https://openrouter.ai/api/v1');
  const [googleApiKey, setGoogleApiKey] = useState('');
  const [maskedGoogleKey, setMaskedGoogleKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-2.5-flash');
  const [ollamaModel, setOllamaModel] = useState('qwen2.5:7b');
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('http://localhost:11434');

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    async function loadConfig() {
      try {
        const cfg = await api.getConfig();
        if (cfg.openrouter_api_key_masked) setMaskedKey(cfg.openrouter_api_key_masked);
        if (cfg.openrouter_model) setModel(cfg.openrouter_model);
        if (cfg.openrouter_base_url) setBaseUrl(cfg.openrouter_base_url);
        if (cfg.google_api_key_masked) setMaskedGoogleKey(cfg.google_api_key_masked);
        if (cfg.google_model) setGeminiModel(cfg.google_model);
        if (cfg.ollama_model) setOllamaModel(cfg.ollama_model);
        if (cfg.ollama_base_url) setOllamaBaseUrl(cfg.ollama_base_url);
        if (cfg.model_provider) setProvider(cfg.model_provider);
      } catch (err) {
        console.error('Failed to load config:', err);
      }
    }
    loadConfig();
  }, []);

  const buildPayload = () => {
    if (provider === 'ollama') {
      return {
        model_provider: 'ollama',
        ollama_base_url: ollamaBaseUrl.trim() || undefined,
        ollama_model: ollamaModel.trim() || undefined,
      };
    }
    if (provider === 'gemini') {
      return {
        model_provider: 'gemini',
        google_api_key: googleApiKey.trim() || undefined,
        google_model: geminiModel.trim() || undefined,
      };
    }
    return {
      model_provider: 'openrouter',
      openrouter_api_key: apiKey.trim() || undefined,
      openrouter_base_url: baseUrl.trim() || undefined,
      openrouter_model: model.trim() || undefined,
    };
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConfig(buildPayload());
      setTestResult(res);
    } catch (err) {
      setTestResult({ status: 'error', message: err.message });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e?.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      const payload = buildPayload();
      if (provider === 'openrouter' && !apiKey.trim() && !maskedKey) {
        setTestResult({
          status: 'error',
          message: 'Enter an OpenRouter API key before saving.',
        });
        return;
      }
      if (provider === 'gemini' && !googleApiKey.trim() && !maskedGoogleKey) {
        setTestResult({
          status: 'error',
          message: 'Enter a Google Gemini API key before saving.',
        });
        return;
      }

      const res = await api.updateConfig(payload);
      if (res.google_api_key_masked) {
        setMaskedGoogleKey(res.google_api_key_masked);
        setGoogleApiKey('');
      }
      if (res.openrouter_api_key_masked) {
        setMaskedKey(res.openrouter_api_key_masked);
        setApiKey('');
      }
      setSaveSuccess(true);
      if (onConfigUpdated) onConfigUpdated(res);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const activeModel = {
    ollama: ollamaModel,
    gemini: geminiModel,
    openrouter: model,
  }[provider];

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <div className="setup-container">
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
            AI Provider & API Key
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
            Choose a hosted model provider, or run a local Ollama model. Each hosted provider has its own usage limits and pricing.
          </p>
        </div>

        <form className="setup-card" onSubmit={handleSaveConfig}>
          {/* Provider switch */}
          <div className="form-group">
            <label className="form-label">
              <span>Provider</span>
              <span className="form-hint">Hosted provider API key, or local Ollama</span>
            </label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => setProvider('openrouter')}
                style={{
                  flex: '1 1 220px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 12px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                  border: provider === 'openrouter' ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                  background: provider === 'openrouter' ? 'rgba(99,102,241,0.08)' : 'transparent',
                  color: 'var(--text-primary)',
                }}
              >
                <Cloud size={16} />
                <span>
                  <strong style={{ display: 'block', fontSize: 13 }}>OpenRouter (cloud)</strong>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    Free-tier `:free` models, ~200 requests/day
                  </span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => setProvider('gemini')}
                style={{
                  flex: '1 1 220px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 12px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                  border: provider === 'gemini' ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                  background: provider === 'gemini' ? 'rgba(99,102,241,0.08)' : 'transparent',
                  color: 'var(--text-primary)',
                }}
              >
                <Cloud size={16} />
                <span>
                  <strong style={{ display: 'block', fontSize: 13 }}>Google Gemini (cloud)</strong>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    Google AI Studio API key; quota and pricing vary
                  </span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => setProvider('ollama')}
                style={{
                  flex: '1 1 220px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 12px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                  border: provider === 'ollama' ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                  background: provider === 'ollama' ? 'rgba(99,102,241,0.08)' : 'transparent',
                  color: 'var(--text-primary)',
                }}
              >
                <Cpu size={16} />
                <span>
                  <strong style={{ display: 'block', fontSize: 13 }}>Ollama (local, free)</strong>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    No API key, unlimited, runs on your machine
                  </span>
                </span>
              </button>
            </div>
          </div>

          {provider === 'openrouter' ? (
            <>
              {/* OpenRouter / OpenKey API Key */}
              <div className="form-group">
                <label className="form-label">
                  <span>OpenRouter / OpenKey API Key</span>
                  {maskedKey && (
                    <span style={{ fontSize: 11, color: 'var(--accent-emerald)' }}>
                      Current: {maskedKey}
                    </span>
                  )}
                </label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder={maskedKey ? 'Leave blank to keep existing key or enter new key' : 'sk-or-v1-...'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="form-input mono"
                    style={{ width: '100%', paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    style={{
                      position: 'absolute',
                      right: 12,
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <div className="form-hint">
                  Use a key from openrouter.ai or your OpenRouter-compatible gateway. It is saved in the workspace .env and never shown in full here.
                </div>
              </div>

              {/* Base URL */}
              <div className="form-group">
                <label className="form-label">
                  <span>API Base URL</span>
                </label>
                <input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  className="form-input mono"
                  placeholder="https://openrouter.ai/api/v1"
                />
              </div>
            </>
          ) : provider === 'gemini' ? (
            <>
              <div className="form-group">
                <label className="form-label">
                  <span>Google Gemini API Key</span>
                  {maskedGoogleKey && (
                    <span style={{ fontSize: 11, color: 'var(--accent-emerald)' }}>
                      Current: {maskedGoogleKey}
                    </span>
                  )}
                </label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder={maskedGoogleKey ? 'Leave blank to keep existing key or enter a new key' : 'Enter your Google AI Studio API key'}
                    value={googleApiKey}
                    onChange={(e) => setGoogleApiKey(e.target.value)}
                    className="form-input mono"
                    style={{ width: '100%', paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    style={{
                      position: 'absolute',
                      right: 12,
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <div className="form-hint">
                  Create a key in Google AI Studio. It is saved in the workspace .env and never shown in full here.
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Ollama server */}
              <div className="form-group">
                <label className="form-label">
                  <span>Ollama Server URL</span>
                </label>
                <input
                  type="text"
                  value={ollamaBaseUrl}
                  onChange={(e) => setOllamaBaseUrl(e.target.value)}
                  className="form-input mono"
                  placeholder="http://localhost:11434"
                />
                <div className="form-hint">
                  Start the server with <code>ollama serve</code>, then pull a model with{' '}
                  <code>ollama pull {ollamaModel || 'qwen2.5:7b'}</code>.
                </div>
              </div>
            </>
          )}

          {/* Model Selection */}
          <div className="form-group">
            <label className="form-label">
              <span>Target LLM ID</span>
            </label>
            <input
              type="text"
              placeholder={
                provider === 'ollama'
                  ? 'Enter a pulled Ollama model ID (e.g. llama3.1:8b)'
                  : provider === 'gemini'
                    ? 'Enter a Gemini model ID (e.g. gemini-2.5-flash)'
                    : 'Enter a model ID (e.g. openai/gpt-4o-mini)'
              }
              value={activeModel}
              onChange={(e) => {
                if (provider === 'ollama') setOllamaModel(e.target.value);
                else if (provider === 'gemini') setGeminiModel(e.target.value);
                else setModel(e.target.value);
              }}
              className="form-input mono"
              style={{ marginTop: 6 }}
            />
          </div>

          {/* Test Connection Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingTop: 4 }}>
            <button
              type="button"
              className="tool-action-btn"
              onClick={handleTestConnection}
              disabled={testing}
              style={{ color: 'var(--accent-primary)', borderColor: 'rgba(99,102,241,0.3)', padding: '8px 14px' }}
            >
              {testing ? <RefreshCw size={14} className="spinning" /> : <Zap size={14} />}
              <span>{testing ? 'Testing Connection...' : 'Test Connection & Ping Provider'}</span>
            </button>

            {testResult && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 12,
                  padding: '6px 12px',
                  borderRadius: 8,
                  background: testResult.status === 'ok' ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                  color: testResult.status === 'ok' ? '#065f46' : '#9f1239',
                  border: `1px solid ${testResult.status === 'ok' ? 'rgba(16,185,129,0.3)' : 'rgba(244,63,94,0.3)'}`,
                }}
              >
                {testResult.status === 'ok' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                <span>
                  {testResult.status === 'ok'
                    ? `Connected! Latency: ${testResult.latency_ms}ms`
                    : testResult.message}
                </span>
              </div>
            )}
          </div>

          {/* Save Button */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
            <div>
              {saveSuccess && (
                <span style={{ fontSize: 12, color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} /> Settings saved and reloaded!
                </span>
              )}
            </div>
            <button
              type="submit"
              className="send-btn"
              disabled={saving}
              style={{ padding: '10px 20px' }}
            >
              <Save size={14} />
              <span>{saving ? 'Saving...' : 'Save & Apply Configuration'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
