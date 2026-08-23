"use strict";

/* ================= 状态 ================= */
const SAVE_KEY = "resume-app-state-v1";
const ACTIVE_KEY = "resume-app-active-id";

const state = {
  id: null,                 // 当前简历 id（服务端简历库）
  name: "未命名简历",
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
  scoreResult: null,
};

const ui = {
  library: [],              // [{id, name, updated_at}]
  starOpen: new Set(),      // "type:idx" 集合，记录 STAR 引导是否展开
  dirty: false,             // 是否有未保存修改
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

async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiDelete(url) {
  const r = await fetch(url, { method: "DELETE" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

/* ================= 本地持久化（离线备份） ================= */
function persist() {
  try {
    const s = JSON.parse(JSON.stringify(state));
    delete s.jdResult;
    delete s.scoreResult;
    localStorage.setItem(SAVE_KEY, JSON.stringify(s));
    if (state.id) localStorage.setItem(ACTIVE_KEY, state.id);
  } catch (e) { /* ignore */ }
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
      for (const k of ["summary", "skills", "self_assessment", "jd", "template", "name"]) {
        if (typeof state[k] !== "string" && k !== "template") state[k] = "";
      }
      state.jdResult = null;
      state.scoreResult = null;
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
    const star = { situation: "", task: "", action: "", result: "" };
    for (const el of row.querySelectorAll("[data-star]")) star[el.dataset.star] = el.value;
    item.star = star;
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
  const star = { situation: "", task: "", action: "", result: "" };
  if (type === "education") return { school: "", major: "", degree: "", period: "", description: "" };
  if (type === "experience") return { company: "", position: "", period: "", description: "", star };
  return { name: "", role: "", period: "", description: "", star };
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

  let starHtml = "";
  if (type === "experience" || type === "project") {
    const st = item.star || { situation: "", task: "", action: "", result: "" };
    const open = ui.starOpen.has(`${type}:${index}`);
    starHtml = `
      <div class="star-box">
        <div class="star-head">
          <button class="btn mini" data-action="toggle-star" data-type="${type}" data-idx="${index}">
            ⭐ STAR 引导${open ? "（收起）" : ""}
          </button>
          <span class="star-tip">按 情境/任务/行动/结果 填写素材，AI 自动整合成要点</span>
          <button class="btn mini ai" data-action="star-integrate" data-type="${type}" data-idx="${index}">✨ 整合为要点</button>
        </div>
        <div class="star-fields${open ? "" : " hidden"}">
          <label>情境 Situation（背景/现状）
            <textarea data-star="situation" rows="2" placeholder="当时面临什么情况？">${esc(st.situation || "")}</textarea>
          </label>
          <label>任务 Task（目标/职责）
            <textarea data-star="task" rows="2" placeholder="你负责什么？">${esc(st.task || "")}</textarea>
          </label>
          <label>行动 Action（你做了什么）
            <textarea data-star="action" rows="3" placeholder="采取了哪些行动？用了什么技术/方法？">${esc(st.action || "")}</textarea>
          </label>
          <label>结果 Result（产出/影响）
            <textarea data-star="result" rows="2" placeholder="带来了什么结果？尽量量化，如提升 X%、缩短到 Y 天">${esc(st.result || "")}</textarea>
          </label>
        </div>
      </div>`;
  }

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
      ${starHtml}
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

/* ================= 简历库 ================= */
function renderResumeList() {
  const box = $("#resume-list");
  if (!box) return;
  box.innerHTML = ui.library.map((r) => {
    const active = r.id === state.id ? " active" : "";
    const time = (r.updated_at || "").slice(11, 16);
    return `<div class="resume-item${active}" data-id="${esc(r.id)}" title="${esc(r.name)}">
      <span class="ri-name">${esc(r.name)}</span>
      <span class="ri-time">${esc(time)}</span>
    </div>`;
  }).join("");
}

function setSaveStatus(text) {
  const el = $("#save-status");
  if (el) el.textContent = text;
}

let saveTimer = null;
function scheduleSave() {
  ui.dirty = true;
  clearTimeout(saveTimer);
  setSaveStatus("保存中…");
  saveTimer = setTimeout(saveResumeNow, 800);
}

async function saveResumeNow() {
  clearTimeout(saveTimer);
  if (!ui.dirty) return;
  ui.dirty = false;
  try {
    const res = await apiPost("/api/resumes/save", {
      id: state.id, name: state.name, data: buildResumeData(),
    });
    state.id = res.id;
    state.name = res.name;
    const t = (res.updated_at || "").slice(11, 16);
    setSaveStatus(`✓ ${t} 已保存`);
    persist();
    await refreshLibrary();
  } catch (e) {
    ui.dirty = true;
    setSaveStatus("⚠ 保存失败");
    toast("保存失败：" + e);
  }
}

async function refreshLibrary() {
  try {
    const res = await apiGet("/api/resumes");
    ui.library = res.resumes || [];
  } catch (e) {
    ui.library = [];
  }
  renderResumeList();
}

async function loadResume(id) {
  if (ui.dirty) await saveResumeNow();
  try {
    const r = await apiGet(`/api/resumes/${id}`);
    const d = r.data || {};
    Object.assign(state, {
      id: r.id, name: r.name || "未命名简历",
      template: d.template || "classic",
      basic: Object.assign({ name: "", target: "", phone: "", email: "", city: "", links: "" }, d.basic || {}),
      summary: d.summary || "",
      educations: d.educations || [],
      experiences: d.experiences || [],
      projects: d.projects || [],
      skills: d.skills || "",
      self_assessment: d.self_assessment || "",
      jd: d.jd || "",
      jdResult: null,
      scoreResult: null,
    });
    ui.dirty = false;
    writeForm();
    renderForm();
    renderPreview();
    $("#jd-result").classList.add("hidden");
    renderResumeList();
    persist();
  } catch (e) {
    toast("加载简历失败：" + e);
  }
}

async function newResume() {
  if (ui.dirty) await saveResumeNow();
  state.id = null;
  state.name = `未命名简历 ${ui.library.length + 1}`;
  state.template = "classic";
  state.basic = { name: "", target: "", phone: "", email: "", city: "", links: "" };
  state.summary = state.skills = state.self_assessment = state.jd = "";
  state.educations = state.experiences = state.projects = [];
  state.jdResult = null;
  state.scoreResult = null;
  ui.dirty = true;
  writeForm();
  renderForm();
  renderPreview();
  await saveResumeNow();
}

async function renameResume() {
  const name = prompt("输入新的简历名称：", state.name || "");
  if (name === null) return;
  state.name = name.trim() || state.name;
  ui.dirty = true;
  await saveResumeNow();
}

async function duplicateResume() {
  if (ui.dirty) await saveResumeNow();
  try {
    const res = await apiPost("/api/resumes/save", {
      id: null, name: (state.name || "未命名简历") + " 副本", data: buildResumeData(),
    });
    state.id = res.id;
    state.name = res.name;
    ui.dirty = false;
    await refreshLibrary();
    toast("已创建副本");
  } catch (e) {
    toast("复制失败：" + e);
  }
}

async function deleteResume() {
  if (!state.id) { toast("当前简历尚未保存"); return; }
  if (!confirm(`确定删除「${state.name}」？此操作不可恢复。`)) return;
  try {
    await apiDelete(`/api/resumes/${state.id}`);
    ui.library = ui.library.filter((r) => r.id !== state.id);
    renderResumeList();
    if (ui.library.length) {
      await loadResume(ui.library[0].id);
    } else {
      await newResume();
    }
  } catch (e) {
    toast("删除失败：" + e);
  }
}

async function initLibrary() {
  try {
    await refreshLibrary();
    const activeId = localStorage.getItem(ACTIVE_KEY);
    const target = ui.library.find((r) => r.id === activeId) || ui.library[0];
    if (target) {
      await loadResume(target.id);
      return;
    }
    // 无简历：把本地旧数据迁移成第一份
    const hasContent = state.basic.name || state.summary || state.experiences.length || state.projects.length || state.skills;
    if (hasContent) {
      state.id = null;
      state.name = "我的简历";
      ui.dirty = true;
      await saveResumeNow();
      toast("已将本地数据迁移到简历库");
    } else {
      await newResume();
    }
  } catch (e) {
    // 服务端不可用：离线模式，继续用本地状态
    toast("简历库加载失败，使用本地缓存（离线模式）");
  }
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
  renderTimer = setTimeout(() => {
    renderPreview();
    persist();
    scheduleSave();
  }, 200);
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
        else if (event === "status") handlers.onStatus?.(obj.label || "");
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
  for (const id of ["btn-generate-all", "btn-jd-analyze", "btn-score"]) {
    const el = document.getElementById(id);
    if (el) el.disabled = busy;
  }
  for (const el of $$('[data-action="polish"], [data-action="star-integrate"]')) el.disabled = busy;
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

/* ================= 数据构建 ================= */
function buildResumeData() {
  const arr = (a) => a.map((x) => ({ ...x }));
  return {
    template: state.template,
    basic: { ...state.basic },
    summary: state.summary,
    educations: arr(state.educations),
    experiences: arr(state.experiences),
    projects: arr(state.projects),
    skills: state.skills,
    self_assessment: state.self_assessment,
    jd: state.jd,
  };
}

function buildResumeForExport() {
  const stripStar = (a) => a.map((x) => {
    const { star, ...rest } = x;
    return rest;
  });
  return {
    basic: { ...state.basic },
    summary: state.summary,
    educations: stripStar(state.educations),
    experiences: stripStar(state.experiences),
    projects: stripStar(state.projects),
    skills: state.skills,
    self_assessment: state.self_assessment,
  };
}

/* ================= AI 动作 ================= */
function applyStep(r) {
  const text = (r.text || "").trim();
  if (!text) return;
  if (r.section === "summary") state.summary = text;
  else if (r.section === "skills") state.skills = text;
  else if (r.section === "self_assessment") state.self_assessment = text;
  else if (r.section === "experiences" && state.experiences[r.index]) state.experiences[r.index].description = text;
  else if (r.section === "projects" && state.projects[r.index]) state.projects[r.index].description = text;
  writeForm();
  renderForm();
  renderPreview();
  persist();
  scheduleSave();
}

async function generateAll() {
  if (AI.running) return;
  collectForm();
  showOverlay("AI 开始分步生成整篇简历…");
  await callAI(
    { mode: "full", user_data: buildUserData() },
    {
      onDelta: appendStream,
      onStatus: (label) => {
        $("#ai-status").textContent = label;
        $("#ai-stream").textContent = "";
      },
      onResult: (r) => {
        if (r.mode === "step") applyStep(r);
        else if (r.mode === "score") { state.scoreResult = r.data; renderScore(); }
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
        scheduleSave();
        toast("✅ 润色完成");
      },
      onError: showAiError,
    }
  );
  if (!AI.errorShown) hideOverlay();
}

async function startStarIntegrate(type, idx) {
  if (AI.running) return;
  collectForm();
  const arr = state[type + "s"];
  if (idx == null || !arr[idx]) { toast("没有可整合的条目"); return; }
  const entry = arr[idx];
  const star = entry.star || {};
  if (![star.situation, star.task, star.action, star.result].some((v) => String(v || "").trim())) {
    toast("请先展开 STAR 引导，填写至少一项素材");
    return;
  }
  showOverlay(`AI 正在把 STAR 素材整合为「${type === "experience" ? "工作经历" : "项目经历"}」要点…`);
  await callAI(
    { mode: "star", entry, context: buildUserData() },
    {
      onDelta: appendStream,
      onResult: (r) => {
        const text = (r.text || "").trim();
        if (!text) return;
        arr[idx].description = text;
        writeForm();
        renderForm();
        renderPreview();
        persist();
        scheduleSave();
        toast("✅ 已整合为要点，可继续微调");
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
      onStatus: (label) => { $("#ai-status").textContent = label; },
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

async function analyzeScore() {
  if (AI.running) return;
  collectForm();
  if (!state.basic.name && !state.summary && !state.experiences.length && !state.projects.length) {
    toast("简历还是空的，先填写内容或点「🧪 填入示例」");
    return;
  }
  showOverlay("AI 正在评审简历…");
  await callAI(
    { mode: "score", resume: buildResumeForExport(), jd: state.jd },
    {
      onDelta: appendStream,
      onStatus: (label) => { $("#ai-status").textContent = label; },
      onResult: (r) => {
        state.scoreResult = r.data || null;
        renderScore();
        $("#score-modal").classList.remove("hidden");
        toast("✅ 评分完成");
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

function renderScore() {
  const box = $("#score-body");
  const r = state.scoreResult;
  if (!r) return;
  const overall = Math.max(0, Math.min(100, Number(r.overall_score) || 0));
  const dims = (r.dimensions || []).map((d) => {
    const s = Math.max(0, Math.min(100, Number(d.score) || 0));
    return `<div class="score-dim">
      <div class="score-dim-head"><span>${esc(d.name || "")}</span><b>${s}</b></div>
      <div class="bar"><i style="width:${s}%"></i></div>
      <div class="score-dim-comment">${esc(d.comment || "")}</div>
    </div>`;
  }).join("");
  const strengths = (r.strengths || []).map((s) => `<li>${esc(s)}</li>`).join("");
  const suggestions = (r.suggestions || []).map((s) => `<li>${esc(s)}</li>`).join("");
  box.innerHTML = `
    <div class="score-overall">
      <div class="score-num">${overall}<span>分</span></div>
      <div class="bar big"><i style="width:${overall}%"></i></div>
    </div>
    ${dims ? `<div class="score-dims">${dims}</div>` : ""}
    ${strengths ? `<div class="jd-list"><b>💪 亮点</b><ul>${strengths}</ul></div>` : ""}
    ${suggestions ? `<div class="jd-list"><b>📈 改进建议</b><ul>${suggestions}</ul></div>` : ""}`;
}

/* ================= 导出 ================= */
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
    const cfg = await apiGet("/api/settings");
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
  try {
    await apiPost("/api/settings", body);
    toast(body.api_key ? "✅ 设置已保存" : "✅ 已保存（未填 Key：Ollama 本地模式可用，其他服务需在生成前补填）");
    $("#settings-modal").classList.add("hidden");
  } catch (e) {
    toast("保存失败：" + e);
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
    star: {
      situation: "公司订单系统随业务增长频繁超时，高峰期核心接口 QPS 仅 2k",
      task: "负责订单系统重构，提升吞吐量与稳定性",
      action: "引入 Redis 缓存与异步消息队列，拆分为独立服务并搭建监控",
      result: "QPS 提升至 8k，线上故障率下降 40%",
    },
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
  // 表单输入 → 收集 + 防抖渲染 + 自动保存
  $("#form-panel").addEventListener("input", () => { collectForm(); scheduleRender(); });

  // 表单按钮（添加 / 删除 / AI 润色 / STAR / JD 分析）
  $("#form-panel").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const { action, type, idx } = btn.dataset;
    collectForm();
    if (action === "add") {
      state[type + "s"].push(emptyEntry(type));
      renderForm(); renderPreview(); persist(); scheduleSave();
    } else if (action === "remove") {
      state[type + "s"].splice(Number(idx), 1);
      renderForm(); renderPreview(); persist(); scheduleSave();
    } else if (action === "polish") {
      startPolish(type, idx === undefined ? undefined : Number(idx));
    } else if (action === "jd") {
      analyzeJd();
    } else if (action === "toggle-star") {
      const key = `${type}:${idx}`;
      if (ui.starOpen.has(key)) ui.starOpen.delete(key);
      else ui.starOpen.add(key);
      renderEntries(type);  // 重绘保持输入内容（collectForm 已同步）
    } else if (action === "star-integrate") {
      startStarIntegrate(type, Number(idx));
    }
  });

  // 简历库
  $("#resume-list").addEventListener("click", (e) => {
    const item = e.target.closest(".resume-item");
    if (item && item.dataset.id && item.dataset.id !== state.id) loadResume(item.dataset.id);
  });
  $("#btn-resume-new").addEventListener("click", newResume);
  $("#btn-resume-rename").addEventListener("click", renameResume);
  $("#btn-resume-duplicate").addEventListener("click", duplicateResume);
  $("#btn-resume-delete").addEventListener("click", deleteResume);

  // 模板切换
  $("#sel-template").addEventListener("change", (e) => {
    state.template = e.target.value;
    renderPreview(); persist(); scheduleSave();
  });

  // 顶栏
  $("#btn-generate-all").addEventListener("click", generateAll);
  $("#btn-sample").addEventListener("click", () => {
    Object.assign(state, JSON.parse(JSON.stringify(SAMPLE)));
    ui.dirty = true;
    writeForm(); renderForm(); renderPreview(); renderJdResult(); persist(); scheduleSave();
    toast("已填入示例数据");
  });
  $("#btn-clear").addEventListener("click", () => {
    if (!confirm("确定清空当前简历的所有内容？")) return;
    state.basic = { name: "", target: "", phone: "", email: "", city: "", links: "" };
    state.summary = state.skills = state.self_assessment = state.jd = "";
    state.educations = state.experiences = state.projects = [];
    state.jdResult = null;
    state.scoreResult = null;
    ui.dirty = true;
    writeForm(); renderForm(); renderPreview();
    $("#jd-result").classList.add("hidden");
    persist(); scheduleSave();
  });

  // 导出、评分与打印
  $("#btn-score").addEventListener("click", analyzeScore);
  $("#btn-export-md").addEventListener("click", () => exportResume("md"));
  $("#btn-export-docx").addEventListener("click", () => exportResume("docx"));
  $("#btn-print").addEventListener("click", () => window.print());

  // 评分弹窗
  $("#btn-score-close").addEventListener("click", () => $("#score-modal").classList.add("hidden"));
  $("#score-modal").addEventListener("click", (e) => {
    if (e.target === $("#score-modal")) $("#score-modal").classList.add("hidden");
  });

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
  initLibrary();
}

document.addEventListener("DOMContentLoaded", init);
