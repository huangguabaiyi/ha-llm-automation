/**
 * HA LLM Automation Panel
 * LitElement single-file panel for Home Assistant HACS integration
 */

const DOMAIN = "ha_llm_automation";

// ============================================================
// Utility: generate session id
// ============================================================
function genSessionId() {
  return `ses_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// ============================================================
// Utility: simple diff renderer (line-level)
// ============================================================
function renderDiff(before, after) {
  if (!before) return `<pre style="background:#1a1a2e;padding:12px;border-radius:6px;overflow:auto;font-size:12px;line-height:1.5">${escHtml(after)}</pre>`;
  const bLines = before.split("\n");
  const aLines = after.split("\n");
  const maxLen = Math.max(bLines.length, aLines.length);
  let html = '<table style="width:100%;border-collapse:collapse;font-size:12px;font-family:monospace">';
  for (let i = 0; i < maxLen; i++) {
    const b = bLines[i] ?? "";
    const a = aLines[i] ?? "";
    if (b === a) {
      html += `<tr><td style="padding:2px 6px;color:#888">${escHtml(a)}</td></tr>`;
    } else if (!b) {
      html += `<tr style="background:#0a3a0a"><td style="padding:2px 6px;color:#4caf50">+${escHtml(a)}</td></tr>`;
    } else if (!a) {
      html += `<tr style="background:#3a0a0a"><td style="padding:2px 6px;color:#f44336;text-decoration:line-through">-${escHtml(b)}</td></tr>`;
    } else {
      html += `<tr style="background:#3a2a0a"><td style="padding:2px 6px;color:#ffeb3b">~${escHtml(a)}</td></tr>`;
    }
  }
  html += "</table>";
  return html;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ============================================================
// Styles
// ============================================================
const STYLES = `
  :host {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: var(--primary-background-color, #111827);
    color: var(--primary-text-color, #e5e7eb);
    font-family: var(--paper-font-body1_-_font-family, sans-serif);
    font-size: 14px;
  }
  .header {
    display: flex;
    align-items: center;
    padding: 16px 24px;
    background: var(--app-header-background-color, #1f2937);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    flex-shrink: 0;
  }
  .header h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    flex: 1;
    color: var(--primary-text-color, #f3f4f6);
  }
  .tabs {
    display: flex;
    gap: 4px;
    padding: 0 24px;
    background: var(--app-header-background-color, #1f2937);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    flex-shrink: 0;
    overflow-x: auto;
  }
  .tab {
    padding: 10px 16px;
    cursor: pointer;
    border-bottom: 3px solid transparent;
    color: var(--secondary-text-color, #9ca3af);
    font-weight: 500;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .tab:hover { color: var(--primary-text-color, #f3f4f6); }
  .tab.active {
    border-bottom-color: var(--primary-color, #6366f1);
    color: var(--primary-color, #6366f1);
  }
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    gap: 24px;
  }
  .main-area { flex: 1; min-width: 0; }
  .log-area {
    width: 300px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }
  @media (max-width: 900px) {
    .content { flex-direction: column; }
    .log-area { width: 100%; }
  }
  .card {
    background: var(--card-background-color, #1f2937);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--secondary-text-color, #9ca3af);
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  textarea, input[type=text], input[type=password], input[type=number], select {
    width: 100%;
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 10px 12px;
    color: var(--primary-text-color, #e5e7eb);
    font-family: inherit;
    font-size: 14px;
    resize: vertical;
    box-sizing: border-box;
    outline: none;
    transition: border-color 0.15s;
  }
  textarea:focus, input:focus, select:focus {
    border-color: var(--primary-color, #6366f1);
  }
  textarea { min-height: 80px; }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.15s;
  }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary {
    background: var(--primary-color, #6366f1);
    color: white;
  }
  .btn-primary:hover:not(:disabled) { filter: brightness(1.1); }
  .btn-success { background: #059669; color: white; }
  .btn-success:hover:not(:disabled) { filter: brightness(1.1); }
  .btn-danger { background: #dc2626; color: white; }
  .btn-secondary {
    background: rgba(255,255,255,0.08);
    color: var(--primary-text-color, #e5e7eb);
  }
  .btn-secondary:hover:not(:disabled) { background: rgba(255,255,255,0.15); }
  .btn-sm { padding: 5px 10px; font-size: 12px; }
  .automation-card {
    background: rgba(0,0,0,0.2);
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 12px;
    overflow: hidden;
  }
  .automation-card.approved { border-color: #059669; }
  .automation-card.skipped { border-color: #6b7280; opacity: 0.6; }
  .automation-card.warning { border-color: #d97706; }
  .automation-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.03);
    cursor: pointer;
    user-select: none;
  }
  .automation-header:hover { background: rgba(255,255,255,0.06); }
  .auto-title { flex: 1; font-weight: 500; }
  .tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }
  .tag-merge { background: #1e3a5f; color: #60a5fa; }
  .tag-fix { background: #3a1e1e; color: #f87171; }
  .tag-ok { background: #1a3a1a; color: #4ade80; }
  .tag-warn { background: #3a2a0a; color: #fbbf24; }
  .yaml-block {
    background: #0d1117;
    border-radius: 6px;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre;
    color: #c9d1d9;
    border: 1px solid rgba(255,255,255,0.08);
    max-height: 400px;
    overflow-y: auto;
  }
  .auto-body { padding: 16px; }
  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
  .refine-input { margin-top: 8px; display: flex; gap: 8px; align-items: flex-start; }
  .refine-input textarea { min-height: 60px; flex: 1; }
  .log-panel {
    background: var(--card-background-color, #1f2937);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.06);
    display: flex;
    flex-direction: column;
    max-height: 500px;
    position: sticky;
    top: 0;
  }
  .log-title {
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: var(--secondary-text-color, #9ca3af);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .log-entries {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    font-family: monospace;
    font-size: 12px;
    line-height: 1.7;
  }
  .log-entry { color: #9ca3af; }
  .log-entry.error { color: #f87171; }
  .log-entry.success { color: #4ade80; }
  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.2);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .select-full { width: 100%; }
  .form-row { margin-bottom: 12px; }
  .form-label { display: block; margin-bottom: 6px; font-size: 13px; color: var(--secondary-text-color, #9ca3af); }
  .analysis-box {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .analysis-intent { font-weight: 600; margin-bottom: 8px; }
  .analysis-list { margin: 0; padding-left: 18px; }
  .analysis-list li { margin-bottom: 4px; color: var(--secondary-text-color, #9ca3af); }
  .diff-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;
  }
  @media (max-width: 700px) { .diff-container { grid-template-columns: 1fr; } }
  .diff-label { font-size: 12px; font-weight: 600; color: var(--secondary-text-color, #9ca3af); margin-bottom: 4px; }
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--secondary-text-color, #9ca3af);
  }
  .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
  .error-box {
    background: rgba(220,38,38,0.1);
    border: 1px solid rgba(220,38,38,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    color: #f87171;
    margin-bottom: 12px;
  }
  .success-box {
    background: rgba(5,150,105,0.1);
    border: 1px solid rgba(5,150,105,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    color: #4ade80;
    margin-bottom: 12px;
  }
  .backup-list { list-style: none; margin: 0; padding: 0; }
  .backup-item {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    gap: 10px;
  }
  .backup-item:last-child { border-bottom: none; }
  .backup-info { flex: 1; }
  .backup-name { font-family: monospace; font-size: 12px; }
  .backup-meta { font-size: 11px; color: var(--secondary-text-color, #9ca3af); margin-top: 2px; }
  .select-wrapper { position: relative; }
  .loading-overlay {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 20px;
    color: var(--secondary-text-color, #9ca3af);
    justify-content: center;
  }
`;

// ============================================================
// Main Panel Component
// ============================================================
class HaLlmAutomationPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "create";
    this._logs = [];
    this._loading = false;
    this._sessionId = null;
    this._logUnsub = null;

    // Create state
    this._createResult = null;
    this._createSystemPrompt = "";
    this._createApprovedItems = new Set();
    this._createSkippedItems = new Set();
    this._createRefineTexts = {};

    // Optimize state
    this._optimizeAutomations = [];
    this._optimizeSelectedId = "";
    this._optimizeAnalysis = null;
    this._optimizeAutoYaml = "";
    this._optimizeGenResult = null;
    this._optimizeSystemPrompt = "";
    this._optimizeRefineText = "";
    this._optimizeOriginalYaml = "";

    // Consolidate state
    this._consolidatePlan = null;
    this._consolidateApproved = {};
    this._consolidateSkipped = new Set();
    this._consolidateRefineTexts = {};
    this._consolidateExpandedYaml = {};

    // Backup state
    this._backups = [];

    this._render();
    this._loadAutomations();
  }

  set hass(val) {
    this._hass = val;
    this._render();
  }

  set panel(val) {
    this._panel = val;
  }

  // ------------------------------------------------------------------
  // WS helpers
  // ------------------------------------------------------------------

  async _ws(type, params = {}) {
    return this._hass.connection.sendMessagePromise({ type: `${DOMAIN}/${type}`, ...params });
  }

  async _startSession() {
    // Cancel previous subscription
    if (this._logUnsub) {
      this._logUnsub();
      this._logUnsub = null;
    }
    const sessionId = genSessionId();
    this._sessionId = sessionId;
    this._logs = [];
    this._render();

    // Subscribe to log events
    this._logUnsub = await this._hass.connection.subscribeMessage(
      (data) => {
        this._logs.push(data.message);
        this._render();
        this._scrollLog();
      },
      { type: `${DOMAIN}/subscribe_log`, session_id: sessionId }
    );
    return sessionId;
  }

  _log(msg) {
    this._logs.push(msg);
    this._render();
    this._scrollLog();
  }

  _scrollLog() {
    const logEl = this.shadowRoot.querySelector(".log-entries");
    if (logEl) logEl.scrollTop = logEl.scrollHeight;
  }

  // ------------------------------------------------------------------
  // Data loaders
  // ------------------------------------------------------------------

  async _loadAutomations() {
    try {
      const r = await this._ws("get_automations");
      this._optimizeAutomations = (r.automations || []).filter(a => a.accessible);
      this._render();
    } catch (e) {
      // ignore on load
    }
  }

  async _loadBackups() {
    try {
      const r = await this._ws("list_backups");
      this._backups = r.backups || [];
      this._render();
    } catch (e) {}
  }

  // ------------------------------------------------------------------
  // Tab: Create
  // ------------------------------------------------------------------

  async _createStart() {
    const ta = this.shadowRoot.querySelector("#create-req");
    const requirement = ta ? ta.value.trim() : "";
    if (!requirement) return;

    this._loading = true;
    this._createResult = null;
    this._createApprovedItems.clear();
    this._createSkippedItems.clear();
    this._createRefineTexts = {};
    this._render();

    try {
      const sessionId = await this._startSession();
      const r = await this._ws("create_start", {
        requirement,
        session_id: sessionId,
        use_docs: true,
      });
      this._createResult = r;
      this._createSystemPrompt = r.system_prompt || "";
      // Auto-approve all valid items
      (r.automations || []).forEach((item, i) => {
        if (item.parsed && (!item.warnings || item.warnings.length === 0)) {
          this._createApprovedItems.add(i);
        }
      });
    } catch (e) {
      this._log(`错误：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _createRefine(index) {
    const feedbackEl = this.shadowRoot.querySelector(`#refine-input-${index}`);
    const feedback = feedbackEl ? feedbackEl.value.trim() : "";
    if (!feedback) return;

    const item = this._createResult.automations[index];
    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      const r = await this._ws("create_refine", {
        current_yaml: item.yaml_str,
        feedback,
        system_prompt: this._createSystemPrompt,
        session_id: sessionId,
      });
      this._createResult.automations[index] = r;
      if (r.parsed && !r.warnings?.length) {
        this._createApprovedItems.add(index);
      } else {
        this._createApprovedItems.delete(index);
      }
      this._createRefineTexts[index] = "";
    } catch (e) {
      this._log(`修改失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _createSaveAll() {
    const automations = (this._createResult?.automations || [])
      .filter((item, i) => this._createApprovedItems.has(i) && item.parsed);

    if (automations.length === 0) {
      alert("没有选中的自动化可以保存");
      return;
    }

    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      const r = await this._ws("create_save", {
        automations: automations.map(a => a.parsed),
        session_id: sessionId,
      });
      this._log(`保存完成：${r.results?.length || 0} 条`);
      this._createResult = null;
    } catch (e) {
      this._log(`保存失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Tab: Optimize
  // ------------------------------------------------------------------

  async _optimizeAnalyze() {
    const id = this._optimizeSelectedId;
    if (!id) return;

    const sessionId = await this._startSession();
    this._loading = true;
    this._optimizeAnalysis = null;
    this._optimizeGenResult = null;
    this._render();

    try {
      const r = await this._ws("optimize_analyze", {
        automation_id: id,
        session_id: sessionId,
      });
      this._optimizeAnalysis = r.analysis;
      this._optimizeAutoYaml = r.automation_yaml;
      this._optimizeOriginalYaml = r.automation_yaml;
    } catch (e) {
      this._log(`分析失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _optimizeGenerate() {
    const sessionId = await this._startSession();
    this._loading = true;
    this._optimizeGenResult = null;
    this._render();

    try {
      const r = await this._ws("optimize_generate", {
        automation_yaml: this._optimizeAutoYaml,
        analysis: this._optimizeAnalysis,
        session_id: sessionId,
      });
      this._optimizeGenResult = r;
      this._optimizeSystemPrompt = r.system_prompt || "";
    } catch (e) {
      this._log(`生成失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _optimizeRefine() {
    const feedbackEl = this.shadowRoot.querySelector("#opt-refine-input");
    const feedback = feedbackEl ? feedbackEl.value.trim() : "";
    if (!feedback || !this._optimizeGenResult) return;

    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      const r = await this._ws("optimize_refine", {
        current_yaml: this._optimizeGenResult.yaml_str,
        feedback,
        system_prompt: this._optimizeSystemPrompt,
        session_id: sessionId,
      });
      this._optimizeGenResult = r;
      this._optimizeRefineText = "";
    } catch (e) {
      this._log(`修改失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _optimizeSave() {
    if (!this._optimizeGenResult?.parsed) {
      alert("无法保存：YAML 校验失败");
      return;
    }

    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      await this._ws("optimize_save", {
        automation_id: this._optimizeSelectedId,
        parsed: this._optimizeGenResult.parsed,
        session_id: sessionId,
      });
      this._log("优化保存成功！");
      this._optimizeAnalysis = null;
      this._optimizeGenResult = null;
      await this._loadAutomations();
    } catch (e) {
      this._log(`保存失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Tab: Consolidate
  // ------------------------------------------------------------------

  async _consolidateAnalyze() {
    const sessionId = await this._startSession();
    this._loading = true;
    this._consolidatePlan = null;
    this._consolidateApproved = {};
    this._consolidateSkipped = new Set();
    this._render();

    try {
      const r = await this._ws("consolidate_analyze", { session_id: sessionId });
      this._consolidatePlan = r;
      // Auto-approve merges and fixes
      (r.merge_groups || []).forEach((g, i) => {
        this._consolidateApproved[`merge_${i}`] = g;
      });
      (r.fix_items || []).forEach((f, i) => {
        this._consolidateApproved[`fix_${i}`] = f;
      });
    } catch (e) {
      this._log(`分析失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _consolidateRefine(type, index, currentYaml) {
    const feedbackEl = this.shadowRoot.querySelector(`#cons-refine-${type}-${index}`);
    const feedback = feedbackEl ? feedbackEl.value.trim() : "";
    if (!feedback) return;

    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      const r = await this._ws("consolidate_refine", {
        item_type: type,
        item_id: `${type}_${index}`,
        current_yaml: currentYaml,
        feedback,
        session_id: sessionId,
      });
      // Update the yaml in plan
      if (type === "merge") {
        this._consolidatePlan.merge_groups[index].merged_yaml = r.yaml_str;
        if (this._consolidateApproved[`merge_${index}`]) {
          this._consolidateApproved[`merge_${index}`].merged_yaml = r.yaml_str;
        }
      } else {
        this._consolidatePlan.fix_items[index].fixed_yaml = r.yaml_str;
        if (this._consolidateApproved[`fix_${index}`]) {
          this._consolidateApproved[`fix_${index}`].fixed_yaml = r.yaml_str;
        }
      }
      this._consolidateRefineTexts[`${type}_${index}`] = "";
    } catch (e) {
      this._log(`修改失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _consolidateExecute() {
    const approvedMerges = Object.entries(this._consolidateApproved)
      .filter(([k]) => k.startsWith("merge_"))
      .map(([, v]) => v);
    const approvedFixes = Object.entries(this._consolidateApproved)
      .filter(([k]) => k.startsWith("fix_"))
      .map(([, v]) => v);

    if (approvedMerges.length === 0 && approvedFixes.length === 0) {
      alert("没有批准的条目");
      return;
    }

    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      const r = await this._ws("consolidate_execute", {
        approved_merges: approvedMerges,
        approved_fixes: approvedFixes,
        session_id: sessionId,
      });
      this._log(`执行完成：${r.success} 成功，${r.failed} 失败`);
      this._consolidatePlan = null;
    } catch (e) {
      this._log(`执行失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Tab: Knowledge & Backup
  // ------------------------------------------------------------------

  async _refreshDocs() {
    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      const r = await this._ws("refresh_docs", { session_id: sessionId });
      this._log(`刷新完成：${(r.succeeded || []).join(", ")}`);
    } catch (e) {
      this._log(`刷新失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _restoreBackup(path) {
    if (!confirm(`确认恢复此备份？\n${path}\n\n此操作将创建对应的自动化。`)) return;

    const sessionId = await this._startSession();
    this._loading = true;
    this._render();

    try {
      await this._ws("restore_backup", { backup_path: path, session_id: sessionId });
      this._log("恢复完成");
    } catch (e) {
      this._log(`恢复失败：${e.message || e}`);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Render helpers
  // ------------------------------------------------------------------

  _renderCreate() {
    const result = this._createResult;
    const approvedCount = this._createApprovedItems.size;

    return `
      <div class="card">
        <div class="card-title">描述你的自动化需求</div>
        <div class="form-row">
          <textarea id="create-req" placeholder="例如：每天晚上10点关闭客厅所有灯；人离开后关闭空调和风扇" rows="4">${""}</textarea>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn btn-primary" id="btn-create-start" ?disabled="${this._loading}">
            ${this._loading ? '<span class="spinner"></span> 生成中...' : '▶ 生成自动化'}
          </button>
        </div>
      </div>

      ${result ? this._renderCreateResults(result) : ""}
      ${result && result.automations?.length ? `
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px">
          <button class="btn btn-secondary" id="btn-create-select-all">全选</button>
          <button class="btn btn-success" id="btn-create-save" ?disabled="${this._loading || approvedCount === 0}">
            ${this._loading ? '<span class="spinner"></span>' : '✓'} 保存选中的 (${approvedCount} 条)
          </button>
        </div>
      ` : ""}
    `;
  }

  _renderCreateResults(result) {
    const items = result.automations || [];
    if (!items.length) return '<div class="error-box">AI 未能生成有效的自动化配置</div>';

    return items.map((item, i) => {
      const approved = this._createApprovedItems.has(i);
      const skipped = this._createSkippedItems.has(i);
      const hasWarnings = item.warnings?.length > 0;
      const alias = item.parsed?.alias || `automation_${i + 1}`;
      const cardClass = skipped ? "automation-card skipped" : approved ? "automation-card approved" : hasWarnings ? "automation-card warning" : "automation-card";

      return `
        <div class="${cardClass}" id="auto-card-${i}">
          <div class="automation-header" id="auto-hdr-${i}">
            <span style="font-size:16px">${approved ? "✓" : skipped ? "✗" : "○"}</span>
            <span class="auto-title">[${i + 1}/${items.length}] ${escHtml(alias)}</span>
            ${hasWarnings ? '<span class="tag tag-warn">⚠ 有问题</span>' : ""}
            <span style="font-size:16px;color:#6b7280" class="expand-icon-${i}">▼</span>
          </div>
          <div class="auto-body" id="auto-body-${i}">
            ${hasWarnings ? `<div class="error-box">${item.warnings.map(w => escHtml(w)).join("<br>")}</div>` : ""}
            <div class="yaml-block">${escHtml(item.yaml_str)}</div>
            <div class="refine-input">
              <textarea id="refine-input-${i}" placeholder="输入修改意见让 AI 重新生成..." rows="2"></textarea>
              <button class="btn btn-secondary btn-sm" id="btn-refine-${i}">重新生成</button>
            </div>
            <div class="btn-row">
              <button class="btn btn-success btn-sm" id="btn-approve-${i}" ?disabled="${!item.parsed}">✓ 批准</button>
              <button class="btn btn-secondary btn-sm" id="btn-skip-${i}">✗ 跳过</button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  _renderOptimize() {
    const automations = this._optimizeAutomations;
    const analysis = this._optimizeAnalysis;
    const genResult = this._optimizeGenResult;

    return `
      <div class="card">
        <div class="card-title">选择要优化的自动化</div>
        <div class="form-row">
          <select class="select-full" id="opt-select">
            <option value="">— 请选择 —</option>
            ${automations.map(a => `<option value="${a.id}" ${this._optimizeSelectedId === a.id ? "selected" : ""}>${escHtml(a.alias)} [${a.id}]</option>`).join("")}
          </select>
        </div>
        <button class="btn btn-primary" id="btn-opt-analyze" ?disabled="${this._loading || !this._optimizeSelectedId}">
          ${this._loading && !analysis ? '<span class="spinner"></span> 分析中...' : '分析意图 ▶'}
        </button>
      </div>

      ${analysis ? `
        <div class="card">
          <div class="card-title">Step 1 — 分析报告</div>
          <div class="analysis-box">
            <div class="analysis-intent">🎯 意图：${escHtml(analysis.intent || "")}</div>
            ${analysis.issues?.length ? `
              <div style="margin-top:8px;font-weight:600;font-size:12px;color:#f87171">发现的问题：</div>
              <ul class="analysis-list">${analysis.issues.map(i => `<li>${escHtml(i)}</li>`).join("")}</ul>
            ` : ""}
            ${analysis.suggestions?.length ? `
              <div style="margin-top:8px;font-weight:600;font-size:12px;color:#60a5fa">优化建议：</div>
              <ul class="analysis-list">${analysis.suggestions.map(s => `<li>${escHtml(s)}</li>`).join("")}</ul>
            ` : ""}
          </div>
          <button class="btn btn-primary" id="btn-opt-generate" ?disabled="${this._loading}">
            ${this._loading && !genResult ? '<span class="spinner"></span> 生成中...' : '生成优化方案 ▶'}
          </button>
        </div>
      ` : ""}

      ${genResult ? `
        <div class="card">
          <div class="card-title">Step 2 — 优化结果</div>
          ${genResult.warnings?.length ? `<div class="error-box">${genResult.warnings.map(w => escHtml(w)).join("<br>")}</div>` : ""}
          <div class="diff-container">
            <div>
              <div class="diff-label">优化前</div>
              <div class="yaml-block">${escHtml(this._optimizeOriginalYaml)}</div>
            </div>
            <div>
              <div class="diff-label">优化后</div>
              <div class="yaml-block">${escHtml(genResult.yaml_str)}</div>
            </div>
          </div>
          <div class="refine-input" style="margin-top:12px">
            <textarea id="opt-refine-input" placeholder="输入追问修改意见..." rows="2"></textarea>
            <button class="btn btn-secondary btn-sm" id="btn-opt-refine">重新生成</button>
          </div>
          <div class="btn-row">
            <button class="btn btn-success" id="btn-opt-save" ?disabled="${!genResult.parsed || this._loading}">
              💾 保存优化结果
            </button>
          </div>
        </div>
      ` : ""}
    `;
  }

  _renderConsolidate() {
    const plan = this._consolidatePlan;

    return `
      <div class="card">
        <div class="card-title">批量整合自动化</div>
        <p style="color:var(--secondary-text-color,#9ca3af);margin:0 0 12px">
          分析所有已有自动化，识别可合并的重复项和需修复的问题，按场景整合。
        </p>
        <button class="btn btn-primary" id="btn-cons-analyze" ?disabled="${this._loading}">
          ${this._loading && !plan ? '<span class="spinner"></span> 分析中...' : '开始分析全部自动化 ▶'}
        </button>
      </div>

      ${plan ? this._renderConsolidatePlan(plan) : ""}
    `;
  }

  _renderConsolidatePlan(plan) {
    const merges = plan.merge_groups || [];
    const fixes = plan.fix_items || [];
    const oks = plan.ok_items || [];

    const approvedMerges = merges.filter((_, i) => this._consolidateApproved[`merge_${i}`] && !this._consolidateSkipped.has(`merge_${i}`));
    const approvedFixes = fixes.filter((_, i) => this._consolidateApproved[`fix_${i}`] && !this._consolidateSkipped.has(`fix_${i}`));

    return `
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div class="card-title" style="margin:0">聚合方案</div>
          <div style="font-size:12px;color:var(--secondary-text-color,#9ca3af)">
            合并 ${merges.length} 组 · 修复 ${fixes.length} 项 · 无需修改 ${oks.length} 项
          </div>
        </div>

        ${merges.map((g, i) => {
          const key = `merge_${i}`;
          const approved = !!this._consolidateApproved[key];
          const skipped = this._consolidateSkipped.has(key);
          const expanded = this._consolidateExpandedYaml[key];
          return `
            <div class="automation-card ${skipped ? "skipped" : approved ? "approved" : ""}">
              <div class="automation-header" id="cons-hdr-merge-${i}">
                <span class="tag tag-merge">合并</span>
                <span class="auto-title">场景：${escHtml(g.scenario || "")}</span>
                <span style="font-size:11px;color:#9ca3af">${(g.aliases || []).join(" + ")}</span>
                <span style="font-size:14px;color:#6b7280">▼</span>
              </div>
              ${expanded ? `
                <div class="auto-body">
                  <p style="color:#9ca3af;font-size:13px;margin:0 0 8px">${escHtml(g.reason || "")}</p>
                  <div class="yaml-block">${escHtml(g.merged_yaml || "")}</div>
                  <div class="refine-input" style="margin-top:8px">
                    <textarea id="cons-refine-merge-${i}" placeholder="输入修改意见..." rows="2"></textarea>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-refine-merge-${i}">重新生成</button>
                  </div>
                  <div class="btn-row">
                    <button class="btn btn-success btn-sm" id="btn-cons-approve-merge-${i}">✓ 批准</button>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-skip-merge-${i}">✗ 跳过</button>
                  </div>
                </div>
              ` : ""}
            </div>
          `;
        }).join("")}

        ${fixes.map((f, i) => {
          const key = `fix_${i}`;
          const approved = !!this._consolidateApproved[key];
          const skipped = this._consolidateSkipped.has(key);
          const expanded = this._consolidateExpandedYaml[key];
          return `
            <div class="automation-card ${skipped ? "skipped" : approved ? "approved" : ""}">
              <div class="automation-header" id="cons-hdr-fix-${i}">
                <span class="tag tag-fix">修复</span>
                <span class="auto-title">${escHtml(f.alias || f.id)}</span>
                <span style="font-size:11px;color:#f87171">${escHtml(f.issue || "")}</span>
                <span style="font-size:14px;color:#6b7280">▼</span>
              </div>
              ${expanded ? `
                <div class="auto-body">
                  <div class="yaml-block">${escHtml(f.fixed_yaml || "")}</div>
                  <div class="refine-input" style="margin-top:8px">
                    <textarea id="cons-refine-fix-${i}" placeholder="输入修改意见..." rows="2"></textarea>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-refine-fix-${i}">重新生成</button>
                  </div>
                  <div class="btn-row">
                    <button class="btn btn-success btn-sm" id="btn-cons-approve-fix-${i}">✓ 批准</button>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-skip-fix-${i}">✗ 跳过</button>
                  </div>
                </div>
              ` : ""}
            </div>
          `;
        }).join("")}

        ${oks.length ? `
          <div style="margin-top:8px;padding:8px 12px;background:rgba(74,222,128,0.05);border-radius:8px;font-size:12px;color:#4ade80">
            ✓ ${oks.length} 条自动化无需修改：${oks.map(o => o.alias).join("、")}
          </div>
        ` : ""}

        <div style="margin-top:16px;display:flex;justify-content:flex-end">
          <button class="btn btn-success" id="btn-cons-execute" ?disabled="${this._loading || (approvedMerges.length === 0 && approvedFixes.length === 0)}">
            ${this._loading ? '<span class="spinner"></span>' : '⚡'} 执行所有批准项 (${approvedMerges.length + approvedFixes.length})
          </button>
        </div>
      </div>
    `;
  }

  _renderConfig() {
    return `
      <div class="card">
        <div class="card-title">LLM 配置说明</div>
        <p style="color:var(--secondary-text-color,#9ca3af);margin:0">
          LLM 接口配置在集成安装时设置。若需修改，请进入「集成」页面 → HA LLM Automation → 选项。
        </p>
        <div style="margin-top:12px">
          <button class="btn btn-secondary" id="btn-reload-integ">重新加载配置</button>
        </div>
      </div>
    `;
  }

  _renderKnowledge() {
    return `
      <div class="card">
        <div class="card-title">知识库文档</div>
        <p style="color:var(--secondary-text-color,#9ca3af);margin:0 0 12px">
          刷新 HA 官方文档缓存（automation、trigger、condition、action、scripts 等）。
          文档 TTL 为 7 天，过期后自动重新抓取。
        </p>
        <button class="btn btn-primary" id="btn-refresh-docs" ?disabled="${this._loading}">
          ${this._loading ? '<span class="spinner"></span> 刷新中...' : '刷新文档缓存'}
        </button>
      </div>

      <div class="card">
        <div class="card-title">
          备份管理
          <button class="btn btn-secondary btn-sm" id="btn-load-backups" style="float:right">刷新列表</button>
        </div>
        ${this._backups.length === 0 ? `
          <div style="color:var(--secondary-text-color,#9ca3af);text-align:center;padding:20px">
            暂无备份记录
          </div>
        ` : `
          <ul class="backup-list">
            ${this._backups.map((b, i) => `
              <li class="backup-item">
                <div class="backup-info">
                  <div class="backup-name">${escHtml(b.name)}</div>
                  <div class="backup-meta">${b.mtime} · ${b.count} 条 · ${b.size_kb}KB</div>
                </div>
                <button class="btn btn-secondary btn-sm" id="btn-restore-${i}">恢复</button>
              </li>
            `).join("")}
          </ul>
        `}
      </div>
    `;
  }

  _renderLogPanel() {
    return `
      <div class="log-panel">
        <div class="log-title">
          运行日志
          <button class="btn btn-secondary btn-sm" id="btn-clear-log">清空</button>
        </div>
        <div class="log-entries">
          ${this._logs.length === 0
            ? '<div style="color:#4b5563;text-align:center;padding:20px">等待操作...</div>'
            : this._logs.map(l => `<div class="log-entry">${escHtml(l)}</div>`).join("")
          }
        </div>
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Main render
  // ------------------------------------------------------------------

  _render() {
    const tabs = [
      { id: "create", label: "创建" },
      { id: "optimize", label: "优化" },
      { id: "consolidate", label: "聚合" },
      { id: "config", label: "配置" },
      { id: "knowledge", label: "知识库/备份" },
    ];

    let mainContent = "";
    if (this._tab === "create") mainContent = this._renderCreate();
    else if (this._tab === "optimize") mainContent = this._renderOptimize();
    else if (this._tab === "consolidate") mainContent = this._renderConsolidate();
    else if (this._tab === "config") mainContent = this._renderConfig();
    else if (this._tab === "knowledge") mainContent = this._renderKnowledge();

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="header">
        <h1>🤖 HA LLM Automation</h1>
        ${this._loading ? '<span class="spinner"></span>' : ""}
      </div>
      <div class="tabs">
        ${tabs.map(t => `<div class="tab ${this._tab === t.id ? "active" : ""}" data-tab="${t.id}">${t.label}</div>`).join("")}
      </div>
      <div class="content">
        <div class="main-area">${mainContent}</div>
        <div class="log-area">${this._renderLogPanel()}</div>
      </div>
    `;

    this._bindEvents();
  }

  // ------------------------------------------------------------------
  // Event binding (after each render)
  // ------------------------------------------------------------------

  _bindEvents() {
    const $ = (id) => this.shadowRoot.getElementById(id);
    const root = this.shadowRoot;

    // Tabs
    root.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        this._tab = tab.dataset.tab;
        if (this._tab === "knowledge") this._loadBackups();
        if (this._tab === "optimize") this._loadAutomations();
        this._render();
      });
    });

    // Log clear
    const clearLog = $("btn-clear-log");
    if (clearLog) clearLog.addEventListener("click", () => { this._logs = []; this._render(); });

    // Create tab
    const btnCreateStart = $("btn-create-start");
    if (btnCreateStart) btnCreateStart.addEventListener("click", () => this._createStart());

    const btnCreateSave = $("btn-create-save");
    if (btnCreateSave) btnCreateSave.addEventListener("click", () => this._createSaveAll());

    const btnSelectAll = $("btn-create-select-all");
    if (btnSelectAll) {
      btnSelectAll.addEventListener("click", () => {
        (this._createResult?.automations || []).forEach((item, i) => {
          if (item.parsed) this._createApprovedItems.add(i);
        });
        this._render();
      });
    }

    // Automation card expand/approve/skip/refine
    if (this._createResult) {
      (this._createResult.automations || []).forEach((item, i) => {
        const hdr = $(`auto-hdr-${i}`);
        if (hdr) hdr.addEventListener("click", () => {
          const body = $(`auto-body-${i}`);
          if (body) body.style.display = body.style.display === "none" ? "" : "none";
        });

        const btnApprove = $(`btn-approve-${i}`);
        if (btnApprove) btnApprove.addEventListener("click", (e) => {
          e.stopPropagation();
          this._createApprovedItems.add(i);
          this._createSkippedItems.delete(i);
          this._render();
        });

        const btnSkip = $(`btn-skip-${i}`);
        if (btnSkip) btnSkip.addEventListener("click", (e) => {
          e.stopPropagation();
          this._createSkippedItems.add(i);
          this._createApprovedItems.delete(i);
          this._render();
        });

        const btnRefine = $(`btn-refine-${i}`);
        if (btnRefine) btnRefine.addEventListener("click", (e) => {
          e.stopPropagation();
          this._createRefine(i);
        });
      });
    }

    // Optimize tab
    const optSelect = $("opt-select");
    if (optSelect) optSelect.addEventListener("change", () => {
      this._optimizeSelectedId = optSelect.value;
      this._optimizeAnalysis = null;
      this._optimizeGenResult = null;
      this._render();
    });

    const btnOptAnalyze = $("btn-opt-analyze");
    if (btnOptAnalyze) btnOptAnalyze.addEventListener("click", () => this._optimizeAnalyze());

    const btnOptGenerate = $("btn-opt-generate");
    if (btnOptGenerate) btnOptGenerate.addEventListener("click", () => this._optimizeGenerate());

    const btnOptRefine = $("btn-opt-refine");
    if (btnOptRefine) btnOptRefine.addEventListener("click", () => this._optimizeRefine());

    const btnOptSave = $("btn-opt-save");
    if (btnOptSave) btnOptSave.addEventListener("click", () => this._optimizeSave());

    // Consolidate tab
    const btnConsAnalyze = $("btn-cons-analyze");
    if (btnConsAnalyze) btnConsAnalyze.addEventListener("click", () => this._consolidateAnalyze());

    const btnConsExec = $("btn-cons-execute");
    if (btnConsExec) btnConsExec.addEventListener("click", () => this._consolidateExecute());

    // Consolidate card headers (expand)
    if (this._consolidatePlan) {
      (this._consolidatePlan.merge_groups || []).forEach((g, i) => {
        const hdr = $(`cons-hdr-merge-${i}`);
        if (hdr) hdr.addEventListener("click", () => {
          const key = `merge_${i}`;
          this._consolidateExpandedYaml[key] = !this._consolidateExpandedYaml[key];
          this._render();
        });
        const btnApprove = $(`btn-cons-approve-merge-${i}`);
        if (btnApprove) btnApprove.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateApproved[`merge_${i}`] = this._consolidatePlan.merge_groups[i];
          this._consolidateSkipped.delete(`merge_${i}`);
          this._render();
        });
        const btnSkip = $(`btn-cons-skip-merge-${i}`);
        if (btnSkip) btnSkip.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateSkipped.add(`merge_${i}`);
          delete this._consolidateApproved[`merge_${i}`];
          this._render();
        });
        const btnRefine = $(`btn-cons-refine-merge-${i}`);
        if (btnRefine) btnRefine.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateRefine("merge", i, g.merged_yaml);
        });
      });

      (this._consolidatePlan.fix_items || []).forEach((f, i) => {
        const hdr = $(`cons-hdr-fix-${i}`);
        if (hdr) hdr.addEventListener("click", () => {
          const key = `fix_${i}`;
          this._consolidateExpandedYaml[key] = !this._consolidateExpandedYaml[key];
          this._render();
        });
        const btnApprove = $(`btn-cons-approve-fix-${i}`);
        if (btnApprove) btnApprove.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateApproved[`fix_${i}`] = this._consolidatePlan.fix_items[i];
          this._consolidateSkipped.delete(`fix_${i}`);
          this._render();
        });
        const btnSkip = $(`btn-cons-skip-fix-${i}`);
        if (btnSkip) btnSkip.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateSkipped.add(`fix_${i}`);
          delete this._consolidateApproved[`fix_${i}`];
          this._render();
        });
        const btnRefine = $(`btn-cons-refine-fix-${i}`);
        if (btnRefine) btnRefine.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateRefine("fix", i, f.fixed_yaml);
        });
      });
    }

    // Knowledge/Backup tab
    const btnRefreshDocs = $("btn-refresh-docs");
    if (btnRefreshDocs) btnRefreshDocs.addEventListener("click", () => this._refreshDocs());

    const btnLoadBackups = $("btn-load-backups");
    if (btnLoadBackups) btnLoadBackups.addEventListener("click", () => this._loadBackups());

    this._backups.forEach((b, i) => {
      const btnRestore = $(`btn-restore-${i}`);
      if (btnRestore) btnRestore.addEventListener("click", () => this._restoreBackup(b.file));
    });

    // Config tab
    const btnReloadInteg = $("btn-reload-integ");
    if (btnReloadInteg) btnReloadInteg.addEventListener("click", () => {
      window.location.reload();
    });
  }
}

customElements.define("ha-llm-automation", HaLlmAutomationPanel);
