"use strict";

/* ================= 状态 ================= */
const SAVE_KEY = "resume-app-state-v1";

const state = {
  template: "classic",
  basic: { name: "", target: "", phone: "", email: "", city: "", links: "" },
  summary: "",
  educations: [],
  experiences: [],
  projects: [],
  skills: "",
  self_assessment: "",
  jd: "",
  jdResult: null,
};

const AI = { running: false, abort: null, errorShown: false };

/* ================= 工具 ================= */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), 3200);
}

/* ================= 本地持久化 ================= */
function persist() {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(state)); } catch (e) { /* ignore */ }
}

function loadState() {
  try {
    const s = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (s && typeof s === "object") {
      Object.assign(state, s);
      state.basic = Object.assign({ name: "", target: "", phone: "", email: "", city: "", links: "" }, s.basic || {});
      for (const k of ["educations", "experiences", "projects"]) {
        if (!Array.isArray(state[k])) state[k] = [];
      }
      for (const k of ["summary", "skills", "self_assessment", "jd", "template"]) {
        if (typeof state[k] !== "string" && k !== "template") state[k] = "";
      }
    }
  } catch (e) { /* ignore */ }
}

/* ================= 表单收集与回填 ================= */
const SINGLE_FIELDS = {
  "f-name": ["basic", "name"], "f-target": ["basic", "target"], "f-phone": ["basic", "phone"],
  "f-email": ["basic", "email"], "f-city": ["basic", "city"], "f-links": ["basic", "links"],
  "f-summary": ["summary"], "f-skills": ["skills"], "f-self": ["self_assessment"], "f-jd": ["jd"],
};

function collectForm() {
  for (const [id, path] of Object.entries(SINGLE_FIELDS)) {
    const el = document.getElementById(id);
    const val = el ? el.value : "";
    if (path.length === 2) state[path[0]][path[1]] = val;
    else state[path[0]] = val;
  }
  state.educations = collectEntries("education");
  state.experiences = collectEntries("experience");
  state.projects = collectEntries("project");
}

function collectEntries(type) {
  const box = $(`#sec-${type} [data-list]`);
  if (!box) return [];
  return [...box.querySelectorAll(".entry")].map((row) => {
    const item = {};
    for (const el of row.querySelectorAll("[data-f]")) item[el.dataset.f] = el.value;
    return item;
  });
}

function writeForm() {
  for (const [id, path] of Object.entries(SINGLE_FIELDS)) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.value = path.length === 2 ? state[path[0]][path[1]] : state[path[0]];
  }
}

/* ================= 动态条目 ================= */
function emptyEntry(type) {
  if (type === "education") return { school: "", major: "", degree: "", period: "", description: "" };
  if (type === "experience") return { company: "", position: "", period: "", description: "" };
  return { name: "", role: "", period: "", description: "" };
}

const ENTRY_FIELDS = {
  education: [["school", "学校*"], ["major", "专业"], ["degree", "学历"], ["period", "起止时间"]],
  experience: [["company", "公司*"], ["position", "职位"], ["period", "起止时间"]],
  project: [["name", "项目名*"], ["role", "角色"], ["period", "时间"]],
};

function entryTemplate(type, item, index) {
  const fields = ENTRY_FIELDS[type]
    .map(([k, label]) => `<label>${label}<input data-f="${k}" value="${esc(item[k] || "")}"></label>`)
    .join("");
  return `
    <div class="entry">
      <div class="entry-head">
        <button class="btn mini ai" data-action="polish" data-type="${type}" data-idx="${index}">✨ AI 润色</button>
        <button class="btn mini del" data-action="remove" data-type="${type}" data-idx="${index}">删除</button>
      </div>
      <div class="grid2">${fields}</div>
      <label>描述 / 成就（每行一条要点，可用数字量化）
        <textarea data-f="description" rows="4" placeholder="- 负责…，将…提升 X%&#10;- 主导…，覆盖…用户">${esc(item.description || "")}</textarea>
      </label>
    </div>`;
}

function renderEntries(type) {
  const box = $(`#sec-${type} [data-list]`);
  if (box) box.innerHTML = state[type + "s"].map((it, i) => entryTemplate(type, it, i)).join("");
}

function renderForm() {
  renderEntries("education");
  renderEntries("experience");
  renderEntries("project");
}

