from __future__ import annotations

import re
from collections import Counter
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="LogSense",
    description="Understand log files in minutes instead of hours.",
    version="0.1.0",
)

LOG_LEVELS = ("ERROR", "WARNING", "INFO")
LEVEL_PATTERN = re.compile(r"\b(ERROR|WARN(?:ING)?|INFO)\b", re.IGNORECASE)


class LogAnalysisRequest(BaseModel):
    filename: str = Field(default="uploaded.log", max_length=255)
    content: str = Field(..., min_length=1)


class LogLine(BaseModel):
    line_number: int
    level: str
    message: str


class LogAnalysisResponse(BaseModel):
    filename: str
    line_count: int
    character_count: int
    blank_line_count: int
    longest_line_length: int
    average_line_length: float
    level_counts: dict[str, int]
    percentages: dict[str, float]
    important_lines: list[LogLine]
    preview: list[str]


def normalize_level(raw_level: str) -> str:
    level = raw_level.upper()
    if level == "WARN":
        return "WARNING"
    return level


def analyze_log(filename: str, content: str) -> dict[str, Any]:
    if not content.strip():
        raise HTTPException(status_code=400, detail="Log content is empty.")

    lines = content.splitlines()
    level_counts = Counter({level: 0 for level in LOG_LEVELS})
    important_lines: list[dict[str, Any]] = []
    total_line_length = 0
    longest_line_length = 0
    blank_line_count = 0

    for index, line in enumerate(lines, start=1):
        line_length = len(line)
        total_line_length += line_length
        longest_line_length = max(longest_line_length, line_length)

        if not line.strip():
            blank_line_count += 1

        match = LEVEL_PATTERN.search(line)
        if match:
            level = normalize_level(match.group(1))
            level_counts[level] += 1

            if level in {"ERROR", "WARNING"}:
                important_lines.append(
                    {
                        "line_number": index,
                        "level": level,
                        "message": line.strip(),
                    }
                )

    line_count = len(lines)
    average_line_length = round(total_line_length / line_count, 2) if line_count else 0
    signal_count = sum(level_counts.values())
    percentages = {
        level: round((level_counts[level] / signal_count) * 100, 2)
        if signal_count
        else 0
        for level in LOG_LEVELS
    }

    return {
        "filename": filename or "uploaded.log",
        "line_count": line_count,
        "character_count": len(content),
        "blank_line_count": blank_line_count,
        "longest_line_length": longest_line_length,
        "average_line_length": average_line_length,
        "level_counts": dict(level_counts),
        "percentages": percentages,
        "important_lines": important_lines[:100],
        "preview": lines[:500],
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "LogSense"}


@app.post("/api/analyze", response_model=LogAnalysisResponse)
def analyze(request: LogAnalysisRequest) -> dict[str, Any]:
    return analyze_log(request.filename, request.content)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HTML_PAGE


HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LogSense</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --text: #172033;
      --muted: #647084;
      --line: #d9deea;
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --error: #dc2626;
      --warning: #d97706;
      --info: #0284c7;
      --shadow: 0 10px 30px rgba(23, 32, 51, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }

    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }

    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 72px;
    }

    h1 {
      margin: 0;
      font-size: 1.5rem;
      line-height: 1.2;
    }

    .tagline {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.95rem;
    }

    main {
      padding: 28px 0 40px;
    }

    .workspace {
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 20px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .controls {
      padding: 20px;
    }

    label {
      display: block;
      color: var(--muted);
      font-size: 0.88rem;
      font-weight: 700;
      margin-bottom: 8px;
    }

    input[type="file"],
    textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      font: inherit;
    }

    input[type="file"] {
      padding: 10px;
    }

    textarea {
      min-height: 260px;
      padding: 12px;
      resize: vertical;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 0.86rem;
      line-height: 1.5;
    }

    button {
      width: 100%;
      border: 0;
      border-radius: 8px;
      background: var(--primary);
      color: white;
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      padding: 12px 16px;
      transition: background 120ms ease, transform 120ms ease;
    }

    button:hover {
      background: var(--primary-dark);
    }

    button:active {
      transform: translateY(1px);
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.6;
    }

    .stack {
      display: grid;
      gap: 16px;
    }

    .meta {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      padding: 16px;
    }

    .stat {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfcff;
    }

    .stat strong {
      display: block;
      font-size: 1.75rem;
      line-height: 1;
      margin-bottom: 6px;
    }

    .stat span {
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
    }

    .error strong {
      color: var(--error);
    }

    .warning strong {
      color: var(--warning);
    }

    .info strong {
      color: var(--info);
    }

    .details {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1px;
      border-top: 1px solid var(--line);
      background: var(--line);
    }

    .detail {
      background: var(--panel);
      padding: 14px 16px;
    }

    .detail span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
    }

    .detail strong {
      display: block;
      margin-top: 4px;
      font-size: 1rem;
    }

    .section {
      padding: 16px;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 1rem;
    }

    .important-list {
      display: grid;
      gap: 8px;
      max-height: 260px;
      overflow: auto;
    }

    .line-item {
      display: grid;
      grid-template-columns: 70px 90px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 0.82rem;
      overflow-wrap: anywhere;
    }

    .badge {
      display: inline-flex;
      justify-content: center;
      border-radius: 999px;
      padding: 3px 8px;
      color: white;
      font-family: inherit;
      font-size: 0.72rem;
      font-weight: 800;
    }

    .badge.ERROR {
      background: var(--error);
    }

    .badge.WARNING {
      background: var(--warning);
    }

    .log-viewer {
      margin: 0;
      max-height: 520px;
      overflow: auto;
      border-top: 1px solid var(--line);
      background: #111827;
      color: #d1d5db;
      padding: 16px;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 0.82rem;
      line-height: 1.55;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .empty {
      color: var(--muted);
      padding: 24px 16px;
      text-align: center;
    }

    .error-message {
      display: none;
      border: 1px solid #fecaca;
      border-radius: 8px;
      background: #fef2f2;
      color: #991b1b;
      padding: 10px 12px;
      font-size: 0.9rem;
    }

    @media (max-width: 860px) {
      .workspace,
      .summary,
      .details {
        grid-template-columns: 1fr;
      }

      .line-item {
        grid-template-columns: 54px 82px minmax(0, 1fr);
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="shell topbar">
      <div>
        <h1>LogSense</h1>
        <p class="tagline">Understand log files in minutes instead of hours.</p>
      </div>
    </div>
  </header>

  <main class="shell workspace">
    <section class="panel controls stack">
      <div>
        <label for="fileInput">Upload Log File</label>
        <input id="fileInput" type="file" accept=".log,.txt,text/plain">
      </div>

      <div>
        <label for="logText">Log Content</label>
        <textarea id="logText" spellcheck="false" placeholder="Paste a log file here or choose one above."></textarea>
      </div>

      <button id="analyzeButton">Analyze Log</button>
      <div id="errorMessage" class="error-message"></div>
      <p class="meta" id="fileMeta">No file selected yet.</p>
    </section>

    <section class="panel">
      <div id="emptyState" class="empty">Upload or paste a log file to see counts, statistics, and important lines.</div>
      <div id="results" hidden>
        <div class="summary">
          <div class="stat error">
            <strong id="errorCount">0</strong>
            <span>Errors</span>
          </div>
          <div class="stat warning">
            <strong id="warningCount">0</strong>
            <span>Warnings</span>
          </div>
          <div class="stat info">
            <strong id="infoCount">0</strong>
            <span>Info</span>
          </div>
        </div>

        <div class="details">
          <div class="detail">
            <span>Lines</span>
            <strong id="lineCount">0</strong>
          </div>
          <div class="detail">
            <span>Characters</span>
            <strong id="characterCount">0</strong>
          </div>
          <div class="detail">
            <span>Blank Lines</span>
            <strong id="blankLineCount">0</strong>
          </div>
          <div class="detail">
            <span>Avg Line Length</span>
            <strong id="averageLineLength">0</strong>
          </div>
        </div>

        <div class="section">
          <h2>Important Lines</h2>
          <div id="importantLines" class="important-list"></div>
        </div>

        <h2 class="section">File Preview</h2>
        <pre id="logPreview" class="log-viewer"></pre>
      </div>
    </section>
  </main>

  <script>
    const fileInput = document.querySelector("#fileInput");
    const logText = document.querySelector("#logText");
    const analyzeButton = document.querySelector("#analyzeButton");
    const errorMessage = document.querySelector("#errorMessage");
    const fileMeta = document.querySelector("#fileMeta");
    const emptyState = document.querySelector("#emptyState");
    const results = document.querySelector("#results");

    let filename = "pasted.log";

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) {
        return;
      }

      filename = file.name;
      logText.value = await file.text();
      fileMeta.textContent = `${file.name} - ${formatNumber(file.size)} bytes`;
      hideError();
    });

    analyzeButton.addEventListener("click", analyzeCurrentLog);

    async function analyzeCurrentLog() {
      const content = logText.value;
      if (!content.trim()) {
        showError("Paste or upload log content before analyzing.");
        return;
      }

      analyzeButton.disabled = true;
      analyzeButton.textContent = "Analyzing...";
      hideError();

      try {
        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ filename, content })
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "Log analysis failed.");
        }

        renderResults(payload);
      } catch (error) {
        showError(error.message);
      } finally {
        analyzeButton.disabled = false;
        analyzeButton.textContent = "Analyze Log";
      }
    }

    function renderResults(data) {
      emptyState.hidden = true;
      results.hidden = false;

      setText("#errorCount", data.level_counts.ERROR);
      setText("#warningCount", data.level_counts.WARNING);
      setText("#infoCount", data.level_counts.INFO);
      setText("#lineCount", formatNumber(data.line_count));
      setText("#characterCount", formatNumber(data.character_count));
      setText("#blankLineCount", formatNumber(data.blank_line_count));
      setText("#averageLineLength", data.average_line_length);

      const importantLines = document.querySelector("#importantLines");
      importantLines.innerHTML = "";

      if (data.important_lines.length === 0) {
        importantLines.innerHTML = `<div class="meta">No ERROR or WARNING lines found.</div>`;
      } else {
        for (const item of data.important_lines) {
          const row = document.createElement("div");
          row.className = "line-item";
          row.innerHTML = `
            <span>#${item.line_number}</span>
            <span class="badge ${item.level}">${item.level}</span>
            <span></span>
          `;
          row.lastElementChild.textContent = item.message;
          importantLines.appendChild(row);
        }
      }

      const preview = data.preview.join("\\n");
      document.querySelector("#logPreview").textContent = preview;
      fileMeta.textContent = `${data.filename} - ${formatNumber(data.line_count)} lines analyzed`;
    }

    function setText(selector, value) {
      document.querySelector(selector).textContent = value;
    }

    function formatNumber(value) {
      return new Intl.NumberFormat().format(value);
    }

    function showError(message) {
      errorMessage.textContent = message;
      errorMessage.style.display = "block";
    }

    function hideError() {
      errorMessage.textContent = "";
      errorMessage.style.display = "none";
    }
  </script>
</body>
</html>
"""
