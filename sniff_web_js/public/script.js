const repoUrlInput = document.getElementById("repoUrl");
const countInput = document.getElementById("count");
const apiKeyInput = document.getElementById("apiKey");
const apiKeyWrap = document.getElementById("apiKeyWrap");
const modeNotice = document.getElementById("modeNotice");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const resultsEl = document.getElementById("results");
const leaderboardEl = document.getElementById("leaderboard");
const analysisModeInputs = document.querySelectorAll('input[name="analysisMode"]');

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showSummary(data) {
  summaryEl.classList.remove("hidden");
  summaryEl.innerHTML = `
    <h2>Summary</h2>
    <p><strong>Repository:</strong> ${escapeHtml(data.owner)}/${escapeHtml(data.repoName)}</p>
    <p><strong>Commits analyzed:</strong> ${data.count}</p>
    <p><strong>Likely Human:</strong> ${data.bands["Likely Human"]} | <strong>Mixed:</strong> ${data.bands["Mixed / Uncertain"]} | <strong>Likely AI-assisted:</strong> ${data.bands["Likely AI-assisted"]}</p>
  `;
}

function showResults(data) {
  resultsEl.classList.remove("hidden");
  const rows = data.results
    .map((row) => `
      <tr>
        <td><code>${escapeHtml(row.shortHash)}</code></td>
        <td>${escapeHtml(row.author)}</td>
        <td>${escapeHtml(row.message)}</td>
        <td>${row.score}</td>
        <td>${escapeHtml(row.band)}</td>
        <td>${escapeHtml(row.reasons.join(" | "))}</td>
      </tr>
    `)
    .join("");

  resultsEl.innerHTML = `
    <h2>Commit Results</h2>
    <table>
      <thead>
        <tr>
          <th>Hash</th>
          <th>Author</th>
          <th>Message</th>
          <th>Score</th>
          <th>Band</th>
          <th>Reasons</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function showLeaderboard(data) {
  leaderboardEl.classList.remove("hidden");
  const rows = data.leaderboard
    .map((row) => `
      <tr>
        <td>${escapeHtml(row.author)}</td>
        <td>${row.commitsAnalyzed}</td>
        <td>${row.highAiCommits}</td>
        <td>${row.avgScore}</td>
        <td>${row.aiDensity}%</td>
      </tr>
    `)
    .join("");

  leaderboardEl.innerHTML = `
    <h2>Contributor Leaderboard</h2>
    <table>
      <thead>
        <tr>
          <th>Author</th>
          <th>Commits</th>
          <th>High AI Commits</th>
          <th>Avg Score</th>
          <th>AI Density</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function getAnalysisMode() {
  const selected = document.querySelector('input[name="analysisMode"]:checked');
  return selected ? selected.value : "offline";
}

function syncModeUi() {
  const isLlmMode = getAnalysisMode() === "llm";
  apiKeyWrap.classList.toggle("hidden", !isLlmMode);
  apiKeyInput.disabled = !isLlmMode;
  modeNotice.classList.add("hidden");
  modeNotice.textContent = "";
}

async function analyze() {
  const repoUrl = repoUrlInput.value.trim();
  const count = Number(countInput.value || 10);

  if (!repoUrl) {
    statusEl.textContent = "Please enter a GitHub repository URL.";
    return;
  }

  analyzeBtn.disabled = true;
  statusEl.textContent = "Analyzing commits...";

  try {
    const analysisMode = getAnalysisMode();
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repoUrl,
        count,
        analysisMode,
        anthropicApiKey: apiKeyInput.value.trim()
      })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    showSummary(data);
    showResults(data);
    showLeaderboard(data);
    if (data.notice) {
      modeNotice.textContent = data.notice;
      modeNotice.classList.remove("hidden");
    }
    statusEl.textContent = "Done.";
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  } finally {
    analyzeBtn.disabled = false;
  }
}

analyzeBtn.addEventListener("click", analyze);
analysisModeInputs.forEach((input) => input.addEventListener("change", syncModeUi));
syncModeUi();