/* ================= 预览渲染 ================= */
function bulletsHtml(description) {
  const lines = String(description || "").split("\n").map((l) => l.trim()).filter(Boolean);
  if (!lines.length) return "";
  const lis = lines.map((l) => `<li>${esc(l.replace(/^[-•·*]\s*/, ""))}</li>`).join("");
  return `<ul>${lis}</ul>`;
}

function entryHtml(item, title, sub) {
  const period = esc(item.period || "");
  const head = (title || sub)
    ? `<div class="r-item-head">
         ${title ? `<span class="r-item-title">${esc(title)}</span>` : ""}
         ${sub ? `<span class="r-item-sub">${esc(sub)}</span>` : ""}
         ${period ? `<span class="r-item-period">${period}</span>` : ""}
       </div>`
    : "";
  return `<div class="r-item">${head}<div class="r-item-desc">${bulletsHtml(item.description)}</div></div>`;
}

function sectionHtml(title, body) {
  if (!body) return "";
  return `<section class="r-section"><h2>${title}</h2>${body}</section>`;
}

function buildPreviewHtml() {
  const b = state.basic;
  const contact = [b.phone, b.email, b.city, b.links].filter((x) => x && x.trim());

  const header = `
    <header class="r-header">
      <h1>${esc(b.name) || "（姓名）"}</h1>
      ${contact.length ? `<div class="r-contact">${contact.map(esc).join("　·　")}</div>` : ""}
      ${b.target ? `<div class="r-target"><span>求职意向</span>${esc(b.target)}</div>` : ""}
    </header>`;

  const secSummary = sectionHtml("职业简介", `<p class="r-summary">${esc(state.summary).replace(/\n/g, "<br>")}</p>`);
  const secExp = sectionHtml("工作经历", state.experiences.map((it) => entryHtml(it, "company", "position")).join(""));
  const secProj = sectionHtml("项目经历", state.projects.map((it) => entryHtml(it, "name", "role")).join(""));
  const secEdu = sectionHtml("教育经历", state.educations.map((it) => entryHtml(it, "school", [it.major, it.degree].filter(Boolean).join(" · "))).join(""));
  const secSkills = sectionHtml("技能特长",
    state.skills.trim()
      ? `<div class="r-skills">${state.skills.split("\n").map((s) => s.trim()).filter(Boolean).map((s) => `<span class="r-chip">${esc(s)}</span>`).join("")}</div>`
      : "");
  const secSelf = sectionHtml("自我评价", `<p class="r-summary">${esc(state.self_assessment).replace(/\n/g, "<br>")}</p>`);

  if (state.template === "modern") {
    const left = secEdu + secSkills + secSelf;
    const right = secSummary + secExp + secProj;
    return header + `<div class="r-grid"><div class="r-left">${left}</div><div class="r-right">${right}</div></div>`;
  }
  return header + secSummary + secExp + secProj + secEdu + secSkills + secSelf;
}

function renderPreview() {
  const el = $("#resume-preview");
  el.className = "resume template-" + state.template;
  el.innerHTML = buildPreviewHtml();
}

let renderTimer = null;
function scheduleRender() {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(() => { renderPreview(); persist(); }, 200);
}

