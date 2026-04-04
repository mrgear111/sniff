require("dotenv").config();

const express = require("express");
const cors = require("cors");
const path = require("path");
const { analyzeRepoFromUrl } = require("./analyzer");

const app = express();
const PORT = process.env.PORT || 8080;

app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "..", "public")));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, service: "sniff-web-js" });
});

app.post("/api/analyze", async (req, res) => {
  try {
    const repoUrl = (req.body?.repoUrl || "").trim();
    const countRaw = Number(req.body?.count || 10);
    const count = Number.isFinite(countRaw) ? Math.max(1, Math.min(30, Math.floor(countRaw))) : 10;
    const analysisMode = (req.body?.analysisMode || "offline").trim() === "llm" ? "llm" : "offline";
    const anthropicApiKey = (req.body?.anthropicApiKey || "").trim();
    const useLlm = analysisMode === "llm" && Boolean(anthropicApiKey || process.env.ANTHROPIC_API_KEY);

    if (!repoUrl) {
      return res.status(400).json({ error: "repoUrl is required" });
    }

    const data = await analyzeRepoFromUrl(repoUrl, count, {
      githubToken: process.env.GITHUB_TOKEN,
      useLlm,
      anthropicApiKey
    });

    if (analysisMode === "llm" && !useLlm) {
      data.notice = "LLM mode was selected, but no Anthropic API key was provided. Falling back to offline heuristics.";
      data.mode = "offline";
    }

    return res.json(data);
  } catch (error) {
    return res.status(500).json({ error: error.message || "Analysis failed" });
  }
});

app.get("*", (_req, res) => {
  res.sendFile(path.join(__dirname, "..", "public", "index.html"));
});

app.listen(PORT, () => {
  console.log(`sniff-web-js running on http://localhost:${PORT}`);
});
