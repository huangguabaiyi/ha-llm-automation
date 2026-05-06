/**
 * HA LLM Automation Panel — v2.0
 * Full rewrite with config tab, improved UX, color-coded logs, toast notifications
 */

const DOMAIN = "ha_llm_automation";

// ============================================================
// i18n — Translations (zh / en)
// Follows hass.language: zh-Hans/zh-Hant → zh, otherwise → en
//
// Convention: translation values are ASCII double-quoted strings. Any literal
// ASCII double quote inside a value MUST be escaped as \"; unescaped " will
// produce a SyntaxError at module load and blank out the panel. Prefer full-
// width quotes “ ” for quoted phrases to sidestep the footgun entirely.
// ============================================================
const TRANSLATIONS = {
  zh: {
    tab_create: "✨ 创建", tab_optimize: "🔧 优化",
    tab_consolidate: "🔗 聚合", tab_manage: "📋 管理",
    tab_config: "⚙ 配置", tab_knowledge: "📚 知识库/备份",
    theme_auto: "自动", theme_dark: "暗色", theme_light: "亮色",
    theme_toggle: "切换主题（当前：{label}）",
    abort_title: "终止当前操作",
    create_title: "描述自动化需求",
    create_placeholder: "例如：每天晚上10点关闭客厅所有灯；人离开后关闭空调和风扇",
    create_btn: "▶ 生成自动化", create_btn_loading: "生成中...",
    create_sel_all: "☑ 全选", create_sel_none: "☐ 全不选",
    create_save_sel: "保存选中 ({n} 条)",
    create_saving: "保存成功：{n} 条",
    create_has_issues: "⚠ 有问题", create_ok: "✓ 正常",
    create_refine_hide: "▲ 收起追问", create_refine_show: "✏ 追问修改",
    create_refine_placeholder: "输入修改意见让 AI 重新生成...",
    create_refine_btn: "重新生成",
    create_no_yaml: "AI 未能生成有效的自动化配置",
    create_expand_hint: "▼ 展开选择（{n} 个可选）",
    opt_select_title: "选择要优化的自动化",
    opt_refresh: "🔄 刷新列表",
    opt_loading: "正在加载自动化列表...",
    opt_load_fail: "加载失败，请点击\"刷新列表\"重试",
    opt_empty: "暂无可优化的自动化（存储型）",
    opt_placeholder: "— 请选择 —",
    opt_analyze_btn: "分析意图 ▶", opt_analyze_loading: "分析中...",
    opt_step1_title: "Step 1 — 分析报告",
    opt_issues_title: "⚠ 发现的问题：", opt_sugg_title: "✦ 优化建议：",
    opt_direction_label: "追问 / 追加方向（可选）",
    opt_direction_placeholder: "可补充分析追问或优化方向，如：重点分析能否加夜间条件、补全其他区域设备...",
    opt_reanalyze: "🔄 重新分析",
    opt_generate_btn: "生成优化方案 ▶", opt_generate_loading: "生成中...",
    opt_step2_title: "Step 2 — 优化结果",
    opt_diff_side: "⇔ 左右对比", opt_diff_inline: "≡ 内联 diff",
    opt_diff_before: "优化前", opt_diff_after: "优化后",
    opt_diff_inline_label: "内联 diff（优化前 → 优化后）",
    opt_refine_placeholder: "输入追问修改意见...",
    opt_refine_btn: "重新生成",
    opt_save_btn: "💾 保存优化结果",
    cons_title: "批量整合自动化",
    cons_refresh: "🔄 刷新列表",
    cons_desc: "分析所有已有自动化，识别可合并的重复项和需修复的问题，按场景整合。",
    cons_loading: "正在加载自动化列表...",
    cons_load_fail: "加载失败，请点击\"刷新列表\"重试",
    cons_empty: "暂无可整合的自动化（存储型）",
    cons_select_label: "选择要参与整合的自动化（{sel}/{total} 已选）：",
    cons_inaccessible: "⚠ 不可访问",
    cons_sel_all: "☑ 全选", cons_sel_none: "☐ 全不选",
    cons_del_btn: "🗑 清除不可访问（{n} 条）",
    cons_deleting: "清除中...",
    cons_analyze_btn: "▶ 开始分析（{n} 条）", cons_analyze_loading: "分析中...",
    cons_plan_title: "聚合方案",
    cons_summary: "合并 {merge} · 修复 {fix} · 无需修改 {ok}",
    cons_batch_selected: "已勾选 {n} 项",
    cons_batch_all: "☑ 全选", cons_batch_none: "☐ 全不选",
    cons_batch_exec: "▶ 批量执行（{n} 项）",
    cons_merge_tag: "合并", cons_fix_tag: "修复",
    cons_scenario: "场景：{name}",
    cons_originals: "原始自动化（共 {n} 条，将被合并替换）：",
    cons_no_original: "（无法获取原始配置）",
    cons_merged_label: "合并后：",
    cons_refine_placeholder: "输入修改意见...",
    cons_approve: "✓ 批准", cons_skip: "✗ 跳过",
    cons_issue_prefix: "问题：{issue}",
    cons_fix_before: "原始配置", cons_fix_after: "修复后",
    cons_ok_items: "✓ {n} 条无需修改：{list}",
    cons_exec_all: "⚡ 执行所有批准项 ({n})",
    cons_refine_btn: "重新生成",
    manage_loading: "加载中...",
    manage_not_loaded: "自动化列表未加载",
    manage_load_btn: "🔄 加载列表",
    manage_title: "自动化管理",
    manage_refresh: "🔄 刷新列表",
    manage_empty: "暂无自动化",
    manage_sel_all: "全选", manage_sel_none: "全不选",
    manage_selected: "已选 {n} 条",
    manage_backup_btn: "💾 备份选中({n})",
    manage_delete_btn: "🗑 删除选中({n})",
    manage_inaccessible: "不可访问",
    config_title: "LLM 接口配置",
    config_loading: "加载配置中...",
    config_model: "模型名称",
    config_filter_title: "实体筛选（可选）",
    config_filter_note: "注：以下筛选仅影响发送给 LLM 的设备与实体列表，不影响自动化的分析范围。",
    config_extra_domains: "额外可见域（逗号分隔，如 notify,remote）",
    config_hidden_domains: "隐藏域（输入 domain + 回车）",
    config_hidden_placeholder: "weather,person（逗号分隔）",
    config_area_filter: "仅显示区域（选择后实体列表只含这些区域）",
    config_integ_filter: "仅显示集成",
    config_label_filter: "仅显示标签",
    config_advanced: "高级选项",
    config_log_prompt: "在日志中打印发给 LLM 的 Prompt 文本（紫色显示）",
    config_use_docs: "在 Prompt 中注入 HA 官方文档（本地缓存，7 天后自动更新；关闭则完全跳过）",
    config_save_btn: "💾 保存配置",
    config_saving: "⏳ 保存中...",
    config_base_url: "Base URL（openai_compatible 需填，如 https://api.xxx.com/v1）",
    know_title: "知识库文档",
    know_preview_btn: "预览",
    know_truncated: "(已截断至 5000 字符)",
    know_refresh_btn: "刷新文档缓存", know_refreshing: "刷新中...",
    backup_title: "备份管理",
    backup_refresh: "刷新列表",
    backup_clear_all: "🗑 清空全部",
    backup_mode_label: "恢复模式：",
    backup_incremental: "增量（跳过已有）", backup_overwrite: "覆盖（更新已有）",
    backup_incremental_hint: "已有同名自动化将跳过",
    backup_overwrite_hint: "已有同名自动化将被覆盖更新",
    backup_empty: "暂无备份记录",
    backup_restore_btn: "恢复",
    backup_meta: "{count} 条 · {size}KB",
    log_title: "运行日志",
    log_clear: "清空",
    log_waiting: "等待操作...",
    copy_btn: "复制",
    confirm_del_inaccessible: "确定要清除全部 {n} 条不可访问的 YAML 型自动化吗？\n\n注意：YAML 型自动化无法通过 API 删除，需在 HA 的 automations.yaml 文件中手动删除对应条目。",
    confirm_restore: "确认以【{mode}】模式恢复此备份？\n\n{file}",
    confirm_clear_backups: "确认清空全部备份？不可恢复！",
    confirm_backup_sel: "备份选中的 {n} 条自动化？",
    confirm_del_sel: "确定删除选中的 {n} 条自动化？此操作不可撤销。",
    confirm_no_approved: "没有批准的条目",
    toast_config_saved: "配置已保存",
    toast_optimize_saved: "优化保存成功",
    toast_restore_done: "恢复完成",
    toast_cleared_n: "已清除 {n} 条不可访问的自动化",
    toast_backed_up: "已备份 {n} 条 → {file}",
    toast_deleted_n: "已删除 {n} 条",
    toast_copied: "已复制到剪贴板",
    toast_docs_refreshed: "刷新完成：{keys}",
    toast_no_sel: "没有选中的自动化可以保存",
    toast_save_fail_yaml: "无法保存：YAML 校验失败",
    toast_clear_partial_fail: "清除完成，{n} 条异常失败（见日志）",
    toast_clear_yaml_warn: "已清除 {del} 条；{warn} 条需手动删除（见日志）",
    toast_del_partial_fail: "已删除 {ok} 条，{fail} 条失败（见日志）",
    toast_exec_done: "执行完成：{ok} 成功，{fail} 失败",
    toast_backups_cleared: "已删除 {n} 个备份文件",
    toast_save_fail: "保存失败：{msg}",
    toast_clear_fail: "清除失败：{msg}",
    toast_backup_fail: "备份失败：{msg}",
    toast_del_fail: "删除失败：{msg}",
    toast_restore_fail: "恢复失败：{msg}",
    toast_refresh_fail: "刷新失败：{msg}",
    toast_preview_fail: "预览失败：{msg}",
    toast_clear_all_fail: "清空失败：{msg}",
    toast_copy_fail: "复制失败（请手动选择复制）",
    log_aborted: "[ERROR] 操作已被用户终止",
    log_no_sel: "[ERROR] 请至少选择一条自动化",
    log_analyze_done: "[OK] 分析完成",
    log_analyze_fail: "[ERROR] 分析失败：{msg}",
    log_generate_fail: "[ERROR] 生成失败：{msg}",
    log_refine_fail: "[ERROR] 修改失败：{msg}",
    log_save_fail: "[ERROR] 保存失败：{msg}",
    log_exec_fail: "[ERROR] 执行失败：{msg}",
    log_refresh_fail: "[ERROR] 刷新失败：{msg}",
    log_del_inaccessible_summary: "[INFO] 清除不可访问：扫描 {scanned} 条，API删除 {api} 条，注册表清除 {ghost} 条，失败 {fail} 条",
    log_ghost_cleared: "[OK] 幽灵实体已清除：{alias}",
    log_yaml_manual: "[WARN] {n} 条无法自动删除，需在 automations.yaml 中手动删除：",
    log_del_fail_id: "[ERROR] 删除失败 id={id} ({alias})：{error}",
    log_del_inaccessible_fail: "[ERROR] 清除不可访问失败：{msg}",
    log_batch_del_summary: "[INFO] 批量删除：成功 {ok} 条，失败 {fail} 条",
    log_batch_del_fail_id: "[ERROR] 删除失败 id={id}：{error}",
    log_batch_del_fail: "[ERROR] 批量删除失败：{msg}",
    log_restore_fail: "[ERROR] 恢复失败：{msg}",
  },
  en: {
    tab_create: "✨ Create", tab_optimize: "🔧 Optimize",
    tab_consolidate: "🔗 Consolidate", tab_manage: "📋 Manage",
    tab_config: "⚙ Config", tab_knowledge: "📚 Knowledge/Backup",
    theme_auto: "Auto", theme_dark: "Dark", theme_light: "Light",
    theme_toggle: "Toggle theme (current: {label})",
    abort_title: "Abort current operation",
    create_title: "Describe your automation",
    create_placeholder: "e.g. Turn off all living room lights at 10 PM; Turn off AC and fan when nobody is home",
    create_btn: "▶ Generate", create_btn_loading: "Generating...",
    create_sel_all: "☑ Select All", create_sel_none: "☐ Deselect All",
    create_save_sel: "Save Selected ({n})",
    create_saving: "Saved: {n}",
    create_has_issues: "⚠ Issues", create_ok: "✓ OK",
    create_refine_hide: "▲ Hide Refine", create_refine_show: "✏ Refine",
    create_refine_placeholder: "Enter feedback for AI to regenerate...",
    create_refine_btn: "Regenerate",
    create_no_yaml: "AI failed to generate valid automation config",
    create_expand_hint: "▼ Expand ({n} available)",
    opt_select_title: "Select automation to optimize",
    opt_refresh: "🔄 Refresh",
    opt_loading: "Loading automations...",
    opt_load_fail: "Load failed, click \"Refresh\" to retry",
    opt_empty: "No optimizable automations (storage type)",
    opt_placeholder: "— Select —",
    opt_analyze_btn: "Analyze ▶", opt_analyze_loading: "Analyzing...",
    opt_step1_title: "Step 1 — Analysis Report",
    opt_issues_title: "⚠ Issues found:", opt_sugg_title: "✦ Suggestions:",
    opt_direction_label: "Follow-up / Additional direction (optional)",
    opt_direction_placeholder: "e.g. Focus on adding nighttime conditions, extend to other rooms...",
    opt_reanalyze: "🔄 Re-analyze",
    opt_generate_btn: "Generate Optimized ▶", opt_generate_loading: "Generating...",
    opt_step2_title: "Step 2 — Optimized Result",
    opt_diff_side: "⇔ Side by side", opt_diff_inline: "≡ Inline diff",
    opt_diff_before: "Before", opt_diff_after: "After",
    opt_diff_inline_label: "Inline diff (Before → After)",
    opt_refine_placeholder: "Enter refinement feedback...",
    opt_refine_btn: "Regenerate",
    opt_save_btn: "💾 Save Optimized",
    cons_title: "Consolidate Automations",
    cons_refresh: "🔄 Refresh",
    cons_desc: "Analyze all automations, identify duplicates and issues, consolidate by scenario.",
    cons_loading: "Loading automations...",
    cons_load_fail: "Load failed, click \"Refresh\" to retry",
    cons_empty: "No consolidatable automations (storage type)",
    cons_select_label: "Select automations to consolidate ({sel}/{total} selected):",
    cons_inaccessible: "⚠ Inaccessible",
    cons_sel_all: "☑ Select All", cons_sel_none: "☐ Deselect All",
    cons_del_btn: "🗑 Clear Inaccessible ({n})",
    cons_deleting: "Clearing...",
    cons_analyze_btn: "▶ Analyze ({n})", cons_analyze_loading: "Analyzing...",
    cons_plan_title: "Consolidation Plan",
    cons_summary: "Merge {merge} · Fix {fix} · Keep {ok}",
    cons_batch_selected: "{n} selected",
    cons_batch_all: "☑ Select All", cons_batch_none: "☐ Deselect All",
    cons_batch_exec: "▶ Execute ({n})",
    cons_merge_tag: "Merge", cons_fix_tag: "Fix",
    cons_scenario: "Scenario: {name}",
    cons_originals: "Original automations ({n} total, will be replaced):",
    cons_no_original: "(Original config unavailable)",
    cons_merged_label: "Merged:",
    cons_refine_placeholder: "Enter feedback...",
    cons_approve: "✓ Approve", cons_skip: "✗ Skip",
    cons_issue_prefix: "Issue: {issue}",
    cons_fix_before: "Original", cons_fix_after: "Fixed",
    cons_ok_items: "✓ {n} unchanged: {list}",
    cons_exec_all: "⚡ Execute All Approved ({n})",
    cons_refine_btn: "Regenerate",
    manage_loading: "Loading...",
    manage_not_loaded: "Automations not loaded",
    manage_load_btn: "🔄 Load List",
    manage_title: "Automation Manager",
    manage_refresh: "🔄 Refresh",
    manage_empty: "No automations",
    manage_sel_all: "Select All", manage_sel_none: "Deselect All",
    manage_selected: "{n} selected",
    manage_backup_btn: "💾 Backup ({n})",
    manage_delete_btn: "🗑 Delete ({n})",
    manage_inaccessible: "Inaccessible",
    config_title: "LLM API Configuration",
    config_loading: "Loading config...",
    config_model: "Model name",
    config_filter_title: "Entity Filters (optional)",
    config_filter_note: "Note: Filters only affect the entity list sent to LLM, not the automation scope.",
    config_extra_domains: "Extra visible domains (comma-separated, e.g. notify,remote)",
    config_hidden_domains: "Hidden domains (type domain + enter)",
    config_hidden_placeholder: "weather,person (comma-separated)",
    config_area_filter: "Show only areas (entity list limited to selected areas)",
    config_integ_filter: "Show only integration",
    config_label_filter: "Show only labels",
    config_advanced: "Advanced Options",
    config_log_prompt: "Print LLM prompt in log panel (shown in purple)",
    config_use_docs: "Inject HA official docs into prompt (locally cached, auto-updated every 7 days)",
    config_save_btn: "💾 Save Config",
    config_saving: "⏳ Saving...",
    config_base_url: "Base URL (required for openai_compatible, e.g. https://api.xxx.com/v1)",
    know_title: "Knowledge Docs",
    know_preview_btn: "Preview",
    know_truncated: "(truncated to 5000 chars)",
    know_refresh_btn: "Refresh Doc Cache", know_refreshing: "Refreshing...",
    backup_title: "Backup Manager",
    backup_refresh: "Refresh",
    backup_clear_all: "🗑 Clear All",
    backup_mode_label: "Restore mode:",
    backup_incremental: "Incremental (skip existing)", backup_overwrite: "Overwrite (update existing)",
    backup_incremental_hint: "Existing automations with same name will be skipped",
    backup_overwrite_hint: "Existing automations with same name will be overwritten",
    backup_empty: "No backups",
    backup_restore_btn: "Restore",
    backup_meta: "{count} · {size} KB",
    log_title: "Run Log",
    log_clear: "Clear",
    log_waiting: "Waiting for operation...",
    copy_btn: "Copy",
    confirm_del_inaccessible: "Clear all {n} inaccessible YAML automations?\n\nNote: YAML automations cannot be deleted via API; you must manually remove them from automations.yaml.",
    confirm_restore: "Restore this backup in [{mode}] mode?\n\n{file}",
    confirm_clear_backups: "Clear all backups? This cannot be undone!",
    confirm_backup_sel: "Backup selected {n} automations?",
    confirm_del_sel: "Delete selected {n} automations? This cannot be undone.",
    confirm_no_approved: "No approved items",
    toast_config_saved: "Config saved",
    toast_optimize_saved: "Optimization saved",
    toast_restore_done: "Restore complete",
    toast_cleared_n: "Cleared {n} inaccessible automations",
    toast_backed_up: "Backed up {n} → {file}",
    toast_deleted_n: "Deleted {n}",
    toast_copied: "Copied to clipboard",
    toast_docs_refreshed: "Refreshed: {keys}",
    toast_no_sel: "No automations selected",
    toast_save_fail_yaml: "Cannot save: YAML validation failed",
    toast_clear_partial_fail: "Clear done, {n} failed (see log)",
    toast_clear_yaml_warn: "Cleared {del}; {warn} need manual deletion (see log)",
    toast_del_partial_fail: "Deleted {ok}, {fail} failed (see log)",
    toast_exec_done: "Done: {ok} succeeded, {fail} failed",
    toast_backups_cleared: "Deleted {n} backup files",
    toast_save_fail: "Save failed: {msg}",
    toast_clear_fail: "Clear failed: {msg}",
    toast_backup_fail: "Backup failed: {msg}",
    toast_del_fail: "Delete failed: {msg}",
    toast_restore_fail: "Restore failed: {msg}",
    toast_refresh_fail: "Refresh failed: {msg}",
    toast_preview_fail: "Preview failed: {msg}",
    toast_clear_all_fail: "Clear all failed: {msg}",
    toast_copy_fail: "Copy failed (please select and copy manually)",
    log_aborted: "[ERROR] Operation aborted by user",
    log_no_sel: "[ERROR] Please select at least one automation",
    log_analyze_done: "[OK] Analysis complete",
    log_analyze_fail: "[ERROR] Analysis failed: {msg}",
    log_generate_fail: "[ERROR] Generation failed: {msg}",
    log_refine_fail: "[ERROR] Refinement failed: {msg}",
    log_save_fail: "[ERROR] Save failed: {msg}",
    log_exec_fail: "[ERROR] Execution failed: {msg}",
    log_refresh_fail: "[ERROR] Refresh failed: {msg}",
    log_del_inaccessible_summary: "[INFO] Clear inaccessible: scanned {scanned}, API deleted {api}, registry cleared {ghost}, failed {fail}",
    log_ghost_cleared: "[OK] Ghost entity cleared: {alias}",
    log_yaml_manual: "[WARN] {n} cannot be auto-deleted, manually remove from automations.yaml:",
    log_del_fail_id: "[ERROR] Delete failed id={id} ({alias}): {error}",
    log_del_inaccessible_fail: "[ERROR] Clear inaccessible failed: {msg}",
    log_batch_del_summary: "[INFO] Batch delete: {ok} succeeded, {fail} failed",
    log_batch_del_fail_id: "[ERROR] Delete failed id={id}: {error}",
    log_batch_del_fail: "[ERROR] Batch delete failed: {msg}",
    log_restore_fail: "[ERROR] Restore failed: {msg}",
  }
};