/* ================= AI 调用（SSE 流式） ================= */
async function callAI(payload, handlers) {
  const ctrl = new AbortController();
  AI.abort = ctrl;
  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    if (!resp.ok || !resp.body) {
      handlers.onError?.(`请求失败（HTTP ${resp.status}）`, "");
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const raw = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        let event = "message", data = "";
        for (const line of raw.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        if (!data) continue;
        let obj;
        try { obj = JSON.parse(data); } catch (e) { continue; }
        if (event === "delta") handlers.onDelta?.(obj.text || "");
        else if (event === "result") handlers.onResult?.(obj);
        else if (event === "error") handlers.onError?.(obj.message || "未知错误", obj.raw || "");
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") handlers.onError?.(String(e), "");
  }
}

function showOverlay(title) {
  AI.running = true;
  AI.errorShown = false;
  $("#btn-ai-close").textContent = "取消";
  $("#ai-status").textContent = title;
  $("#ai-stream").textContent = "";
  $("#ai-overlay").classList.remove("hidden");
  setBusy(true);
}

function hideOverlay() {
  AI.running = false;
  $("#ai-overlay").classList.add("hidden");
  setBusy(false);
}

function appendStream(text) {
  const el = $("#ai-stream");
  el.textContent = (el.textContent + text).slice(-6000);
  el.scrollTop = el.scrollHeight;
}

function showAiError(msg, raw) {
  AI.errorShown = true;
  $("#ai-status").textContent = "❌ " + msg;
  if (raw) {
    const el = $("#ai-stream");
    el.textContent = (el.textContent || "") + "\n\n—— 原始输出（可手动复制）——\n" + raw;
    el.scrollTop = el.scrollHeight;
  }
  $("#btn-ai-close").textContent = "关闭";
}

function setBusy(busy) {
  for (const id of ["btn-generate-all", "btn-jd-analyze"]) {
    const el = document.getElementById(id);
    if (el) el.disabled = busy;
  }
  for (const el of $$('[data-action="polish"]')) el.disabled = busy;
}

function buildUserData() {
  const arr = (a) => a.map((x) => ({ ...x }));
  return {
    basic: { ...state.basic },
    summary: state.summary,
    educations: arr(state.educations),
    experiences: arr(state.experiences),
    projects: arr(state.projects),
    skills: state.skills.split("\n").map((s) => s.trim()).filter(Boolean),
    self_assessment: state.self_assessment,
    jd: state.jd,
  };
}

/* ================= AI 动作 ================= */
function mergeEntries(orig, aiList, keys) {
  if (!Array.isArray(aiList) || !orig.length) return orig;
  const n = Math.min(orig.length, aiList.length);
  const out = orig.map((o, i) => ({ ...o }));
  for (let i = 0; i < n; i++) {
    const a = aiList[i] || {};
    for (const k of keys) {
      if (a[k] !== undefined && String(a[k]).trim() !== "") out[i][k] = String(a[k]);
    }
    if (Array.isArray(a.bullets)) out[i].description = a.bullets.join("\n");
    else if (a.description !== undefined) out[i].description = String(a.description);
  }
  return out;
}

async function generateAll() {
  if (AI.running) return;
  collectForm();
  showOverlay("AI 正在根据你的经历与 JD 撰写整份简历…");
  await callAI(
    { mode: "full", user_data: buildUserData() },
    {
      onDelta: appendStream,
      onResult: (r) => {
        const d = r.data || {};
        if (d.summary) state.summary = String(d.summary);
        if (Array.isArray(d.educations)) state.educations = mergeEntries(state.educations, d.educations, ["school", "major", "degree", "period"]);
        if (Array.isArray(d.experiences)) state.experiences = mergeEntries(state.experiences, d.experiences, ["company", "position", "period"]);
        if (Array.isArray(d.projects)) state.projects = mergeEntries(state.projects, d.projects, ["name", "role", "period"]);
        if (Array.isArray(d.skills)) state.skills = d.skills.join("\n");
        if (d.self_assessment) state.self_assessment = String(d.self_assessment);
        writeForm();
        renderForm();
        renderPreview();
        persist();
        toast("✅ 已生成并填入表单，可继续手动微调");
      },
      onError: showAiError,
    }
  );
  if (!AI.errorShown) hideOverlay();
}

async function startPolish(type, idx) {
  if (AI.running) return;
  collectForm();
  const labels = {
    summary: "职业简介", skills: "技能特长", self_assessment: "自我评价",
    education: "教育经历", experience: "工作经历", project: "项目经历",
  };
  let entry;
  if (type === "summary" || type === "skills" || type === "self_assessment") {
    entry = { content: state[type === "self_assessment" ? "self_assessment" : type] };
  } else {
    const arr = state[type + "s"];
    if (idx == null || !arr[idx]) { toast("没有可润色的条目"); return; }
    entry = arr[idx];
  }
  showOverlay(`AI 正在润色「${labels[type] || type}」…`);
  await callAI(
    { mode: "module", module: type, entry, context: buildUserData() },
    {
      onDelta: appendStream,
      onResult: (r) => {
        const text = (r.text || "").trim();
        if (!text) return;
        if (type === "summary") state.summary = text;
        else if (type === "skills") state.skills = text;
        else if (type === "self_assessment") state.self_assessment = text;
        else state[type + "s"][idx].description = text;
        writeForm();
        renderForm();
        renderPreview();
        persist();
        toast("✅ 润色完成");
      },
      onError: showAiError,
    }
  );
  if (!AI.errorShown) hideOverlay();
}

async function analyzeJd() {
  if (AI.running) return;
  collectForm();
  if (!state.jd.trim()) { toast("请先粘贴岗位描述（JD）"); return; }
  showOverlay("AI 正在分析 JD 关键词与匹配度…");
  await callAI(
    { mode: "jd", jd: state.jd, user_data: buildUserData() },
    {
      onDelta: appendStream,
      onResult: (r) => {
        state.jdResult = r.data || null;
        renderJdResult();
        persist();
        toast("✅ JD 分析完成");
      },
      onError: showAiError,
    }
  );
  if (!AI.errorShown) hideOverlay();
}

function renderJdResult() {
  const box = $("#jd-result");
  const r = state.jdResult;
  if (!r) return;
  const score = Math.max(0, Math.min(100, Number(r.match_score) || 0));
  const kw = (r.keywords || []).map((k) => `<span class="chip">${esc(k)}</span>`).join("");
  const sug = (r.suggestions || []).map((s) => `<li>${esc(s)}</li>`).join("");
  const hl = (r.highlights || []).map((s) => `<li>${esc(s)}</li>`).join("");
  box.innerHTML = `
    <div class="jd-score">与目标岗位匹配度 <b>${score}%</b>
      <div class="bar"><i style="width:${score}%"></i></div>
    </div>
    <div class="jd-kw">${kw}</div>
    <ul class="jd-list"><b>简历修改建议</b>${sug}</ul>
    <details class="jd-list"><summary><b>JD 重点</b></summary><ul>${hl}</ul></details>`;
  box.classList.remove("hidden");
}

/* ================= 导出 ================= */
function buildResumeForExport() {
  return {
    basic: { ...state.basic },
    summary: state.summary,
    educations: state.educations.map((x) => ({ ...x })),
    experiences: state.experiences.map((x) => ({ ...x })),
    projects: state.projects.map((x) => ({ ...x })),
    skills: state.skills,
    self_assessment: state.self_assessment,
  };
}

async function exportResume(fmt) {
  collectForm();
  const label = fmt === "docx" ? "Word" : "Markdown";
  try {
    const resp = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fmt, resume: buildResumeForExport() }),
    });
    if (!resp.ok) { toast("导出失败（HTTP " + resp.status + "）"); return; }
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = fmt === "docx" ? "我的简历.docx" : "我的简历.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    toast(`✅ 已导出 ${label}（同时保存在 output/ 目录）`);
  } catch (e) {
    toast("导出失败：" + e);
  }
}

