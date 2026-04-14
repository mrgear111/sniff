import { useState } from 'react';

export default function AnalysisForm({ onResult, onStatusChange }) {
  const [repoUrl, setRepoUrl] = useState('');
  const [count, setCount] = useState(10);
  const [analysisMode, setAnalysisMode] = useState('offline');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');

  async function handleAnalyze() {
    if (!repoUrl.trim()) {
      onStatusChange('Please enter a GitHub repository URL.');
      return;
    }

    setLoading(true);
    setNotice('');
    onStatusChange('Analyzing commits...');
    onResult(null);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repoUrl: repoUrl.trim(),
          count: Number(count) || 10,
          analysisMode,
          anthropicApiKey: apiKey.trim(),
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Request failed');
      }

      if (data.notice) {
        setNotice(data.notice);
      }

      onResult(data);
      onStatusChange('Done.');
    } catch (err) {
      onStatusChange(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <label>
        GitHub Repo URL
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
        />
      </label>

      <label>
        Commit Count (max 30)
        <input
          type="number"
          value={count}
          min={1}
          max={30}
          onChange={(e) => setCount(e.target.value)}
        />
      </label>

      <fieldset className="mode-switch">
        <legend>Analysis Mode</legend>
        <label className="mode-option">
          <input
            type="radio"
            name="analysisMode"
            value="offline"
            checked={analysisMode === 'offline'}
            onChange={() => setAnalysisMode('offline')}
          />
          Offline mode, heuristics only
        </label>
        <label className="mode-option">
          <input
            type="radio"
            name="analysisMode"
            value="llm"
            checked={analysisMode === 'llm'}
            onChange={() => setAnalysisMode('llm')}
          />
          LLM tie-breaker with my Anthropic API key
        </label>
      </fieldset>

      {analysisMode === 'llm' && (
        <label className="api-key-wrap">
          Anthropic API Key
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-ant-..."
            autoComplete="off"
          />
        </label>
      )}

      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>

      {notice && <p className="notice">{notice}</p>}
    </section>
  );
}