/** Translate a key with optional variable interpolation {varName} */
function _i18n(lang, key, vars = {}) {
  let str = (TRANSLATIONS[lang] || TRANSLATIONS.zh)[key];
  if (str === undefined) str = TRANSLATIONS.zh[key] || key;
  for (const [k, v] of Object.entries(vars)) {
    str = str.replace(new RegExp(`\\{${k}\\}`, "g"), v);
  }
  return str;
}

// ============================================================
// Utilities
// ============================================================
function genSessionId() {
  return `ses_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderDiff(before, after) {
  if (!before) return `<pre class="yaml-block">${escHtml(after)}</pre>`;
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

// ============================================================
// Styles
// ============================================================
const STYLES = `
  :host {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: var(--primary-background-color, #0f1117);
    color: var(--primary-text-color, #e5e7eb);
    font-family: var(--paper-font-body1_-_font-family, sans-serif);
    font-size: 14px;
  }
  .header {
    display: flex;
    align-items: center;
    padding: 14px 24px;
    background: var(--app-header-background-color, #1a1f2e);
    border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.07));
    flex-shrink: 0;
    gap: 12px;
  }
  .header h1 {
    margin: 0;
    font-size: 17px;
    font-weight: 700;
    flex: 1;
    color: var(--app-header-text-color, #ffffff);
    letter-spacing: 0.02em;
  }
  .tabs {
    display: flex;
    gap: 0;
    padding: 0 24px;
    background: var(--app-header-background-color, #1a1f2e);
    border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.07));
    flex-shrink: 0;
    overflow-x: auto;
  }
  .tab {
    padding: 11px 18px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    color: var(--app-header-text-color, #e5e7eb);
    opacity: 0.65;
    font-weight: 500;
    font-size: 13px;
    transition: color 0.15s, opacity 0.15s;
    white-space: nowrap;
    position: relative;
  }
  .tab:hover { opacity: 0.9; }
  .tab.active {
    color: var(--app-header-text-color, #818cf8);
    border-bottom-color: var(--app-header-text-color, #818cf8);
    opacity: 1;
  }
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    display: flex;
    gap: 20px;
  }
  .main-area { flex: 1; min-width: 0; }
  .log-area {
    width: 290px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }
  @media (max-width: 900px) {
    .content { flex-direction: column; }
    .log-area { width: 100%; }
  }
  .card {
    background: var(--card-background-color, #1e2433);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border: 1px solid var(--divider-color, rgba(255,255,255,0.06));
  }
  .card-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--secondary-text-color, #9ca3af);
    margin-bottom: 14px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  textarea, input[type=text], input[type=password], input[type=number], select {
    width: 100%;
    background: linear-gradient(135deg,
      rgba(129, 140, 248, 0.07) 0%,
      rgba(255, 255, 255, 0.02) 50%,
      rgba(129, 140, 248, 0.05) 100%);
    border: 1px solid var(--divider-color, rgba(255,255,255,0.12));
    border-radius: 8px;
    padding: 9px 12px;
    color: var(--primary-text-color, #e5e7eb);
    font-family: inherit;
    font-size: 14px;
    resize: vertical;
    box-sizing: border-box;
    outline: none;
    transition: border-color 0.3s ease, box-shadow 0.3s ease, background 0.3s ease;
  }
  textarea:focus, input:focus, select:focus {
    border-color: rgba(129, 140, 248, 0.55);
    box-shadow: 0 0 0 2px rgba(129,140,248,0.12), 0 4px 16px rgba(129,140,248,0.12);
    background: linear-gradient(135deg,
      rgba(129, 140, 248, 0.12) 0%,
      rgba(255, 255, 255, 0.04) 50%,
      rgba(129, 140, 248, 0.10) 100%);
  }
  textarea { min-height: 80px; }
  :host([data-theme="light"]) textarea,
  :host([data-theme="light"]) input[type=text],
  :host([data-theme="light"]) input[type=password],
  :host([data-theme="light"]) input[type=number],
  :host([data-theme="light"]) select {
    background: rgba(255, 255, 255, 0.75);
    box-shadow: 0 2px 8px rgba(0,0,0,0.05), inset 0 1px 2px rgba(255,255,255,0.9);
  }
  :host([data-theme="light"]) textarea:focus,
  :host([data-theme="light"]) input:focus,
  :host([data-theme="light"]) select:focus {
    border-color: rgba(99, 102, 241, 0.5);
    box-shadow: 0 0 0 2px rgba(99,102,241,0.12), 0 4px 16px rgba(99,102,241,0.10);
    background: rgba(255, 255, 255, 0.92);
  }
  /* ===== 液态荡漾主输入框 ===== */
  .input-wrap {
    position: relative;
    border-radius: 12px;
  }
  .input-wrap::before {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: 13px;
    background: linear-gradient(90deg, #d65f00, #ffb800, #8a2be2, #818cf8, #ffb800, #d45e00);
    background-size: 300% 300%;
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    mask-composite: exclude;
    padding: 1.5px;
    animation: inputGradientFlow 4s linear infinite;
    opacity: 0.2;
    transition: opacity 0.4s ease-in-out;
    pointer-events: none;
    z-index: 3;
  }
  .input-wrap::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 0;
    background: linear-gradient(to top, rgba(129, 140, 248, 0.35), transparent 80%);
    border-radius: 12px;
    opacity: 0;
    z-index: 1;
    transform-origin: bottom;
    pointer-events: none;
    will-change: height, opacity, transform;
  }
  .input-wrap:focus-within::before { opacity: 1; }
  .input-wrap:focus-within {
    box-shadow: 0 0 0 3px rgba(129,140,248,0.18), 0 6px 24px rgba(129,140,248,0.15);
  }
  :host([data-theme="light"]) .input-wrap:focus-within {
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15), 0 6px 24px rgba(99,102,241,0.10);
  }
  .input-wrap:focus-within::after {
    animation: inputLiquidRipple 1.5s cubic-bezier(0.33, 1, 0.68, 1) forwards;
  }
  .input-wrap textarea {
    border-radius: 12px;
    border: none;
    position: relative;
    z-index: 2;
    background: linear-gradient(135deg,
      rgba(129, 140, 248, 0.10) 0%,
      rgba(255, 255, 255, 0.03) 50%,
      rgba(129, 140, 248, 0.08) 100%);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15), inset 0 2px 4px rgba(255,255,255,0.08);
    transition: box-shadow 0.3s ease, background 0.3s ease;
  }
  .input-wrap textarea:focus {
    box-shadow: 0 8px 28px rgba(129,140,248,0.2),
      inset 0 4px 8px rgba(255,255,255,0.12),
      inset 0 -4px 8px rgba(0,0,0,0.1);
    background: linear-gradient(135deg,
      rgba(129, 140, 248, 0.15) 0%,
      rgba(255, 255, 255, 0.05) 50%,
      rgba(129, 140, 248, 0.12) 100%);
  }
  :host([data-theme="light"]) .input-wrap::before {
    background: linear-gradient(90deg, #d65f00, #ffb800, #6366f1, #818cf8, #ffb800, #d45e00);
    background-size: 300% 300%;
  }
  :host([data-theme="light"]) .input-wrap::after {
    background: linear-gradient(to top, rgba(99, 102, 241, 0.28), transparent 80%);
  }
  :host([data-theme="light"]) .input-wrap textarea {
    background: linear-gradient(135deg,
      rgba(99, 102, 241, 0.07) 0%, rgba(255,255,255,0.93) 50%, rgba(99, 102, 241, 0.05) 100%);
    box-shadow: 0 4px 20px rgba(0,0,0,0.08), inset 0 2px 4px rgba(255,255,255,0.95);
  }
  :host([data-theme="light"]) .input-wrap textarea:focus {
    box-shadow: 0 8px 28px rgba(99,102,241,0.15), inset 0 4px 8px rgba(255,255,255,0.98);
  }
  @keyframes inputGradientFlow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  @keyframes inputBlinking {
    0%   { filter: drop-shadow(0px 0px 3px rgba(129,140,248,0.6)); }
    25%  { filter: drop-shadow(0px 0px 6px rgba(129,140,248,0.7)); }
    50%  { filter: drop-shadow(0px 0px 10px rgba(255,165,0,0.6)); }
    75%  { filter: drop-shadow(0px 0px 6px rgba(129,140,248,0.7)); }
    100% { filter: drop-shadow(0px 0px 3px rgba(129,140,248,0.6)); }
  }
  @keyframes inputLiquidRipple {
    0%   { height: 10%; opacity: 0; transform: scaleY(0.5); }
    30%  { height: 50%; opacity: 0.9; transform: scaleY(1); }
    70%  { height: 75%; opacity: 0.4; }
    100% { height: 100%; opacity: 0; transform: scaleY(1.1); }
  }
  /* 触摸设备（手机/平板）键盘收起防护
   *
   * 只禁用"focus 瞬间触发的 CSS 变化"——这才是让 WebKit 收起键盘的根因。
   * 流光渐变动画在 focus 前已在运行，focus 时不触发任何变化，可以安全保留。
   */
  @media (hover: none) and (pointer: coarse) {
    /* ── 流光渐变边框：保留，只把频率降低一点省性能 ── */
    .input-wrap::before {
      animation-duration: 6s;
      opacity: 0.45;      /* 常驻稍亮，不靠 focus 才能看见 */
      transition: none;   /* 无过渡 → opacity 变化为单帧，安全 */
    }
    .input-wrap:focus-within::before {
      opacity: 1;         /* focus 时全亮（瞬时，无 transition） */
    }
    /* ── 液态荡漾高光：从 focus 时启动 → 危险，保持禁用 ── */
    .input-wrap::after { will-change: auto; }
    .input-wrap:focus-within::after { animation: none; }
    /* ── input/textarea 的 transition 全禁：防 focus 渐变触发合成层重建 ── */
    textarea, input[type=text], input[type=password], input[type=number], select {
      transition: none !important;
    }
    /* ── focus 时新增的 box-shadow 全禁：这才是键盘收起的直接原因 ── */
    textarea:focus, input:focus, select:focus { box-shadow: none !important; }
    .input-wrap:focus-within { box-shadow: none !important; }
    .input-wrap textarea:focus { box-shadow: none !important; }
    /* ── 补偿：给容器加常驻微光（不依赖 focus，不触发变化） ── */
    .input-wrap {
      box-shadow: 0 0 0 1px rgba(129,140,248,0.18), 0 2px 14px rgba(129,140,248,0.10);
    }
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s;
  }
  .btn:disabled { opacity: 0.45; cursor: not-allowed; }
  .btn-primary {
    background: #818cf8;
    color: white;
    box-shadow: 0 2px 8px rgba(129,140,248,0.25);
  }
  .btn-primary:hover:not(:disabled) {
    filter: brightness(1.12);
    box-shadow: 0 4px 14px rgba(129,140,248,0.35);
  }
  .btn-success { background: #059669; color: white; box-shadow: 0 2px 8px rgba(5,150,105,0.2); }
  .btn-success:hover:not(:disabled) { filter: brightness(1.1); box-shadow: 0 4px 12px rgba(5,150,105,0.3); }
  .btn-danger { background: #dc2626; color: white; }
  .btn-danger:hover:not(:disabled) { filter: brightness(1.1); }
  .btn-secondary {
    background: rgba(255,255,255,0.08);
    color: var(--primary-text-color, #e5e7eb);
  }
  .btn-secondary:hover:not(:disabled) { background: rgba(255,255,255,0.14); }
  .btn-sm { padding: 5px 10px; font-size: 12px; }
  .automation-card {
    background: var(--secondary-background-color, rgba(0,0,0,0.2));
    border-radius: 10px;
    border: 1px solid var(--divider-color, rgba(255,255,255,0.07));
    margin-bottom: 10px;
    overflow: hidden;
    border-left: 3px solid transparent;
  }
  .automation-card.approved { border-left-color: #059669; border-color: rgba(5,150,105,0.4); }
  .automation-card.skipped { border-left-color: #6b7280; opacity: 0.55; }
  .automation-card.warning { border-left-color: #d97706; border-color: rgba(217,119,6,0.35); }
  .automation-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 11px 14px;
    background: rgba(128,128,128,0.05);
    cursor: pointer;
    user-select: none;
  }
  .automation-header:hover { background: rgba(128,128,128,0.1); }
  .auto-title { flex: 1; font-weight: 500; font-size: 13px; }
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
  .tag-info { background: rgba(129,140,248,0.15); color: #818cf8; }
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
    border: 1px solid rgba(255,255,255,0.07);
    max-height: 380px;
    overflow-y: auto;
    position: relative;
  }
  .yaml-wrapper { position: relative; }
  .yaml-copy-btn {
    position: absolute;
    top: 6px;
    right: 6px;
    padding: 3px 8px;
    font-size: 11px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px;
    color: #9ca3af;
    cursor: pointer;
    transition: all 0.15s;
  }
  .yaml-copy-btn:hover { background: rgba(255,255,255,0.15); color: #fff; }
  .auto-body { padding: 14px 16px; }
  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
  .refine-area { margin-top: 10px; display: none; }
  .load-hint {
    padding: 20px 0;
    text-align: center;
    color: var(--secondary-text-color, #9ca3af);
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .refine-area.visible { display: block; }
  .refine-input { display: flex; gap: 8px; align-items: flex-start; }
  .refine-input textarea { min-height: 56px; flex: 1; }
  .refine-input .input-wrap { flex: 1; }
  .refine-input .input-wrap textarea { min-height: 56px; flex: none; width: 100%; }
  .log-panel {
    background: var(--card-background-color, #1a1f2e);
    border-radius: 12px;
    border: 1px solid var(--divider-color, rgba(255,255,255,0.06));
    display: flex;
    flex-direction: column;
    max-height: 520px;
    position: sticky;
    top: 0;
  }
  .log-title {
    padding: 11px 14px;
    font-weight: 600;
    font-size: 12px;
    color: var(--secondary-text-color, #9ca3af);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    justify-content: space-between;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .log-entries {
    flex: 1;
    overflow-y: auto;
    padding: 10px 12px;
    font-family: monospace;
    font-size: 11.5px;
    line-height: 1.7;
  }
  .log-entry { color: #6b7280; word-break: break-all; }
  .log-error   { color: #f87171; }
  .log-success { color: #4ade80; }
  .log-prompt  { color: #a78bfa; font-size: 11px; opacity: 0.8; }
  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.2);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .form-row { margin-bottom: 12px; }
  .form-label { display: block; margin-bottom: 5px; font-size: 12px; color: var(--secondary-text-color, #9ca3af); }
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  @media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
  .config-section {
    border-top: 1px solid rgba(255,255,255,0.07);
    padding-top: 14px;
    margin-top: 14px;
  }
  .config-section-title {
    font-size: 11px;
    font-weight: 700;
    color: #818cf8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
  }
  .pw-wrapper { position: relative; }
  .pw-toggle {
    position: absolute; right: 10px; top: 50%;
    transform: translateY(-50%);
    cursor: pointer; color: #9ca3af; font-size: 14px;
    background: none; border: none; padding: 2px;
  }
  .tag-input-wrapper {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    background: transparent;
    border: 1px solid var(--divider-color, rgba(255,255,255,0.1));
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 40px;
    cursor: text;
    transition: border-color 0.15s;
  }
  .tag-input-wrapper:focus-within { border-color: #818cf8; box-shadow: 0 0 0 2px rgba(129,140,248,0.15); }
  .tag-chip {
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(129,140,248,0.18); color: #818cf8;
    border-radius: 4px; padding: 2px 7px; font-size: 12px;
  }
  .tag-chip-del { cursor: pointer; font-size: 13px; line-height: 1; }
  .tag-chip-del:hover { color: #f87171; }
  .tag-bare-input {
    background: transparent; border: none; outline: none;
    color: var(--primary-text-color, #e5e7eb); font-size: 13px; padding: 2px 4px; min-width: 80px; flex: 1;
  }
  .multi-select-dropdown {
    background: var(--card-background-color, #1a1f2e);
    border: 1px solid var(--divider-color, rgba(255,255,255,0.12));
    border-radius: 8px;
    padding: 6px 0;
    max-height: 200px;
    overflow-y: auto;
    display: none;
  }
  .multi-select-dropdown.open { display: block; }
  .multi-select-item {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 12px; cursor: pointer; font-size: 13px;
  }
  .multi-select-item:hover { background: rgba(255,255,255,0.05); }
  .dropdown-toggle-btn {
    width: 100%;
    text-align: left;
    background: transparent;
    border: 1px solid var(--divider-color, rgba(255,255,255,0.1));
    border-radius: 8px;
    padding: 7px 12px;
    color: var(--secondary-text-color, #9ca3af);
    cursor: pointer;
    font-size: 12px;
  }
  .dropdown-toggle-btn:hover { border-color: #818cf8; }
  .analysis-box {
    background: rgba(129,140,248,0.07);
    border: 1px solid rgba(129,140,248,0.2);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }
  .analysis-intent {
    font-size: 15px;
    font-weight: 700;
    color: #c7d2fe;
    padding: 6px 12px;
    background: rgba(129,140,248,0.1);
    border-radius: 6px;
    margin-bottom: 12px;
  }
  .analysis-issues li { color: #f87171; }
  .analysis-suggs li { color: #6ee7b7; }
  .analysis-list { margin: 4px 0; padding-left: 20px; }
  .analysis-list li { margin-bottom: 4px; font-size: 13px; }
  .diff-container {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;
  }
  @media (max-width: 700px) { .diff-container { grid-template-columns: 1fr; } }
  .diff-label { font-size: 11px; font-weight: 600; color: #9ca3af; margin-bottom: 4px; }
  .summary-badges { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
  .badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600;
  }
  .badge-blue { background: rgba(96,165,250,0.15); color: #60a5fa; }
  .badge-green { background: rgba(74,222,128,0.12); color: #4ade80; }
  .badge-orange { background: rgba(251,191,36,0.12); color: #fbbf24; }
  .badge-purple { background: rgba(167,139,250,0.15); color: #a78bfa; }
  .empty-state {
    text-align: center; padding: 50px 20px;
    color: var(--secondary-text-color, #9ca3af);
  }
  .error-box {
    background: rgba(220,38,38,0.09);
    border: 1px solid rgba(220,38,38,0.25);
    border-radius: 8px;
    padding: 10px 14px;
    color: #f87171;
    margin-bottom: 12px;
    font-size: 13px;
  }
  .success-box {
    background: rgba(5,150,105,0.09);
    border: 1px solid rgba(5,150,105,0.25);
    border-radius: 8px;
    padding: 10px 14px;
    color: #4ade80;
    margin-bottom: 12px;
    font-size: 13px;
  }
  .backup-list { list-style: none; margin: 0; padding: 0; }
  .backup-item {
    display: flex; align-items: center; padding: 9px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05); gap: 10px;
  }
  .backup-item:last-child { border-bottom: none; }
  .backup-info { flex: 1; }
  .backup-name { font-family: monospace; font-size: 12px; }
  .backup-meta { font-size: 11px; color: #9ca3af; margin-top: 2px; }
  .doc-list { list-style: none; margin: 0; padding: 0; }
  .doc-item {
    display: flex; align-items: center; padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05); gap: 10px;
  }
  .doc-item:last-child { border-bottom: none; }
  .doc-key { flex: 1; font-family: monospace; font-size: 12px; color: #818cf8; }
  .doc-preview-area {
    background: #0d1117; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px; padding: 12px; font-family: monospace;
    font-size: 11px; color: #c9d1d9; white-space: pre-wrap;
    overflow-y: auto; max-height: 320px; margin-top: 10px;
    display: none;
  }
  .doc-preview-area.visible { display: block; }
  .toast-container {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    z-index: 9999; display: flex; flex-direction: column; gap: 8px; align-items: center;
  }
  .toast {
    background: var(--card-background-color, #1e2433);
    border: 1px solid var(--divider-color, rgba(255,255,255,0.12));
    border-radius: 8px; padding: 10px 20px;
    color: var(--primary-text-color, #e5e7eb);
    font-size: 13px; max-width: 400px; text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    animation: toast-in 0.2s ease;
  }
  .toast.success { border-color: #059669; color: #4ade80; }
  .toast.error { border-color: #dc2626; color: #f87171; }
  .toast.warn { border-color: #d97706; color: #fbbf24; }
  @keyframes toast-in { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
  .checkbox-row {
    display: flex; align-items: center; gap: 8px; cursor: pointer;
    padding: 4px 0;
  }
  .checkbox-row input[type=checkbox] { width: auto; }
  .icon-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 8px;
    font-size: 18px;
    color: var(--app-header-text-color, #e5e7eb);
    opacity: 0.8;
    border-radius: 4px;
  }
  .icon-btn:hover { opacity: 1; background: rgba(255,255,255,0.1); }
  .abort-btn { color: #f87171; }
  /* 主题切换按钮三态 */
  .theme-btn { display: inline-flex; align-items: center; gap: 4px; font-size: 14px; padding: 4px 9px; border-radius: 6px; border: 1px solid transparent; }
  .theme-label { font-size: 11px; font-weight: 500; letter-spacing: 0; opacity: 1; }
  .theme-auto  { border-color: rgba(255,255,255,0.22); }
  .theme-dark  { background: rgba(99,102,241,0.22); border-color: rgba(99,102,241,0.55); }
  .theme-light { background: rgba(251,191,36,0.2);  border-color: rgba(251,191,36,0.6); }
  .hint-text { font-size: 12px; color: var(--secondary-text-color, #9ca3af); margin: 4px 0 8px; }
  .consolidate-select-panel { padding: 12px; }
  .panel-label { font-size: 13px; color: var(--secondary-text-color, #9ca3af); margin-bottom: 8px; }
  .automation-checklist { max-height: 280px; overflow-y: auto; border: 1px solid var(--divider-color, rgba(255,255,255,0.08)); border-radius: 6px; padding: 4px; margin-bottom: 10px; }
  .check-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 4px; cursor: pointer; }
  .check-item:hover { background: rgba(255,255,255,0.05); }
  .check-item-disabled { opacity: 0.4; cursor: not-allowed; }
  .consolidate-check-item { accent-color: #818cf8; width: 15px; height: 15px; cursor: pointer; flex-shrink: 0; }
  .check-label { flex: 1; font-size: 13px; }
  .check-warning { font-size: 11px; color: #f87171; }
  .checklist-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .btn-sm-plain { padding: 4px 10px; font-size: 12px; border-radius: 4px; border: 1px solid var(--divider-color, rgba(255,255,255,0.15)); background: transparent; color: var(--primary-text-color, #e5e7eb); cursor: pointer; }
  .btn-sm-plain:hover { background: rgba(255,255,255,0.08); }
  .btn-sm.active { background: rgba(99,102,241,0.2); border-color: #6366f1; color: #818cf8; }
  .diff-mode-btns { display: flex; gap: 6px; margin-bottom: 8px; }
  .consolidate-batch-bar {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    padding: 8px 12px; border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.08));
    margin-bottom: 8px; background: rgba(255,255,255,0.02); border-radius: 6px 6px 0 0;
  }
  .consolidate-batch-bar .hint-text { font-size: 12px; color: var(--secondary-text-color, #9ca3af); flex: 1; }
  .cons-item-cb { width: 15px; height: 15px; cursor: pointer; flex-shrink: 0; accent-color: #818cf8; }
  :host([data-theme="dark"]) {
    --primary-background-color: #0f1117;
    --card-background-color: #1e2433;
    --app-header-background-color: #1a1f2e;
    --app-header-text-color: #e5e7eb;
    --primary-text-color: #e5e7eb;
    --secondary-text-color: #9ca3af;
    --divider-color: rgba(255,255,255,0.08);
  }
  :host([data-theme="light"]) {
    --primary-background-color: #f3f4f6;
    --card-background-color: #ffffff;
    --app-header-background-color: #6366f1;
    --app-header-text-color: #ffffff;
    --primary-text-color: #111827;
    --secondary-text-color: #6b7280;
    --divider-color: rgba(0,0,0,0.1);
  }
`;

// ============================================================
// Main Panel Component
// ============================================================
class HaLlmAutomationPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    try {
      this._initState();
      this._render();
    } catch (e) {
      this._renderFatalError(e, "constructor");
    }
    // Do NOT call _loadAutomations() here — wait for hass to be injected
  }

  _initState() {
    this._tab = "create";
    this._logs = [];  // [{text, cls}]
    this._loading = false;
    this._sessionId = null;
    this._logUnsub = null;

    // Create state
    this._createResult = null;
    this._createSystemPrompt = "";
    this._createExpanded = new Set();       // default collapsed
    this._createRefineVisible = new Set();  // refine area visibility
    this._createChecked = new Set();        // checkbox selection

    // All automations (used by optimize + consolidate pre-selection)
    this._automations = null;       // null=未加载，[]+=已加载
    this._automationsLoading = false;

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
    this._delInaccessibleRunning = false;
    this._consolidateExpandedYaml = {};
    this._consolidateSelectedIds = null; // null=未初始化，Set=已选

    // Manage tab state
    this._manageChecked = new Set();

    // Knowledge/Backup state: restore mode
    this._restoreMode = "incremental"; // "incremental" | "overwrite"

    // Config state
    this._configData = {};
    this._configLoaded = false;
    this._showApiKey = false;
    this._areas = [];
    this._labels = [];
    this._integrations = [];
    this._areaDropOpen = false;
    this._labelDropOpen = false;
    this._integDropOpen = false;

    // Knowledge/Backup state
    this._backups = [];
    this._docPreview = {};  // {key: content}

    // Misc state
    this._abortSignal = false;
    this._optimizeDiffMode = "side"; // "side" | "inline"
  }

  /**
   * Render a visible, hard-coded error card when any lifecycle entry throws.
   * MUST NOT depend on TRANSLATIONS / _i18n / _t / STYLES / this._hass / this._tab.
   * If shadowRoot is unavailable, falls back to this.innerHTML; if that also
   * fails, the console.error is still the last-resort signal.
   */
  _renderFatalError(err, phase) {
    try { console.error(`[ha-llm-automation] fatal error in ${phase}:`, err); } catch (_) {}
    const safe = (s) => {
      try {
        return String(s == null ? "" : s)
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      } catch (_) { return ""; }
    };
    const stackSummary = (() => {
      try { return (err && err.stack) ? err.stack.split("\n").slice(0, 5).join("\n") : ""; }
      catch (_) { return ""; }
    })();
    const html = `
      <div style="padding:24px;margin:12px;background:#3a0a0a;color:#ffd9d9;font-family:monospace;border:2px solid #7a2a2a;border-radius:8px;line-height:1.5">
        <h2 style="margin:0 0 12px 0;color:#ff8080">⚠ HA LLM Automation — Panel failed to initialize</h2>
        <div style="margin:6px 0"><b>面板初始化失败 / Panel initialization failed</b></div>
        <div style="margin:6px 0"><b>Phase:</b> <code>${safe(phase)}</code></div>
        <div style="margin:6px 0"><b>Error:</b> <code>${safe(err && err.message ? err.message : err)}</code></div>
        ${stackSummary ? `<pre style="margin:8px 0;padding:8px;background:#1a0505;color:#ffb3b3;overflow:auto;max-height:200px;white-space:pre-wrap">${safe(stackSummary)}</pre>` : ""}
        <div style="margin-top:12px;color:#ffb3b3">
          下一步：打开浏览器 DevTools Console 查看完整堆栈；复制上面的内容去 GitHub 提 issue。<br>
          Next: open DevTools Console for the full stack; copy the text above when filing an issue.
        </div>
      </div>
    `;
    try {
      if (this.shadowRoot) { this.shadowRoot.innerHTML = html; return; }
    } catch (_) {}
    try { this.innerHTML = html; } catch (_) {}
  }

  connectedCallback() {
    try {
      this._mqListener = () => {
        // 仅当未强制主题时跟随系统切换
        if (!this.hasAttribute("data-theme")) this._render();
      };
      window.matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", this._mqListener);
    } catch (e) {
      this._renderFatalError(e, "connectedCallback");
    }
  }

  disconnectedCallback() {
    if (this._mqListener) {
      window.matchMedia("(prefers-color-scheme: dark)")
        .removeEventListener("change", this._mqListener);
      this._mqListener = null;
    }
  }

  set hass(val) {
    try {
      const firstLoad = !this._hass;
      this._hass = val;
      if (firstLoad) {
        this._render();
        this._loadAutomations();
      }
    } catch (e) {
      this._renderFatalError(e, "hass_setter");
    }
  }

  set panel(val) {
    this._panel = val;
  }

  // ------------------------------------------------------------------
  // i18n helpers
  // ------------------------------------------------------------------

  /** Returns 'zh' for Chinese HA locales, 'en' for everything else */
  get _lang() {
    const lang = this._hass?.language || "zh-Hans";
    return lang.toLowerCase().startsWith("zh") ? "zh" : "en";
  }

  /** Translate key with optional interpolation vars, e.g. _t('key', {n: 3}) */
  _t(key, vars = {}) {
    return _i18n(this._lang, key, vars);
  }

  // ------------------------------------------------------------------
  // WS helpers
  // ------------------------------------------------------------------

  async _ws(type, params = {}) {
    return this._hass.connection.sendMessagePromise({ type: `${DOMAIN}/${type}`, ...params });
  }

  async _startSession() {
    if (this._logUnsub) {
      this._logUnsub();
      this._logUnsub = null;
    }
    const sessionId = genSessionId();
    this._sessionId = sessionId;
    this._logs = [];
    this._render();

    this._logUnsub = await this._hass.connection.subscribeMessage(
      (data) => {
        this._pushLog(data.message);
        this._updateLogPanel();
        this._scrollLog();
      },
      { type: `${DOMAIN}/subscribe_log`, session_id: sessionId }
    );
    return sessionId;
  }

  _pushLog(msg) {
    let cls = "log-entry";
    const m = msg.toLowerCase();
    if (msg.startsWith("[ERROR]") || msg.includes("失败") || msg.includes("错误") ||
        m.includes("fail") || m.includes("error")) {
      cls = "log-error";
    } else if (msg.startsWith("[OK]") || msg.startsWith("[SUCCESS]") ||
               msg.includes("完成") || msg.includes("成功") ||
               m.includes("complete") || m.includes("success") || m.includes("saved")) {
      cls = "log-success";
    } else if (msg.startsWith("[PROMPT]")) {
      cls = "log-prompt";
    }
    this._logs.push({ text: msg, cls });
  }

  _log(msg) {
    this._pushLog(msg);
    this._updateLogPanel();
    this._scrollLog();
  }

  _scrollLog() {
    const logEl = this.shadowRoot.querySelector(".log-entries");
    if (logEl) logEl.scrollTop = logEl.scrollHeight;
  }

  // 精准更新日志面板（不重建整个 DOM，避免干扰其他 Tab 的下拉/输入状态）
  _updateLogPanel() {
    const logEntries = this.shadowRoot.querySelector(".log-entries");
    if (logEntries) {
      logEntries.innerHTML = this._logs.map(
        l => `<div class="${l.cls}">${escHtml(l.text)}</div>`
      ).join("");
    }
  }

  _toast(msg, type = "") {
    const container = this.shadowRoot.querySelector(".toast-container");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `toast${type ? " " + type : ""}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }

  // ------------------------------------------------------------------
  // Data loaders
  // ------------------------------------------------------------------

  async _loadAutomations() {
    this._automationsLoading = true;
    this._render();
    try {
      const r = await this._ws("get_automations");
      this._automations = r.automations || [];
      this._optimizeAutomations = this._automations.filter(a => a.accessible);
      // Initialize consolidate selection to all accessible automations (only on first load)
      const accessibleIds = this._automations
        .filter(a => a.accessible && a.id && a.id !== "new")
        .map(a => a.id);
      if (this._consolidateSelectedIds === null) {
        this._consolidateSelectedIds = new Set(accessibleIds);
      }
    } catch (e) {
      // 保留 _automations 的当前值（null=失败，数组=之前成功过）
    } finally {
      this._automationsLoading = false;
      this._render();
    }
  }

  async _deleteInaccessible() {
    const inaccessible = (this._automations || []).filter(a => a.id && a.id !== "new" && a.accessible === false);
    if (inaccessible.length === 0) return;
    if (!confirm(this._t("confirm_del_inaccessible", {n: inaccessible.length}))) return;
    this._delInaccessibleRunning = true;
    this._render();
    try {
      // 后端自动探测并删除，不依赖前端传 ID（规避 HA WS 数组参数兼容性问题）
      const r = await this._ws("delete_inaccessible_automations");
      const deleted = r.deleted || [];
      const failed = r.failed || [];
      const scanned = r.scanned ?? "?";
      const ghostDeleted = deleted.filter(d => d.ghost);
      const normalDeleted = deleted.filter(d => !d.ghost);
      const yamlFailed = failed.filter(f => f.yaml_type);
      const realFailed = failed.filter(f => !f.yaml_type);
      this._log(this._t("log_del_inaccessible_summary", {scanned, api: normalDeleted.length, ghost: ghostDeleted.length, fail: failed.length}));
      ghostDeleted.forEach(d => this._log(this._t("log_ghost_cleared", {alias: d.alias || d.id})));
      if (yamlFailed.length > 0) {
        this._log(this._t("log_yaml_manual", {n: yamlFailed.length}));
        yamlFailed.forEach(f => this._log(`  • ${f.alias || f.id}`));
      }
      realFailed.forEach(f => this._log(this._t("log_del_fail_id", {id: f.id, alias: f.alias || "", error: f.error})));
      if (realFailed.length > 0) {
        this._toast(this._t("toast_clear_partial_fail", {n: realFailed.length}), "error");
      } else if (yamlFailed.length > 0) {
        this._toast(this._t("toast_clear_yaml_warn", {del: deleted.length, warn: yamlFailed.length}), "warn");
      } else {
        this._toast(this._t("toast_cleared_n", {n: deleted.length}), "success");
      }
      await this._loadAutomations();
    } catch (e) {
      const msg = e?.message || e?.code || String(e);
      this._log(this._t("log_del_inaccessible_fail", {msg}));
      this._toast(this._t("toast_clear_fail", {msg}), "error");
    } finally {
      this._delInaccessibleRunning = false;
      this._render();
    }
  }

  async _loadBackups() {
    try {
      const r = await this._ws("list_backups");
      this._backups = r.backups || [];
      this._render();
    } catch (e) {}
  }

  async _loadConfig() {
    try {
      const r = await this._ws("get_config");
      this._configData = r.config || {};
      this._configLoaded = true;
      this._render();
    } catch (e) {}
  }

  async _loadAreas() {
    try {
      const r = await this._ws("get_areas");
      this._areas = r.areas || [];
    } catch (e) { this._areas = []; }
  }

  async _loadLabels() {
    try {
      const r = await this._ws("get_labels");
      this._labels = r.labels || [];
    } catch (e) { this._labels = []; }
  }

  async _loadIntegrations() {
    try {
      const r = await this._ws("get_integrations");
      this._integrations = r.integrations || [];
    } catch (e) { this._integrations = []; }
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
    this._createExpanded = new Set();
    this._createRefineVisible = new Set();
    this._createChecked = new Set();
    this._render();

    try {
      const sessionId = await this._startSession();
      const r = await this._ws("create_start", {
        requirement,
        session_id: sessionId,
        // use_docs 由后端从 config.options 读取，此处不传
      });
      this._createResult = r;
      this._createSystemPrompt = r.system_prompt || "";
      // Auto-check all valid items (but don't expand)
      (r.automations || []).forEach((item, i) => {
        if (item.parsed && (!item.warnings || item.warnings.length === 0)) {
          this._createChecked.add(i);
        }
      });
    } catch (e) {
      this._log(`[ERROR] ${e.message || e}`);
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
        this._createChecked.add(index);
      } else {
        this._createChecked.delete(index);
      }
      this._createRefineVisible.delete(index);
    } catch (e) {
      this._log(this._t("log_refine_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _createSaveAll() {
    const automations = (this._createResult?.automations || [])
      .filter((item, i) => this._createChecked.has(i) && item.parsed);

    if (automations.length === 0) {
      this._toast(this._t("toast_no_sel"), "error");
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
      this._toast(this._t("create_saving", {n: r.results?.length || 0}), "success");
      this._createResult = null;
    } catch (e) {
      this._log(this._t("log_save_fail", {msg: e.message || e}));
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

    // 在 startSession 前读取追问方向（_startSession 会触发 _render 重置 DOM）
    const dirEl = this.shadowRoot.querySelector("#opt-direction-input");
    const userDirection = dirEl ? dirEl.value.trim() : "";

    const sessionId = await this._startSession();
    this._loading = true;
    this._optimizeAnalysis = null;
    this._optimizeGenResult = null;
    this._render();

    try {
      const r = await this._ws("optimize_analyze", {
        automation_id: id,
        session_id: sessionId,
        ...(userDirection ? { user_direction: userDirection } : {}),
      });
      this._optimizeAnalysis = r.analysis;
      this._optimizeAutoYaml = r.automation_yaml;
      this._optimizeOriginalYaml = r.automation_yaml;
    } catch (e) {
      this._log(this._t("log_analyze_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _optimizeGenerate() {
    const sessionId = await this._startSession();
    const directionEl = this.shadowRoot.querySelector("#opt-direction-input");
    const userDirection = directionEl ? directionEl.value.trim() : "";
    this._loading = true;
    this._optimizeGenResult = null;
    this._render();

    try {
      const r = await this._ws("optimize_generate", {
        automation_yaml: this._optimizeAutoYaml,
        analysis: this._optimizeAnalysis,
        session_id: sessionId,
        ...(userDirection ? { user_direction: userDirection } : {}),
      });
      this._optimizeGenResult = r;
      this._optimizeSystemPrompt = r.system_prompt || "";
    } catch (e) {
      this._log(this._t("log_generate_fail", {msg: e.message || e}));
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
    } catch (e) {
      this._log(this._t("log_refine_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _optimizeSave() {
    if (!this._optimizeGenResult?.parsed) {
      this._toast(this._t("toast_save_fail_yaml"), "error");
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
      this._toast(this._t("toast_optimize_saved"), "success");
      this._optimizeAnalysis = null;
      this._optimizeGenResult = null;
      await this._loadAutomations();
    } catch (e) {
      this._log(this._t("log_save_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Theme toggle & abort
  // ------------------------------------------------------------------

  _toggleTheme() {
    const t = this.getAttribute("data-theme");
    if (!t) this.setAttribute("data-theme", "dark");
    else if (t === "dark") this.setAttribute("data-theme", "light");
    else this.removeAttribute("data-theme");
    this._render();
  }

  _abort() {
    this._abortSignal = true;
    this._loading = false;
    this._log(this._t("log_aborted"));
    this._render();
  }

  // ------------------------------------------------------------------
  // Tab: Consolidate
  // ------------------------------------------------------------------

  _selectAllConsolidate(selectAll) {
    const all = (this._automations || []).filter(a => a.accessible && a.id && a.id !== "new");
    if (selectAll) {
      this._consolidateSelectedIds = new Set(all.map(a => a.id));
    } else {
      this._consolidateSelectedIds = new Set();
    }
    this._render();
  }

  async _startConsolidateAnalyze() {
    const selectedIds = [...(this._consolidateSelectedIds || [])];
    if (selectedIds.length === 0) {
      this._log(this._t("log_no_sel"));
      return;
    }
    this._abortSignal = false;
    this._loading = true;
    this._consolidatePlan = null;
    this._consolidateApproved = {};
    this._consolidateSkipped = new Set();
    this._render();

    try {
      const sessionId = await this._startSession();
      const r = await this._ws("consolidate_analyze", {
        session_id: sessionId,
        automation_ids: selectedIds,
      });
      if (this._abortSignal) return;
      this._consolidatePlan = r;
      (r.merge_groups || []).forEach((g, i) => {
        this._consolidateApproved[`merge_${i}`] = g;
      });
      (r.fix_items || []).forEach((f, i) => {
        this._consolidateApproved[`fix_${i}`] = f;
      });
      this._log(this._t("log_analyze_done"));
    } catch (e) {
      if (!this._abortSignal) this._log(this._t("log_analyze_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

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
      (r.merge_groups || []).forEach((g, i) => {
        this._consolidateApproved[`merge_${i}`] = g;
      });
      (r.fix_items || []).forEach((f, i) => {
        this._consolidateApproved[`fix_${i}`] = f;
      });
    } catch (e) {
      this._log(this._t("log_analyze_fail", {msg: e.message || e}));
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
        item_type: type, item_id: `${type}_${index}`,
        current_yaml: currentYaml, feedback, session_id: sessionId,
      });
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
    } catch (e) {
      this._log(this._t("log_refine_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _consolidateExecute() {
    const approvedMerges = Object.entries(this._consolidateApproved)
      .filter(([k]) => k.startsWith("merge_")).map(([, v]) => v);
    const approvedFixes = Object.entries(this._consolidateApproved)
      .filter(([k]) => k.startsWith("fix_")).map(([, v]) => v);

    if (approvedMerges.length === 0 && approvedFixes.length === 0) {
      this._toast(this._t("confirm_no_approved"), "error");
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
      this._toast(this._t("toast_exec_done", {ok: r.success, fail: r.failed}), r.failed > 0 ? "error" : "success");
      this._consolidatePlan = null;
    } catch (e) {
      this._log(this._t("log_exec_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Tab: Config — Save
  // ------------------------------------------------------------------

  async _saveConfig() {
    // Collect form values FIRST (before any DOM manipulation)
    const $ = id => this.shadowRoot.getElementById(id);
    const payload = {};

    const fields = [
      ["provider", "cfg-provider"],
      ["api_key", "cfg-api-key"],
      ["base_url", "cfg-base-url"],
      ["model", "cfg-model"],
    ];
    for (const [k, id] of fields) {
      const el = $(id);
      if (el) payload[k] = el.value.trim();
    }

    const maxTokensEl = $("cfg-max-tokens");
    if (maxTokensEl) {
      const v = parseInt(maxTokensEl.value);
      if (!isNaN(v)) payload.max_tokens = v;
    }
    const tempEl = $("cfg-temperature");
    if (tempEl) {
      const v = parseFloat(tempEl.value);
      if (!isNaN(v)) payload.temperature = v;
    }

    const extraDomEl = $("cfg-extra-domains-input");
    if (extraDomEl) payload.extra_visible_domains = extraDomEl.value.trim();
    const hiddenDomEl = $("cfg-hidden-domains");
    if (hiddenDomEl) payload.hidden_domains = hiddenDomEl.value.trim();

    const logPromptEl = $("cfg-log-prompt");
    if (logPromptEl) payload.log_prompt = logPromptEl.checked;

    const useDocsEl = $("cfg-use-docs");
    if (useDocsEl) payload.use_docs = useDocsEl.checked;

    // Area / label / integration filters from config state
    payload.area_filter = (this._configData.area_filter || []).slice();
    payload.label_filter = (this._configData.label_filter || []).slice();
    payload.integration_filter = (this._configData.integration_filter || []).slice();

    // Disable button to prevent double-click
    const btnSave = $("btn-save-config");
    if (btnSave) { btnSave.disabled = true; btnSave.textContent = this._t("config_saving"); }

    try {
      await this._ws("save_config", payload);
      this._configData = { ...this._configData, ...payload };
      this._toast(this._t("toast_config_saved"), "success");
    } catch (e) {
      this._toast(this._t("toast_save_fail", {msg: e.message || e}), "error");
    } finally {
      if (btnSave) { btnSave.disabled = false; btnSave.textContent = this._t("config_save_btn"); }
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
      this._toast(this._t("toast_docs_refreshed", {keys: (r.succeeded || []).join(", ")}), "success");
    } catch (e) {
      this._log(this._t("log_refresh_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _previewDoc(key) {
    try {
      const r = await this._ws("preview_doc", { doc_key: key });
      this._docPreview = { key, content: r.content, truncated: r.truncated };
      this._render();
    } catch (e) {
      this._toast(this._t("toast_preview_fail", {msg: e.message || e}), "error");
    }
  }

  async _restoreBackup(path) {
    const modeLabel = this._restoreMode === "overwrite" ? this._t("backup_overwrite") : this._t("backup_incremental");
    if (!confirm(this._t("confirm_restore", {mode: modeLabel, file: path.split("/").pop()}))) return;
    const sessionId = await this._startSession();
    this._loading = true;
    this._render();
    try {
      await this._ws("restore_backup", { backup_path: path, session_id: sessionId, restore_mode: this._restoreMode });
      this._toast(this._t("toast_restore_done"), "success");
    } catch (e) {
      this._log(this._t("log_restore_fail", {msg: e.message || e}));
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _clearBackups() {
    if (!confirm(this._t("confirm_clear_backups"))) return;
    const sessionId = genSessionId();
    try {
      const r = await this._ws("clear_backups", { session_id: sessionId });
      this._toast(this._t("toast_backups_cleared", {n: r.deleted}), "success");
      this._backups = [];
      this._render();
    } catch (e) {
      this._toast(this._t("toast_clear_all_fail", {msg: e.message || e}), "error");
    }
  }

  // ------------------------------------------------------------------
  // Render: YAML block with copy button
  // ------------------------------------------------------------------

  _renderYamlBlock(yaml, id) {
    return `
      <div class="yaml-wrapper">
        <div class="yaml-block" id="${id || ""}">${escHtml(yaml)}</div>
        <button class="yaml-copy-btn" data-yaml="${escHtml(yaml)}">${this._t("copy_btn")}</button>
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Render: Tag input
  // ------------------------------------------------------------------

  _renderTagInput(containerId, tags, placeholder) {
    return `
      <div class="tag-input-wrapper" id="${containerId}-wrapper">
        ${(tags || []).map((t, i) => `
          <span class="tag-chip">
            ${escHtml(t)}
            <span class="tag-chip-del" data-container="${containerId}" data-index="${i}">×</span>
          </span>
        `).join("")}
        <input type="text" class="tag-bare-input" id="${containerId}-input"
          placeholder="${tags?.length ? '' : placeholder}" />
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Render: Multi-select dropdown
  // ------------------------------------------------------------------

  _renderMultiSelect(id, items, selectedIds, labelKey, valueKey, isOpen) {
    const selected = new Set(selectedIds || []);
    const hasSelected = selected.size > 0;
    return `
      <div>
        <div class="summary-badges" style="${hasSelected ? '' : 'display:none'}">
          ${[...selected].map(sid => {
            const item = items.find(it => it[valueKey] === sid);
            return `<span class="badge badge-purple">${escHtml(item ? item[labelKey] : sid)}<span style="cursor:pointer;margin-left:4px" data-ms-remove="${id}" data-ms-val="${escHtml(sid)}">×</span></span>`;
          }).join("")}
        </div>
        <button class="dropdown-toggle-btn" id="${id}-toggle">
          ${this._t("create_expand_hint", {n: items.length})}
        </button>
        <div class="multi-select-dropdown ${isOpen ? 'open' : ''}" id="${id}-dropdown">
          ${items.map(item => `
            <label class="multi-select-item">
              <input type="checkbox" ${selected.has(item[valueKey]) ? 'checked' : ''}
                data-ms-id="${id}" data-ms-val="${escHtml(item[valueKey])}">
              ${escHtml(item[labelKey])}
              ${item[labelKey] !== item[valueKey] ? `<span style="color:#6b7280;font-size:11px;margin-left:4px">(${escHtml(item[valueKey])})</span>` : ''}
            </label>
          `).join("")}
        </div>
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Render: Create Tab
  // ------------------------------------------------------------------

  _renderCreate() {
    const result = this._createResult;
    const checkedCount = this._createChecked.size;

    return `
      <div class="card">
        <div class="card-title">${this._t("create_title")}</div>
        <div class="form-row">
          <div class="input-wrap">
            <textarea id="create-req" placeholder="${this._t("create_placeholder")}" rows="4"></textarea>
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn btn-primary" id="btn-create-start" ${this._loading ? 'disabled' : ''}>
            ${this._loading ? `<span class="spinner"></span> ${this._t("create_btn_loading")}` : this._t("create_btn")}
          </button>
        </div>
      </div>

      ${result ? this._renderCreateResults(result) : ""}
      ${result && result.automations?.length ? `
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:4px;flex-wrap:wrap;align-items:center">
          <button class="btn btn-secondary btn-sm" id="btn-create-select-all">${this._t("create_sel_all")}</button>
          <button class="btn btn-secondary btn-sm" id="btn-create-deselect-all">${this._t("create_sel_none")}</button>
          <button class="btn btn-success" id="btn-create-save" ${this._loading || checkedCount === 0 ? 'disabled' : ''}>
            ${this._loading ? '<span class="spinner"></span>' : '✓'} ${this._t("create_save_sel", {n: checkedCount})}
          </button>
        </div>
      ` : ""}
    `;
  }

  _renderCreateResults(result) {
    const items = result.automations || [];
    if (!items.length) return `<div class="error-box">${this._t("create_no_yaml")}</div>`;

    return items.map((item, i) => {
      const checked = this._createChecked.has(i);
      const expanded = this._createExpanded.has(i);
      const refineVisible = this._createRefineVisible.has(i);
      const hasWarnings = item.warnings?.length > 0;
      const alias = item.parsed?.alias || `automation_${i + 1}`;
      let cardClass = "automation-card";
      if (checked) cardClass += " approved";
      else if (hasWarnings) cardClass += " warning";

      return `
        <div class="${cardClass}" id="auto-card-${i}">
          <div class="automation-header" id="auto-hdr-${i}">
            <input type="checkbox" ${checked ? 'checked' : ''} ${!item.parsed ? 'disabled' : ''}
              id="auto-chk-${i}" style="width:auto;cursor:pointer" onclick="event.stopPropagation()">
            <span class="auto-title">[${i + 1}/${items.length}] ${escHtml(alias)}</span>
            ${hasWarnings ? `<span class="tag tag-warn">${this._t("create_has_issues")}</span>` : `<span class="tag tag-ok">${this._t("create_ok")}</span>`}
            <span style="font-size:14px;color:#6b7280">${expanded ? '▲' : '▼'}</span>
          </div>
          ${expanded ? `
            <div class="auto-body">
              ${hasWarnings ? `<div class="error-box">${item.warnings.map(w => escHtml(w)).join("<br>")}</div>` : ""}
              ${this._renderYamlBlock(item.yaml_str, `yaml-${i}`)}
              <div class="btn-row">
                <button class="btn btn-primary" id="btn-refine-toggle-${i}">
                  ${refineVisible ? this._t("create_refine_hide") : this._t("create_refine_show")}
                </button>
              </div>
              <div class="refine-area ${refineVisible ? 'visible' : ''}" id="refine-area-${i}">
                <div class="refine-input" style="margin-top:8px">
                  <textarea id="refine-input-${i}" placeholder="${this._t("create_refine_placeholder")}" rows="2"></textarea>
                  <button class="btn btn-secondary btn-sm" id="btn-refine-${i}">${this._t("create_refine_btn")}</button>
                </div>
              </div>
            </div>
          ` : ""}
        </div>
      `;
    }).join("");
  }

  // ------------------------------------------------------------------
  // Render: Optimize Tab
  // ------------------------------------------------------------------

  _renderOptimize() {
    const automations = this._optimizeAutomations;
    const analysis = this._optimizeAnalysis;
    const genResult = this._optimizeGenResult;

    return `
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
          <div class="card-title" style="margin:0">${this._t("opt_select_title")}</div>
          <button class="btn btn-secondary btn-sm" id="btn-opt-reload"
            ${this._automationsLoading ? 'disabled' : ''}>
            ${this._automationsLoading ? '<span class="spinner"></span>' : '🔄'} ${this._t("opt_refresh")}
          </button>
        </div>
        ${this._automationsLoading ? `
          <div class="load-hint"><span class="spinner"></span> ${this._t("opt_loading")}</div>
        ` : automations.length === 0 ? `
          <div class="load-hint">
            ${this._automations === null ? this._t("opt_load_fail") : this._t("opt_empty")}
          </div>
        ` : `
          <div class="form-row">
            <select id="opt-select">
              <option value="">${this._t("opt_placeholder")}</option>
              ${automations.map(a => `<option value="${escHtml(a.id)}" ${this._optimizeSelectedId === a.id ? "selected" : ""}>${escHtml(a.alias)} [${escHtml(a.id)}]</option>`).join("")}
            </select>
          </div>
          <button class="btn btn-primary" id="btn-opt-analyze" ${this._loading || !this._optimizeSelectedId ? 'disabled' : ''}>
            ${this._loading && !analysis ? `<span class="spinner"></span> ${this._t("opt_analyze_loading")}` : this._t("opt_analyze_btn")}
          </button>
        `}
      </div>

      ${analysis ? `
        <div class="card">
          <div class="card-title" style="margin-bottom:10px">${this._t("opt_step1_title")}</div>
          <div class="analysis-box">
            <div class="analysis-intent">🎯 ${escHtml(analysis.intent || "")}</div>
            ${analysis.issues?.length ? `
              <div style="font-size:12px;font-weight:700;color:#f87171;margin-bottom:4px">${this._t("opt_issues_title")}</div>
              <ul class="analysis-list analysis-issues">${analysis.issues.map(i => `<li>⚠ ${escHtml(i)}</li>`).join("")}</ul>
            ` : ""}
            ${analysis.suggestions?.length ? `
              <div style="font-size:12px;font-weight:700;color:#4ade80;margin-top:8px;margin-bottom:4px">${this._t("opt_sugg_title")}</div>
              <ul class="analysis-list analysis-suggs">${analysis.suggestions.map(s => `<li>✦ ${escHtml(s)}</li>`).join("")}</ul>
            ` : ""}
          </div>
          <div style="margin: 10px 0 6px">
            <label class="form-label" style="font-size:12px;margin-bottom:4px;display:block">${this._t("opt_direction_label")}</label>
            <div class="input-wrap">
              <textarea id="opt-direction-input" rows="2"
                placeholder="${this._t("opt_direction_placeholder")}"></textarea>
            </div>
          </div>
          <div class="btn-row" style="margin-top:8px">
            <button class="btn btn-secondary" id="btn-opt-reanalyze" ${this._loading ? 'disabled' : ''}>${this._t("opt_reanalyze")}</button>
            <button class="btn btn-primary" id="btn-opt-generate" ${this._loading ? 'disabled' : ''}>
              ${this._loading && !genResult ? `<span class="spinner"></span> ${this._t("opt_generate_loading")}` : this._t("opt_generate_btn")}
            </button>
          </div>
        </div>
      ` : ""}

      ${genResult ? `
        <div class="card">
          <div class="card-title">${this._t("opt_step2_title")}</div>
          ${genResult.warnings?.length ? `<div class="error-box">${genResult.warnings.map(w => escHtml(w)).join("<br>")}</div>` : ""}
          ${analysis?.suggestions?.length ? `
            <div class="summary-badges">
              ${analysis.suggestions.slice(0, 5).map((s, si) => {
                const colors = ["badge-blue","badge-green","badge-orange","badge-purple","badge-blue"];
                return `<span class="badge ${colors[si % colors.length]}">${escHtml(s.slice(0, 30))}${s.length > 30 ? "…" : ""}</span>`;
              }).join("")}
            </div>
          ` : ""}
          <div class="diff-mode-btns">
            <button class="btn btn-secondary btn-sm${this._optimizeDiffMode === 'side' ? ' active' : ''}" id="btn-diff-side">${this._t("opt_diff_side")}</button>
            <button class="btn btn-secondary btn-sm${this._optimizeDiffMode === 'inline' ? ' active' : ''}" id="btn-diff-inline">${this._t("opt_diff_inline")}</button>
          </div>
          ${this._optimizeDiffMode === 'side' ? `
            <div class="diff-container">
              <div>
                <div class="diff-label">${this._t("opt_diff_before")}</div>
                ${this._renderYamlBlock(this._optimizeOriginalYaml, "yaml-opt-before")}
              </div>
              <div>
                <div class="diff-label">${this._t("opt_diff_after")}</div>
                ${this._renderYamlBlock(genResult.yaml_str, "yaml-opt-after")}
              </div>
            </div>
          ` : `
            <div class="diff-label" style="margin-bottom:4px">${this._t("opt_diff_inline_label")}</div>
            <div class="yaml-block">${renderDiff(this._optimizeOriginalYaml, genResult.yaml_str)}</div>
          `}
          <div class="refine-input" style="margin-top:12px">
            <div class="input-wrap">
              <textarea id="opt-refine-input" placeholder="${this._t("opt_refine_placeholder")}" rows="2"></textarea>
            </div>
            <button class="btn btn-secondary btn-sm" id="btn-opt-refine">${this._t("opt_refine_btn")}</button>
          </div>
          <div class="btn-row">
            <button class="btn btn-success" id="btn-opt-save" ${!genResult.parsed || this._loading ? 'disabled' : ''}>
              ${this._t("opt_save_btn")}
            </button>
          </div>
        </div>
      ` : ""}
    `;
  }

  // ------------------------------------------------------------------
  // Render: Consolidate Tab
  // ------------------------------------------------------------------

  _renderConsolidate() {
    const plan = this._consolidatePlan;
    const consolidateAutomations = (this._automations || []).filter(a => a.id && a.id !== "new" && a.accessible !== false);
    const selectedSet = this._consolidateSelectedIds || new Set();
    const accessibleAutomations = consolidateAutomations.filter(a => a.accessible);
    const selectedAccessibleCount = accessibleAutomations.filter(a => selectedSet.has(a.id)).length;
    const inaccessibleCount = (this._automations || []).filter(a => a.id && a.id !== "new" && a.accessible === false).length;

    return `
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
          <div class="card-title" style="margin:0">${this._t("cons_title")}</div>
          <button class="btn btn-secondary btn-sm" id="btn-cons-reload"
            ${this._automationsLoading ? 'disabled' : ''}>
            ${this._automationsLoading ? '<span class="spinner"></span>' : '🔄'} ${this._t("cons_refresh")}
          </button>
        </div>
        <p style="color:#9ca3af;margin:0 0 12px;font-size:13px">
          ${this._t("cons_desc")}
        </p>

        ${this._automationsLoading ? `
          <div class="load-hint"><span class="spinner"></span> ${this._t("cons_loading")}</div>
        ` : consolidateAutomations.length === 0 ? `
          <div class="load-hint">
            ${this._automations === null ? this._t("cons_load_fail") : this._t("cons_empty")}
          </div>
        ` : `
          <div class="consolidate-select-panel" style="padding:0 0 12px 0">
            <div class="panel-label">
              ${this._t("cons_select_label", {sel: selectedAccessibleCount, total: accessibleAutomations.length})}
            </div>
            <div class="automation-checklist" id="consolidate-checklist">
              ${consolidateAutomations.map(a => `
                <label class="check-item${!a.accessible ? ' check-item-disabled' : ''}">
                  <input type="checkbox" class="consolidate-check-item" data-aid="${escHtml(a.id)}"
                    ${!a.accessible ? 'disabled' : ''}
                    ${selectedSet.has(a.id) ? 'checked' : ''}>
                  <span class="check-label">${escHtml(a.alias || a.id)}</span>
                  ${!a.accessible ? `<span class="check-warning">${this._t("cons_inaccessible")}</span>` : ''}
                </label>
              `).join('')}
            </div>
            <div class="checklist-actions">
              <button class="btn btn-secondary btn-sm" id="btn-cons-select-all">${this._t("cons_sel_all")}</button>
              <button class="btn btn-secondary btn-sm" id="btn-cons-deselect-all">${this._t("cons_sel_none")}</button>
              ${inaccessibleCount > 0 ? `
              <button class="btn btn-secondary btn-sm" id="btn-cons-del-inaccessible"
                style="color:#f87171;border-color:#f87171"
                ${this._loading || this._delInaccessibleRunning ? 'disabled' : ''}>
                ${this._delInaccessibleRunning
                  ? `<span class="spinner"></span> ${this._t("cons_deleting")}`
                  : this._t("cons_del_btn", {n: inaccessibleCount})}
              </button>` : ''}
              <button class="btn btn-primary" id="btn-cons-start-analyze"
                ${this._loading || selectedAccessibleCount === 0 ? 'disabled' : ''}>
                ${this._loading && !plan
                  ? `<span class="spinner"></span> ${this._t("cons_analyze_loading")}`
                  : this._t("cons_analyze_btn", {n: selectedAccessibleCount})}
              </button>
            </div>
          </div>
        `}
      </div>
      ${plan ? this._renderConsolidatePlan(plan) : ""}
    `;
  }

  _renderConsolidatePlan(plan) {
    const merges = plan.merge_groups || [];
    const fixes = plan.fix_items || [];
    const oks = plan.ok_items || [];
    const approvedCount = Object.keys(this._consolidateApproved).filter(k => !this._consolidateSkipped.has(k)).length;

    return `
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <div class="card-title" style="margin:0">${this._t("cons_plan_title")}</div>
          <div style="font-size:12px;color:#9ca3af">
            ${this._t("cons_summary", {merge: merges.length, fix: fixes.length, ok: oks.length})}
          </div>
        </div>

        ${(merges.length + fixes.length) > 0 ? `
          <div class="consolidate-batch-bar">
            <span class="hint-text">${this._t("cons_batch_selected", {n: approvedCount})}</span>
            <button class="btn-sm btn-sm-plain" id="btn-cs-all">${this._t("cons_batch_all")}</button>
            <button class="btn-sm btn-sm-plain" id="btn-cs-none">${this._t("cons_batch_none")}</button>
            <button class="btn btn-primary btn-sm" id="btn-cs-execute"
              ${this._loading || approvedCount === 0 ? 'disabled' : ''}>
              ${this._t("cons_batch_exec", {n: approvedCount})}
            </button>
          </div>
        ` : ""}

        ${merges.map((g, i) => {
          const key = `merge_${i}`;
          const approved = !!this._consolidateApproved[key];
          const skipped = this._consolidateSkipped.has(key);
          const expanded = this._consolidateExpandedYaml[key];
          return `
            <div class="automation-card ${skipped ? "skipped" : approved ? "approved" : ""}">
              <div class="automation-header" id="cons-hdr-merge-${i}">
                <input type="checkbox" class="cons-item-cb" data-key="merge_${i}"
                  ${approved && !skipped ? 'checked' : ''}>
                <span class="tag tag-merge">${this._t("cons_merge_tag")}</span>
                <span class="auto-title">${this._t("cons_scenario", {name: escHtml(g.scenario || "")})}</span>
                <span style="font-size:11px;color:#9ca3af">${(g.aliases || []).slice(0,3).join(" + ")}${g.aliases?.length > 3 ? '…' : ''}</span>
                <span style="font-size:14px;color:#6b7280">${expanded ? '▲' : '▼'}</span>
              </div>
              ${expanded ? `
                <div class="auto-body">
                  <p style="color:#9ca3af;font-size:12px;margin:0 0 8px">${escHtml(g.reason || "")}</p>
                  ${(g.original_yamls || []).length > 0 ? `
                    <div style="margin-bottom:10px">
                      <div style="font-size:11px;font-weight:700;color:var(--secondary-text-color,#9ca3af);margin-bottom:6px">
                        ${this._t("cons_originals", {n: (g.original_yamls || []).length})}
                      </div>
                      ${(g.original_yamls || []).map((oy, oi) => `
                        <div style="margin-bottom:6px">
                          <div style="font-size:11px;color:#818cf8;margin-bottom:3px">[${oi + 1}] ${escHtml(oy.id)}</div>
                          ${oy.yaml ? this._renderYamlBlock(oy.yaml, `cons-orig-merge-${i}-${oi}`) : `<div style="color:#6b7280;font-size:11px">${this._t("cons_no_original")}</div>`}
                        </div>
                      `).join("")}
                    </div>
                    <div style="font-size:11px;font-weight:700;color:#818cf8;margin-bottom:6px">${this._t("cons_merged_label")}</div>
                  ` : ""}
                  ${this._renderYamlBlock(g.merged_yaml || "", `cons-yaml-merge-${i}`)}
                  <div class="refine-input" style="margin-top:8px">
                    <textarea id="cons-refine-merge-${i}" placeholder="${this._t("cons_refine_placeholder")}" rows="2"></textarea>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-refine-merge-${i}">${this._t("cons_refine_btn")}</button>
                  </div>
                  <div class="btn-row">
                    <button class="btn btn-success btn-sm" id="btn-cons-approve-merge-${i}">${this._t("cons_approve")}</button>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-skip-merge-${i}">${this._t("cons_skip")}</button>
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
                <input type="checkbox" class="cons-item-cb" data-key="fix_${i}"
                  ${approved && !skipped ? 'checked' : ''}>
                <span class="tag tag-fix">${this._t("cons_fix_tag")}</span>
                <span class="auto-title">${escHtml(f.alias || f.id)}</span>
                <span style="font-size:11px;color:#f87171">${escHtml((f.issue || "").slice(0, 50))}</span>
                <span style="font-size:14px;color:#6b7280">${expanded ? '▲' : '▼'}</span>
              </div>
              ${expanded ? `
                <div class="auto-body">
                  <p style="color:#f87171;font-size:12px;margin:0 0 8px">${this._t("cons_issue_prefix", {issue: escHtml(f.issue || "")})}</p>
                  ${f.original_yaml ? `
                    <div class="diff-container">
                      <div>
                        <div class="diff-label">${this._t("cons_fix_before")}</div>
                        ${this._renderYamlBlock(f.original_yaml, `cons-orig-fix-${i}`)}
                      </div>
                      <div>
                        <div class="diff-label">${this._t("cons_fix_after")}</div>
                        ${this._renderYamlBlock(f.fixed_yaml || "", `cons-yaml-fix-${i}`)}
                      </div>
                    </div>
                  ` : this._renderYamlBlock(f.fixed_yaml || "", `cons-yaml-fix-${i}`)}
                  <div class="refine-input" style="margin-top:8px">
                    <textarea id="cons-refine-fix-${i}" placeholder="${this._t("cons_refine_placeholder")}" rows="2"></textarea>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-refine-fix-${i}">${this._t("cons_refine_btn")}</button>
                  </div>
                  <div class="btn-row">
                    <button class="btn btn-success btn-sm" id="btn-cons-approve-fix-${i}">${this._t("cons_approve")}</button>
                    <button class="btn btn-secondary btn-sm" id="btn-cons-skip-fix-${i}">${this._t("cons_skip")}</button>
                  </div>
                </div>
              ` : ""}
            </div>
          `;
        }).join("")}

        ${oks.length ? `
          <div style="padding:8px 12px;background:rgba(74,222,128,0.04);border-radius:8px;font-size:12px;color:#4ade80;margin-top:4px">
            ${this._t("cons_ok_items", {n: oks.length, list: oks.map(o => o.alias).join("、")})}
          </div>
        ` : ""}

        <div style="margin-top:14px;display:flex;justify-content:flex-end">
          <button class="btn btn-success" id="btn-cons-execute"
            ${this._loading || approvedCount === 0 ? 'disabled' : ''}>
            ${this._loading ? '<span class="spinner"></span>' : '⚡'} ${this._t("cons_exec_all", {n: approvedCount})}
          </button>
        </div>
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Render: Config Tab
  // ------------------------------------------------------------------

  _renderConfig() {
    const c = this._configData;
    if (!this._configLoaded) {
      return `<div class="card"><div style="color:#9ca3af;text-align:center;padding:30px">${this._t("config_loading")}</div></div>`;
    }

    const areaFilter = c.area_filter || [];
    const labelFilter = c.label_filter || [];
    const integFilter = c.integration_filter || [];

    // Map area ids to names for display
    const areaItems = this._areas.map(a => ({ label_id: a.area_id, name: a.name }));

    return `
      <div class="card">
        <div class="card-title">${this._t("config_title")}</div>

        <div class="form-row">
          <label class="form-label">Provider</label>
          <select id="cfg-provider">
            ${["openai_compatible","openai","anthropic"].map(p =>
              `<option value="${p}" ${(c.provider || "openai_compatible") === p ? "selected" : ""}>${p}</option>`
            ).join("")}
          </select>
        </div>

        <div class="form-row">
          <label class="form-label">API Key</label>
          <div class="pw-wrapper">
            <input type="${this._showApiKey ? 'text' : 'password'}" id="cfg-api-key"
              value="${escHtml(c.api_key || "")}" placeholder="sk-..." style="padding-right:38px">
            <button class="pw-toggle" id="btn-toggle-apikey">${this._showApiKey ? '🙈' : '👁'}</button>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label">${this._t("config_base_url")}</label>
          <input type="text" id="cfg-base-url" value="${escHtml(c.base_url || "")}" placeholder="https://api.openai.com/v1">
        </div>

        <div class="form-row">
          <label class="form-label">${this._t("config_model")}</label>
          <input type="text" id="cfg-model" value="${escHtml(c.model || "gpt-4o")}" placeholder="gpt-4o">
        </div>

        <div class="form-grid">
          <div class="form-row">
            <label class="form-label">Max Tokens</label>
            <input type="number" id="cfg-max-tokens" value="${c.max_tokens || 8192}" min="512" max="32768">
          </div>
          <div class="form-row">
            <label class="form-label">Temperature (0.0–1.0)</label>
            <input type="number" id="cfg-temperature" value="${c.temperature !== undefined ? c.temperature : 0.3}" min="0" max="1" step="0.05">
          </div>
        </div>

        <div class="config-section">
          <div class="config-section-title">${this._t("config_filter_title")}</div>
          <p class="hint-text">${this._t("config_filter_note")}</p>

          <div class="form-row">
            <label class="form-label">${this._t("config_extra_domains")}</label>
            <input type="text" id="cfg-extra-domains-input" value="${escHtml(c.extra_visible_domains || "")}" placeholder="notify,remote">
          </div>

          <div class="form-row">
            <label class="form-label">${this._t("config_hidden_domains")}</label>
            <div style="margin-top:0"><input type="text" id="cfg-hidden-domains" value="${escHtml(c.hidden_domains || "")}" placeholder="${this._t("config_hidden_placeholder")}" style="font-size:12px"></div>
          </div>

          <div class="form-row">
            <label class="form-label">${this._t("config_area_filter")}</label>
            ${this._renderMultiSelect(
              "cfg-area", this._areas,
              areaFilter, "name", "area_id",
              this._areaDropOpen
            )}
          </div>

          <div class="form-row">
            <label class="form-label">${this._t("config_integ_filter")}</label>
            ${this._renderMultiSelect(
              "cfg-integ",
              this._integrations.map(s => ({label_id: s, name: s})),
              integFilter, "name", "label_id",
              this._integDropOpen
            )}
          </div>

          <div class="form-row">
            <label class="form-label">${this._t("config_label_filter")}</label>
            ${this._renderMultiSelect(
              "cfg-label", this._labels.map(l => ({label_id: l.label_id, name: l.name || l.label_id})),
              labelFilter, "name", "label_id",
              this._labelDropOpen
            )}
          </div>
        </div>

        <div class="config-section">
          <div class="config-section-title">${this._t("config_advanced")}</div>
          <label class="checkbox-row">
            <input type="checkbox" id="cfg-log-prompt" ${c.log_prompt ? 'checked' : ''}>
            ${this._t("config_log_prompt")}
          </label>
          <label class="checkbox-row" style="margin-top:8px">
            <input type="checkbox" id="cfg-use-docs" ${c.use_docs !== false ? 'checked' : ''}>
            ${this._t("config_use_docs")}
          </label>
        </div>

        <div style="margin-top:18px">
          <button class="btn btn-primary" id="btn-save-config">${this._t("config_save_btn")}</button>
        </div>
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Render: Knowledge/Backup Tab
  // ------------------------------------------------------------------

  _renderKnowledge() {
    const DOC_KEYS = [
      "automation_basic", "automation_trigger", "automation_condition",
      "automation_action", "templating", "scripts", "service_calls"
    ];

    return `
      <div class="card">
        <div class="card-title">${this._t("know_title")}</div>
        <ul class="doc-list">
          ${DOC_KEYS.map(k => `
            <li class="doc-item">
              <span class="doc-key">${k}</span>
              <button class="btn btn-secondary btn-sm" id="btn-preview-doc-${k}">${this._t("know_preview_btn")}</button>
            </li>
          `).join("")}
        </ul>
        ${this._docPreview.key ? `
          <div style="margin-top:10px">
            <div style="font-size:12px;color:#9ca3af;margin-bottom:4px">
              ${escHtml(this._docPreview.key)}${this._docPreview.truncated ? ` ${this._t("know_truncated")}` : ""}
            </div>
            <div class="doc-preview-area visible">${escHtml(this._docPreview.content || "")}</div>
          </div>
        ` : ""}
        <div style="margin-top:14px">
          <button class="btn btn-primary" id="btn-refresh-docs" ${this._loading ? 'disabled' : ''}>
            ${this._loading ? `<span class="spinner"></span> ${this._t("know_refreshing")}` : this._t("know_refresh_btn")}
          </button>
        </div>
      </div>

      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
          <div class="card-title" style="margin:0">${this._t("backup_title")}</div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary btn-sm" id="btn-load-backups">${this._t("backup_refresh")}</button>
            <button class="btn btn-danger btn-sm" id="btn-clear-backups">${this._t("backup_clear_all")}</button>
          </div>
        </div>
        <!-- 恢复模式选择器 -->
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;padding:8px 10px;background:rgba(129,140,248,0.06);border-radius:8px;flex-wrap:wrap">
          <span style="font-size:12px;color:var(--secondary-text-color)">${this._t("backup_mode_label")}</span>
          <button class="btn btn-sm ${this._restoreMode === 'incremental' ? 'btn-primary' : 'btn-secondary'}" id="btn-mode-incremental">${this._t("backup_incremental")}</button>
          <button class="btn btn-sm ${this._restoreMode === 'overwrite' ? 'btn-primary' : 'btn-secondary'}" id="btn-mode-overwrite">${this._t("backup_overwrite")}</button>
          <span style="font-size:11px;color:#6b7280">${this._restoreMode === 'incremental' ? this._t("backup_incremental_hint") : this._t("backup_overwrite_hint")}</span>
        </div>
        ${this._backups.length === 0 ? `
          <div style="color:#6b7280;text-align:center;padding:20px;font-size:13px">${this._t("backup_empty")}</div>
        ` : `
          <ul class="backup-list">
            ${this._backups.map((b, i) => `
              <li class="backup-item">
                <div class="backup-info">
                  <div class="backup-name">${escHtml(b.name)}</div>
                  <div class="backup-meta">${escHtml(b.mtime)} · ${this._t("backup_meta", {count: b.count, size: b.size_kb})}</div>
                </div>
                <button class="btn btn-secondary btn-sm" id="btn-restore-${i}">${this._t("backup_restore_btn")}</button>
              </li>
            `).join("")}
          </ul>
        `}
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Render: Log Panel
  // ------------------------------------------------------------------

  _renderLogPanel() {
    return `
      <div class="log-panel">
        <div class="log-title">
          ${this._t("log_title")}
          <button class="btn btn-secondary btn-sm" id="btn-clear-log">${this._t("log_clear")}</button>
        </div>
        <div class="log-entries">
          ${this._logs.length === 0
            ? `<div style="color:#374151;text-align:center;padding:20px">${this._t("log_waiting")}</div>`
            : this._logs.map(l => `<div class="${l.cls}">${escHtml(l.text)}</div>`).join("")
          }
        </div>
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Manage tab
  // ------------------------------------------------------------------

  _renderManage() {
    if (this._automationsLoading) {
      return `<div class="card" style="text-align:center;padding:24px"><span class="spinner"></span> ${this._t("manage_loading")}</div>`;
    }
    if (this._automations === null) {
      return `<div class="card"><div style="text-align:center;padding:20px">
        <div style="color:#9ca3af;margin-bottom:12px">${this._t("manage_not_loaded")}</div>
        <button class="btn btn-primary" id="btn-manage-reload">${this._t("manage_load_btn")}</button>
      </div></div>`;
    }
    const list = (this._automations || []).filter(a => a.id && a.id !== "new");
    const checkedIds = list.filter(a => this._manageChecked.has(a.id) && a.accessible !== false);
    const checkedCount = checkedIds.length;
    return `
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div class="card-title" style="margin:0">${this._t("manage_title")}
            <span style="font-weight:400;font-size:13px;color:#9ca3af"> ${list.length}</span>
          </div>
          <button class="btn btn-secondary btn-sm" id="btn-manage-reload">${this._t("manage_refresh")}</button>
        </div>
        ${list.length === 0 ? `<div style="color:#6b7280;text-align:center;padding:20px">${this._t("manage_empty")}</div>` : `
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;padding:8px 10px;background:rgba(129,140,248,0.07);border-radius:8px;flex-wrap:wrap">
            <button class="btn btn-secondary btn-sm" id="btn-manage-sel-all">${this._t("manage_sel_all")}</button>
            <button class="btn btn-secondary btn-sm" id="btn-manage-sel-none">${this._t("manage_sel_none")}</button>
            <span style="flex:1;font-size:12px;color:#9ca3af">${this._t("manage_selected", {n: checkedCount})}</span>
            <button class="btn btn-secondary btn-sm" id="btn-manage-backup" ${checkedCount === 0 ? 'disabled' : ''}>${this._t("manage_backup_btn", {n: checkedCount})}</button>
            <button class="btn btn-danger btn-sm" id="btn-manage-delete" ${checkedCount === 0 ? 'disabled' : ''}>${this._t("manage_delete_btn", {n: checkedCount})}</button>
          </div>
          <ul style="list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px">
            ${list.map(a => {
              const inaccessible = a.accessible === false;
              const checked = this._manageChecked.has(a.id) && !inaccessible;
              return `<li style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;
                background:${inaccessible ? 'rgba(239,68,68,0.05)' : 'rgba(129,140,248,0.04)'};
                border:1px solid ${inaccessible ? 'rgba(239,68,68,0.15)' : 'var(--divider-color,rgba(255,255,255,0.06))'}">
                <input type="checkbox" id="manage-chk-${escHtml(a.id)}" ${checked ? 'checked' : ''} ${inaccessible ? 'disabled' : ''}
                  style="accent-color:#818cf8;flex-shrink:0;width:15px;height:15px">
                <div style="flex:1;min-width:0">
                  <div style="font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escHtml(a.alias || a.id)}</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:1px">${escHtml(a.id)} · ${escHtml(a.mode || "single")}${inaccessible ? ` · <span style="color:#f87171">${this._t("manage_inaccessible")}</span>` : ''}</div>
                </div>
              </li>`;
            }).join("")}
          </ul>
        `}
      </div>
    `;
  }

  async _manageBackup() {
    const ids = (this._automations || [])
      .filter(a => this._manageChecked.has(a.id) && a.accessible !== false)
      .map(a => a.id);
    if (ids.length === 0) return;
    if (!confirm(this._t("confirm_backup_sel", {n: ids.length}))) return;
    try {
      const r = await this._ws("backup_selected", { automation_ids_csv: ids.join(",") });
      this._toast(this._t("toast_backed_up", {n: r.count, file: r.name}), "success");
    } catch (e) {
      this._toast(this._t("toast_backup_fail", {msg: e.message || e}), "error");
    }
  }

  async _manageDelete() {
    const ids = (this._automations || [])
      .filter(a => this._manageChecked.has(a.id) && a.accessible !== false)
      .map(a => a.id);
    if (ids.length === 0) return;
    if (!confirm(this._t("confirm_del_sel", {n: ids.length}))) return;
    const sessionId = await this._startSession();
    this._loading = true;
    this._render();
    try {
      const r = await this._ws("batch_delete_automations", {
        automation_ids_csv: ids.join(","),
        session_id: sessionId,
      });
      const deleted = r.deleted || [];
      const failed = r.failed || [];
      this._log(this._t("log_batch_del_summary", {ok: deleted.length, fail: failed.length}));
      failed.forEach(f => this._log(this._t("log_batch_del_fail_id", {id: f.id, error: f.error})));
      if (failed.length > 0) {
        this._toast(this._t("toast_del_partial_fail", {ok: deleted.length, fail: failed.length}), "error");
      } else {
        this._toast(this._t("toast_deleted_n", {n: deleted.length}), "success");
      }
      this._manageChecked.clear();
      await this._loadAutomations();
    } catch (e) {
      this._log(this._t("log_batch_del_fail", {msg: e.message || e}));
      this._toast(this._t("toast_del_fail", {msg: e.message || e}), "error");
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // ------------------------------------------------------------------
  // Main render
  // ------------------------------------------------------------------

  _render() {
    try {
      this._renderInner();
    } catch (e) {
      this._renderFatalError(e, "render");
    }
  }

  _renderInner() {
    const tabs = [
      { id: "create", label: this._t("tab_create") },
      { id: "optimize", label: this._t("tab_optimize") },
      { id: "consolidate", label: this._t("tab_consolidate") },
      { id: "manage", label: this._t("tab_manage") },
      { id: "config", label: this._t("tab_config") },
      { id: "knowledge", label: this._t("tab_knowledge") },
    ];

    let mainContent = "";
    if (this._tab === "create") mainContent = this._renderCreate();
    else if (this._tab === "optimize") mainContent = this._renderOptimize();
    else if (this._tab === "consolidate") mainContent = this._renderConsolidate();
    else if (this._tab === "manage") mainContent = this._renderManage();
    else if (this._tab === "config") mainContent = this._renderConfig();
    else if (this._tab === "knowledge") mainContent = this._renderKnowledge();

    // 主题按钮三态
    const _themeAttr = this.getAttribute("data-theme");
    const _themeIcon  = _themeAttr === "dark" ? "🌙" : _themeAttr === "light" ? "☀️" : "🖥️";
    const _themeLabel = _themeAttr === "dark" ? this._t("theme_dark") : _themeAttr === "light" ? this._t("theme_light") : this._t("theme_auto");
    const _themeCls   = _themeAttr === "dark" ? "theme-dark" : _themeAttr === "light" ? "theme-light" : "theme-auto";

    // 保存滚动位置，防止 innerHTML 重写后归零
    const prevContent = this.shadowRoot.querySelector(".content");
    const prevMain = this.shadowRoot.querySelector(".main-area");
    const savedContentScroll = prevContent ? prevContent.scrollTop : 0;
    const savedMainScroll = prevMain ? prevMain.scrollTop : 0;

    // 保存 Toast 节点（innerHTML 重写会清空容器，toast 会消失）
    const prevToastContainer = this.shadowRoot.querySelector(".toast-container");
    const toastNodes = prevToastContainer ? [...prevToastContainer.childNodes] : [];

    // 保存配置表单的当前输入值（避免 re-render 重置用户正在编辑的内容）
    const cfgFieldIds = ["cfg-provider", "cfg-api-key", "cfg-base-url", "cfg-model",
                         "cfg-max-tokens", "cfg-temperature", "cfg-extra-domains-input", "cfg-hidden-domains"];
    const savedCfgValues = {};
    if (this._tab === "config") {
      for (const fid of cfgFieldIds) {
        const el = this.shadowRoot.getElementById(fid);
        if (el) savedCfgValues[fid] = el.value;
      }
    }

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="header">
        <h1>🤖 HA LLM Automation</h1>
        ${this._loading ? '<span class="spinner" style="color:#818cf8"></span>' : ""}
        ${this._loading ? `<button class="icon-btn abort-btn" id="btn-abort" title="${this._t("abort_title")}">■</button>` : ""}
        <button class="icon-btn theme-btn ${_themeCls}" id="btn-toggle-theme" title="${this._t("theme_toggle", {label: _themeLabel})}">${_themeIcon}<span class="theme-label">${_themeLabel}</span></button>
      </div>
      <div class="tabs">
        ${tabs.map(t => `<div class="tab ${this._tab === t.id ? "active" : ""}" data-tab="${t.id}">${t.label}</div>`).join("")}
      </div>
      <div class="content">
        <div class="main-area">${mainContent}</div>
        <div class="log-area">${this._renderLogPanel()}</div>
      </div>
      <div class="toast-container"></div>
    `;

    // 恢复滚动位置
    const newContent = this.shadowRoot.querySelector(".content");
    if (newContent && savedContentScroll) newContent.scrollTop = savedContentScroll;
    const newMain = this.shadowRoot.querySelector(".main-area");
    if (newMain && savedMainScroll) newMain.scrollTop = savedMainScroll;

    // 恢复 Toast 节点（移动到新容器，保持 setTimeout 引用有效）
    if (toastNodes.length) {
      const newToastContainer = this.shadowRoot.querySelector(".toast-container");
      if (newToastContainer) toastNodes.forEach(n => newToastContainer.appendChild(n));
    }

    // 恢复配置表单值（防止用户正在编辑时被 re-render 重置）
    for (const [fid, val] of Object.entries(savedCfgValues)) {
      const el = this.shadowRoot.getElementById(fid);
      if (el) el.value = val;
    }

    this._bindEvents();
  }

  // ------------------------------------------------------------------
  // Event binding
  // ------------------------------------------------------------------

  _bindEvents() {
    const $ = id => this.shadowRoot.getElementById(id);
    const root = this.shadowRoot;

    // Header buttons
    const btnAbort = $("btn-abort");
    if (btnAbort) btnAbort.addEventListener("click", () => this._abort());

    const btnToggleTheme = $("btn-toggle-theme");
    if (btnToggleTheme) btnToggleTheme.addEventListener("click", () => this._toggleTheme());

    // Tabs
    root.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        const prevTab = this._tab;
        this._tab = tab.dataset.tab;
        if (this._tab === "knowledge") this._loadBackups();
        if (this._tab === "optimize" && prevTab !== "optimize") this._loadAutomations();
        if (this._tab === "consolidate" && prevTab !== "consolidate") this._loadAutomations();
        if (this._tab === "manage" && prevTab !== "manage") this._loadAutomations();
        if (this._tab === "config" && !this._configLoaded) {
          Promise.all([this._loadConfig(), this._loadAreas(), this._loadLabels(), this._loadIntegrations()])
            .then(() => this._render());
        }
        this._render();
      });
    });

    // Log clear
    const clearLog = $("btn-clear-log");
    if (clearLog) clearLog.addEventListener("click", () => { this._logs = []; this._render(); });

    // ==== Create tab ====
    const btnCreate = $("btn-create-start");
    if (btnCreate) btnCreate.addEventListener("click", () => this._createStart());

    const btnSave = $("btn-create-save");
    if (btnSave) btnSave.addEventListener("click", () => this._createSaveAll());

    const btnSelAll = $("btn-create-select-all");
    if (btnSelAll) btnSelAll.addEventListener("click", () => {
      (this._createResult?.automations || []).forEach((item, i) => {
        if (item.parsed) this._createChecked.add(i);
      });
      this._render();
    });

    const btnDeselAll = $("btn-create-deselect-all");
    if (btnDeselAll) btnDeselAll.addEventListener("click", () => {
      this._createChecked.clear();
      this._render();
    });

    if (this._createResult) {
      (this._createResult.automations || []).forEach((item, i) => {
        // Header click → expand/collapse
        const hdr = $(`auto-hdr-${i}`);
        if (hdr) hdr.addEventListener("click", (e) => {
          if (e.target.type === "checkbox") return;
          if (this._createExpanded.has(i)) this._createExpanded.delete(i);
          else this._createExpanded.add(i);
          this._render();
        });

        // Checkbox
        const chk = $(`auto-chk-${i}`);
        if (chk) chk.addEventListener("change", () => {
          if (chk.checked) this._createChecked.add(i);
          else this._createChecked.delete(i);
          this._render();
        });

        // Refine toggle
        const btnRefineToggle = $(`btn-refine-toggle-${i}`);
        if (btnRefineToggle) btnRefineToggle.addEventListener("click", (e) => {
          e.stopPropagation();
          if (this._createRefineVisible.has(i)) this._createRefineVisible.delete(i);
          else this._createRefineVisible.add(i);
          this._render();
        });

        // Refine submit
        const btnRefine = $(`btn-refine-${i}`);
        if (btnRefine) btnRefine.addEventListener("click", (e) => {
          e.stopPropagation();
          this._createRefine(i);
        });
      });
    }

    // ==== Optimize tab ====
    const optSel = $("opt-select");
    if (optSel) optSel.addEventListener("change", () => {
      this._optimizeSelectedId = optSel.value;
      this._optimizeAnalysis = null;
      this._optimizeGenResult = null;
      this._render();
    });

    const btnOptReload = $("btn-opt-reload");
    if (btnOptReload) btnOptReload.addEventListener("click", () => this._loadAutomations());

    const btnOptAna = $("btn-opt-analyze");
    if (btnOptAna) btnOptAna.addEventListener("click", () => this._optimizeAnalyze());

    const btnOptReana = $("btn-opt-reanalyze");
    if (btnOptReana) btnOptReana.addEventListener("click", () => this._optimizeAnalyze());

    const btnOptGen = $("btn-opt-generate");
    if (btnOptGen) btnOptGen.addEventListener("click", () => this._optimizeGenerate());

    const btnOptRef = $("btn-opt-refine");
    if (btnOptRef) btnOptRef.addEventListener("click", () => this._optimizeRefine());

    const btnOptSave = $("btn-opt-save");
    if (btnOptSave) btnOptSave.addEventListener("click", () => this._optimizeSave());

    const btnDiffSide = $("btn-diff-side");
    if (btnDiffSide) btnDiffSide.addEventListener("click", () => {
      this._optimizeDiffMode = "side";
      this._render();
    });

    const btnDiffInline = $("btn-diff-inline");
    if (btnDiffInline) btnDiffInline.addEventListener("click", () => {
      this._optimizeDiffMode = "inline";
      this._render();
    });

    // ==== Consolidate tab ====
    const btnConsReload = $("btn-cons-reload");
    if (btnConsReload) btnConsReload.addEventListener("click", () => this._loadAutomations());

    const btnDelInaccessible = $("btn-cons-del-inaccessible");
    if (btnDelInaccessible) btnDelInaccessible.addEventListener("click", () => this._deleteInaccessible());

    const btnConsSelAll = $("btn-cons-select-all");
    if (btnConsSelAll) btnConsSelAll.addEventListener("click", () => this._selectAllConsolidate(true));

    const btnConsDeselAll = $("btn-cons-deselect-all");
    if (btnConsDeselAll) btnConsDeselAll.addEventListener("click", () => this._selectAllConsolidate(false));

    const btnConsStartAna = $("btn-cons-start-analyze");
    if (btnConsStartAna) btnConsStartAna.addEventListener("click", () => this._startConsolidateAnalyze());

    // Consolidate checklist checkboxes
    root.querySelectorAll(".consolidate-check-item").forEach(cb => {
      cb.addEventListener("change", () => {
        const aid = cb.dataset.aid;
        if (!this._consolidateSelectedIds) this._consolidateSelectedIds = new Set();
        if (cb.checked) {
          this._consolidateSelectedIds.add(aid);
        } else {
          this._consolidateSelectedIds.delete(aid);
        }
        this._render();
      });
    });

    // Batch bar buttons
    const btnCsAll = $("btn-cs-all");
    if (btnCsAll) btnCsAll.addEventListener("click", () => {
      if (this._consolidatePlan) {
        (this._consolidatePlan.merge_groups || []).forEach((g, i) => {
          this._consolidateApproved[`merge_${i}`] = g;
          this._consolidateSkipped.delete(`merge_${i}`);
        });
        (this._consolidatePlan.fix_items || []).forEach((f, i) => {
          this._consolidateApproved[`fix_${i}`] = f;
          this._consolidateSkipped.delete(`fix_${i}`);
        });
      }
      this._render();
    });
    const btnCsNone = $("btn-cs-none");
    if (btnCsNone) btnCsNone.addEventListener("click", () => {
      if (this._consolidatePlan) {
        (this._consolidatePlan.merge_groups || []).forEach((_, i) => {
          this._consolidateSkipped.add(`merge_${i}`);
          delete this._consolidateApproved[`merge_${i}`];
        });
        (this._consolidatePlan.fix_items || []).forEach((_, i) => {
          this._consolidateSkipped.add(`fix_${i}`);
          delete this._consolidateApproved[`fix_${i}`];
        });
      }
      this._render();
    });
    const btnCsExec = $("btn-cs-execute");
    if (btnCsExec) btnCsExec.addEventListener("click", () => this._consolidateExecute());

    // Per-item checkboxes
    root.querySelectorAll(".cons-item-cb").forEach(cb => {
      cb.addEventListener("click", (e) => {
        e.stopPropagation();
        const key = cb.dataset.key;
        if (!key || !this._consolidatePlan) return;
        const [type, idxStr] = key.split("_");
        const idx = parseInt(idxStr, 10);
        if (cb.checked) {
          if (type === "merge") this._consolidateApproved[key] = this._consolidatePlan.merge_groups[idx];
          else this._consolidateApproved[key] = this._consolidatePlan.fix_items[idx];
          this._consolidateSkipped.delete(key);
        } else {
          this._consolidateSkipped.add(key);
          delete this._consolidateApproved[key];
        }
        this._render();
      });
    });

    const btnConsExec = $("btn-cons-execute");
    if (btnConsExec) btnConsExec.addEventListener("click", () => this._consolidateExecute());

    if (this._consolidatePlan) {
      (this._consolidatePlan.merge_groups || []).forEach((g, i) => {
        const hdr = $(`cons-hdr-merge-${i}`);
        if (hdr) hdr.addEventListener("click", () => {
          const key = `merge_${i}`;
          this._consolidateExpandedYaml[key] = !this._consolidateExpandedYaml[key];
          this._render();
        });
        const btnApp = $(`btn-cons-approve-merge-${i}`);
        if (btnApp) btnApp.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateApproved[`merge_${i}`] = this._consolidatePlan.merge_groups[i];
          this._consolidateSkipped.delete(`merge_${i}`);
          this._render();
        });
        const btnSkp = $(`btn-cons-skip-merge-${i}`);
        if (btnSkp) btnSkp.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateSkipped.add(`merge_${i}`);
          delete this._consolidateApproved[`merge_${i}`];
          this._render();
        });
        const btnRef = $(`btn-cons-refine-merge-${i}`);
        if (btnRef) btnRef.addEventListener("click", (e) => {
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
        const btnApp = $(`btn-cons-approve-fix-${i}`);
        if (btnApp) btnApp.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateApproved[`fix_${i}`] = this._consolidatePlan.fix_items[i];
          this._consolidateSkipped.delete(`fix_${i}`);
          this._render();
        });
        const btnSkp = $(`btn-cons-skip-fix-${i}`);
        if (btnSkp) btnSkp.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateSkipped.add(`fix_${i}`);
          delete this._consolidateApproved[`fix_${i}`];
          this._render();
        });
        const btnRef = $(`btn-cons-refine-fix-${i}`);
        if (btnRef) btnRef.addEventListener("click", (e) => {
          e.stopPropagation();
          this._consolidateRefine("fix", i, f.fixed_yaml);
        });
      });
    }

    // ==== Config tab ====
    const btnToggleApiKey = $("btn-toggle-apikey");
    if (btnToggleApiKey) btnToggleApiKey.addEventListener("click", () => {
      this._showApiKey = !this._showApiKey;
      this._render();
    });

    const btnSaveCfg = $("btn-save-config");
    if (btnSaveCfg) btnSaveCfg.addEventListener("click", () => this._saveConfig());

    // Multi-select dropdowns (area / label / integ)
    const msConfigs = [
      { id: "cfg-area", key: "area_filter", valueKey: "area_id", open: "_areaDropOpen" },
      { id: "cfg-integ", key: "integration_filter", valueKey: "label_id", open: "_integDropOpen" },
      { id: "cfg-label", key: "label_filter", valueKey: "label_id", open: "_labelDropOpen" },
    ];
    for (const mc of msConfigs) {
      const toggleBtn = $(`${mc.id}-toggle`);
      if (toggleBtn) toggleBtn.addEventListener("click", () => {
        this[mc.open] = !this[mc.open];
        this._render();
      });

      root.querySelectorAll(`[data-ms-id="${mc.id}"]`).forEach(chkEl => {
        chkEl.addEventListener("change", () => {
          const val = chkEl.dataset.msVal;
          const current = [...(this._configData[mc.key] || [])];
          if (chkEl.checked) {
            if (!current.includes(val)) current.push(val);
          } else {
            const idx = current.indexOf(val);
            if (idx >= 0) current.splice(idx, 1);
          }
          this._configData[mc.key] = current;
          this._render();
        });
      });

      root.querySelectorAll(`[data-ms-remove="${mc.id}"]`).forEach(btn => {
        btn.addEventListener("click", () => {
          const val = btn.dataset.msVal;
          const current = [...(this._configData[mc.key] || [])];
          const idx = current.indexOf(val);
          if (idx >= 0) {
            current.splice(idx, 1);
            this._configData[mc.key] = current;
            this._render();
          }
        });
      });
    }

    // ==== Knowledge/Backup tab ====
    const btnRefDocs = $("btn-refresh-docs");
    if (btnRefDocs) btnRefDocs.addEventListener("click", () => this._refreshDocs());

    const btnLoadBkp = $("btn-load-backups");
    if (btnLoadBkp) btnLoadBkp.addEventListener("click", () => this._loadBackups());

    const btnClearBkp = $("btn-clear-backups");
    if (btnClearBkp) btnClearBkp.addEventListener("click", () => this._clearBackups());

    // 恢复模式切换
    const btnModeInc = $("btn-mode-incremental");
    if (btnModeInc) btnModeInc.addEventListener("click", () => { this._restoreMode = "incremental"; this._render(); });
    const btnModeOvr = $("btn-mode-overwrite");
    if (btnModeOvr) btnModeOvr.addEventListener("click", () => { this._restoreMode = "overwrite"; this._render(); });

    this._backups.forEach((b, i) => {
      const btnRestore = $(`btn-restore-${i}`);
      if (btnRestore) btnRestore.addEventListener("click", () => this._restoreBackup(b.file));
    });

    // ==== Manage tab ====
    const btnManageReload = $("btn-manage-reload");
    if (btnManageReload) btnManageReload.addEventListener("click", () => this._loadAutomations());

    const btnManageSelAll = $("btn-manage-sel-all");
    if (btnManageSelAll) btnManageSelAll.addEventListener("click", () => {
      (this._automations || []).filter(a => a.id && a.id !== "new" && a.accessible !== false)
        .forEach(a => this._manageChecked.add(a.id));
      this._render();
    });

    const btnManageSelNone = $("btn-manage-sel-none");
    if (btnManageSelNone) btnManageSelNone.addEventListener("click", () => {
      this._manageChecked.clear();
      this._render();
    });

    const btnManageBackup = $("btn-manage-backup");
    if (btnManageBackup) btnManageBackup.addEventListener("click", () => this._manageBackup());

    const btnManageDelete = $("btn-manage-delete");
    if (btnManageDelete) btnManageDelete.addEventListener("click", () => this._manageDelete());

    (this._automations || []).filter(a => a.id && a.id !== "new").forEach(a => {
      const chk = $(`manage-chk-${a.id}`);
      if (chk) chk.addEventListener("change", () => {
        if (chk.checked) this._manageChecked.add(a.id);
        else this._manageChecked.delete(a.id);
        this._render();
      });
    });

    // Doc preview buttons
    root.querySelectorAll("[id^='btn-preview-doc-']").forEach(btn => {
      const key = btn.id.replace("btn-preview-doc-", "");
      btn.addEventListener("click", () => this._previewDoc(key));
    });

    // YAML copy buttons
    root.querySelectorAll(".yaml-copy-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const yaml = btn.dataset.yaml || "";
        navigator.clipboard.writeText(yaml).then(() => {
          this._toast(this._t("toast_copied"), "success");
        }).catch(() => {
          this._toast(this._t("toast_copy_fail"), "error");
        });
      });
    });
  }
}

customElements.define("ha-llm-automation", HaLlmAutomationPanel);