/* ================= 设置 ================= */
const PRESETS = {
  deepseek: { base: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  openai: { base: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  siliconflow: { base: "https://api.siliconflow.cn/v1", model: "deepseek-ai/DeepSeek-V3" },
  moonshot: { base: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
  ollama: { base: "http://localhost:11434/v1", model: "qwen2.5:7b" },
};

async function loadSettings() {
  try {
    const r = await fetch("/api/settings");
    const cfg = await r.json();
    $("#s-key").value = cfg.api_key || "";
    $("#s-base").value = cfg.base_url || PRESETS.deepseek.base;
    $("#s-model").value = cfg.model || PRESETS.deepseek.model;
    $("#s-temp").value = cfg.temperature ?? 0.7;
  } catch (e) { /* ignore */ }
}

async function saveSettings() {
  const body = {
    api_key: $("#s-key").value.trim(),
    base_url: $("#s-base").value.trim(),
    model: $("#s-model").value.trim(),
    temperature: parseFloat($("#s-temp").value) || 0.7,
  };
  const r = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.ok) {
    toast(body.api_key ? "✅ 设置已保存" : "✅ 已保存（未填 Key：Ollama 本地模式可用，其他服务需在生成前补填）");
    $("#settings-modal").classList.add("hidden");
  } else {
    toast("保存失败");
  }
}

/* ================= 示例数据 ================= */
const SAMPLE = {
  template: "classic",
  basic: {
    name: "张伟", target: "Python 后端开发工程师", phone: "138-0000-0000",
    email: "zhangwei@example.com", city: "上海", links: "github.com/zhangwei",
  },
  summary: "4 年后端开发经验，深耕 Python 高并发服务与数据管道设计，主导过订单系统重构与微服务拆分，关注工程效率与代码质量。",
  educations: [{
    school: "华东理工大学", major: "计算机科学与技术", degree: "本科",
    period: "2016.09 - 2020.06",
    description: "- 主修课程：数据结构、操作系统、数据库原理\n- 校级二等奖学金，GPA 3.6/4.0",
  }],
  experiences: [{
    company: "某互联网公司", position: "后端开发工程师", period: "2021.07 - 至今",
    description: "- 负责订单系统重构，通过缓存与异步化将核心接口 QPS 从 2k 提升至 8k\n- 主导微服务拆分，上线后线上故障率下降 40%\n- 搭建基于 Prometheus + Grafana 的监控体系，告警响应时间缩短至 5 分钟内",
  }],
  projects: [{
    name: "智能客服机器人", role: "核心开发", period: "2022.03 - 2022.09",
    description: "- 基于 FastAPI + Redis 实现意图识别与多轮对话服务\n- 日均处理 10 万次对话，首响延迟 < 200ms\n- 通过 Pytest 构建自动化测试，覆盖率 85%",
  }],
  skills: "Python\nFastAPI / Django\nMySQL / Redis\nDocker / Kubernetes\nLinux",
  self_assessment: "热爱技术，关注代码质量与工程效率，乐于承担复杂问题；具备良好的沟通与文档能力。",
  jd: "",
};

/* ================= 事件绑定 ================= */
function bindEvents() {
  // 表单输入 → 收集 + 防抖渲染
  $("#form-panel").addEventListener("input", () => { collectForm(); scheduleRender(); });

  // 表单按钮（添加 / 删除 / AI 润色 / JD 分析）
  $("#form-panel").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const { action, type, idx } = btn.dataset;
    collectForm();
    if (action === "add") {
      state[type + "s"].push(emptyEntry(type));
      renderForm(); renderPreview(); persist();
    } else if (action === "remove") {
      state[type + "s"].splice(Number(idx), 1);
      renderForm(); renderPreview(); persist();
    } else if (action === "polish") {
      startPolish(type, idx === undefined ? undefined : Number(idx));
    } else if (action === "jd") {
      analyzeJd();
    }
  });

  // 模板切换
  $("#sel-template").addEventListener("change", (e) => {
    state.template = e.target.value;
    renderPreview(); persist();
  });

  // 顶栏
  $("#btn-generate-all").addEventListener("click", generateAll);
  $("#btn-sample").addEventListener("click", () => {
    Object.assign(state, JSON.parse(JSON.stringify(SAMPLE)));
    writeForm(); renderForm(); renderPreview(); renderJdResult(); persist();
    toast("已填入示例数据");
  });
  $("#btn-clear").addEventListener("click", () => {
    if (!confirm("确定清空所有内容？")) return;
    state.basic = { name: "", target: "", phone: "", email: "", city: "", links: "" };
    state.summary = state.skills = state.self_assessment = state.jd = "";
    state.educations = state.experiences = state.projects = [];
    state.jdResult = null;
    writeForm(); renderForm(); renderPreview();
    $("#jd-result").classList.add("hidden");
    persist();
  });

  // 导出与打印
  $("#btn-export-md").addEventListener("click", () => exportResume("md"));
  $("#btn-export-docx").addEventListener("click", () => exportResume("docx"));
  $("#btn-print").addEventListener("click", () => window.print());

  // AI 浮层
  $("#btn-ai-close").addEventListener("click", () => {
    if (AI.errorShown || !AI.running) { hideOverlay(); return; }
    if (AI.abort) AI.abort.abort();
    hideOverlay();
  });

  // 设置
  $("#btn-settings").addEventListener("click", () => $("#settings-modal").classList.remove("hidden"));
  $("#btn-settings-close").addEventListener("click", () => $("#settings-modal").classList.add("hidden"));
  $("#btn-settings-save").addEventListener("click", saveSettings);
  $("#settings-modal").addEventListener("click", (e) => {
    if (e.target === $("#settings-modal")) $("#settings-modal").classList.add("hidden");
  });
  for (const btn of $$("[data-preset]")) {
    btn.addEventListener("click", () => {
      const p = PRESETS[btn.dataset.preset];
      if (!p) return;
      $("#s-base").value = p.base;
      $("#s-model").value = p.model;
      if (btn.dataset.preset === "ollama") toast("Ollama 模式无需 Key；请确认本地已启动 ollama serve");
    });
  }
}

/* ================= 启动 ================= */
function init() {
  loadState();
  writeForm();
  renderForm();
  renderPreview();
  if (state.jdResult) renderJdResult();
  bindEvents();
  loadSettings();
}

document.addEventListener("DOMContentLoaded", init);
