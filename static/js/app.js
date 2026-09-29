// ===== 顶栏滚动阴影 =====
window.addEventListener('scroll', () => {
  const topbar = document.getElementById('topbar');
  if (!topbar) return;
  if (window.scrollY > 10) topbar.classList.add('scrolled');
  else topbar.classList.remove('scrolled');
});

// ===== 全局状态 =====
let currentDiagnosis = null;
let practiceQuestions = [];
let practiceIndex = 0;
let practiceCorrect = 0;
let selectedOption = -1;
let answered = false;
let historyCache = null;
let analysisAnimDone = false;
let diagnosisResult = null;
let currentUser = null;
let chatOpen = false;
let notebookData = null;
let currentFilter = 'all';
let uploadedImagePath = null;
let currentSubject = '高等数学';

const API_BASE = '/api';

// ===== Toast 提示 =====
function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => t.classList.remove('show'), 2500);
}

// ===== Token 管理 =====
function getToken() { return localStorage.getItem('token'); }
function setToken(token) { localStorage.setItem('token', token); }
function clearToken() { localStorage.removeItem('token'); currentUser = null; }
function isLoggedIn() { return !!getToken(); }

// ===== API 请求封装 =====
async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error?.message || '请求失败');
  return data;
}

// ===== 列表批量渲染数学公式 =====
function renderMathInList(containerId) {
  if (typeof renderMathInElement !== 'function') return;
  const container = document.getElementById(containerId);
  if (!container) return;
  const targets = container.querySelectorAll('.math-text');
  targets.forEach(function(el) {
    const text = el.textContent || '';
    if (text.includes('$')) {
      renderMathInElement(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false }
        ],
        throwOnError: false
      });
    }
  });
}

// ===== Markdown + KaTeX 渲染 =====
function renderFormatted(text, targetEl) {
  if (!text) { targetEl.innerHTML = ''; return; }

  // 先提取 LaTeX 公式占位，避免后续转义和格式化破坏公式
  const mathStore = [];
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, m) => {
    mathStore.push({ display: true, formula: m });
    return `\x00MATH${mathStore.length - 1}\x00`;
  });
  text = text.replace(/\$([^\$\n]+?)\$/g, (_, m) => {
    mathStore.push({ display: false, formula: m });
    return `\x00MATH${mathStore.length - 1}\x00`;
  });
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_, m) => {
    mathStore.push({ display: false, formula: m });
    return `\x00MATH${mathStore.length - 1}\x00`;
  });
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, m) => {
    mathStore.push({ display: true, formula: m });
    return `\x00MATH${mathStore.length - 1}\x00`;
  });

  // HTML 转义（公式已被保护，不会受影响）
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // 代码块
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre style="background:#1e1e2e;color:#cdd6f4;padding:14px;border-radius:8px;overflow-x:auto;font-size:13px;margin:10px 0">${code.trim()}</pre>`);

  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code style="background:#f0ebde;padding:2px 6px;border-radius:4px;font-size:13px">$1</code>');

  // 标题
  html = html.replace(/^### (.+)$/gm, '<h4 style="font-size:15px;font-weight:600;margin:12px 0 6px;color:var(--ink)">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 style="font-size:16px;font-weight:600;margin:14px 0 8px;color:var(--ink)">$1</h3>');

  // 粗体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 有序列表
  const lines = html.split('\n');
  let inOl = false, inUl = false;
  const result = [];
  for (let line of lines) {
    const olMatch = line.match(/^\s*(\d+)[.、]\s*(.+)/);
    const ulMatch = line.match(/^\s*[-•·]\s*(.+)/);
    if (olMatch) {
      if (inUl) { result.push('</ul>'); inUl = false; }
      if (!inOl) { result.push('<ol style="margin:8px 0 8px 20px;line-height:1.8">'); inOl = true; }
      result.push(`<li>${olMatch[2]}</li>`);
    } else if (ulMatch) {
      if (inOl) { result.push('</ol>'); inOl = false; }
      if (!inUl) { result.push('<ul style="margin:8px 0 8px 20px;line-height:1.8">'); inUl = true; }
      result.push(`<li>${ulMatch[1]}</li>`);
    } else {
      if (inOl) { result.push('</ol>'); inOl = false; }
      if (inUl) { result.push('</ul>'); inUl = false; }
      if (line.trim()) result.push(`<p style="margin:6px 0;line-height:1.8">${line}</p>`);
    }
  }
  if (inOl) result.push('</ol>');
  if (inUl) result.push('</ul>');
  html = result.join('');

  // 还原 LaTeX 公式并用 KaTeX 渲染
  html = html.replace(/\x00MATH(\d+)\x00/g, (_, idx) => {
    const item = mathStore[parseInt(idx)];
    if (!item) return '';
    if (typeof katex !== 'undefined') {
      try {
        return katex.renderToString(item.formula, { displayMode: item.display, throwOnError: false });
      } catch (e) {
        return `<span style="color:var(--danger)">${escapeHtml(item.formula)}</span>`;
      }
    }
    return escapeHtml(item.formula);
  });

  targetEl.innerHTML = html;
}

// ===== 页面导航 =====
function goTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const el = document.getElementById('page-' + pageId);
  if (el) el.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // 返回首页时加载数据
  if (pageId === 'home') {
    loadHomeData();
  }
  if (pageId === 'home' || pageId === 'input') {
    clearInputPage();
  }
}

function clearInputPage(showToast = false) {
  document.getElementById('input-question').value = '';
  document.getElementById('input-student').value = '';
  document.getElementById('input-correct').value = '';
  removeUploadedImage();
  ['question', 'student', 'correct'].forEach(f => {
    const errEl = document.getElementById('err-' + f);
    if (errEl) errEl.classList.remove('show');
    const previewEl = document.getElementById('preview-' + f);
    if (previewEl) previewEl.innerHTML = '';
    // 重置大预览框为占位文字
    const mathPreview = document.getElementById('math-preview-' + f);
    if (mathPreview) mathPreview.innerHTML = '<span class="preview-placeholder">' + (f === 'question' ? '请输入题目，或从左侧拍照上传' : f === 'student' ? '请输入你的作答过程' : '请输入标准答案') + '</span>';
    // 切回预览模式
    const editArea = document.getElementById('edit-area-' + f);
    const previewBox = document.getElementById('preview-box-' + f);
    if (editArea) editArea.style.display = 'none';
    if (previewBox) previewBox.style.display = 'flex';
  });
  currentDiagnosis = null;
  if (showToast) toast('已清空');
}

// ===== 首页数据加载 =====
async function loadHomeData() {
  const classBadge = document.getElementById('class-badge-home');
  if (classBadge) {
    if (isLoggedIn() && currentUser && currentUser.class_code) {
      const className = currentUser.class_name || '未知班级';
      classBadge.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px;background:var(--green-2);color:var(--green);padding:5px 14px;border-radius:20px;font-size:13px;font-weight:600">🏫 ${escapeHtml(className)} <span style="opacity:.6;font-weight:400">(${currentUser.class_code})</span></span>`;
      classBadge.style.display = 'block';
    } else {
      classBadge.style.display = 'none';
    }
  }

  const statTotal = document.getElementById('stat-total');
  const statFinished = document.getElementById('stat-finished');
  const statFav = document.getElementById('stat-fav');
  const trendBars = document.getElementById('trend-bars');
  const weakList = document.getElementById('weak-list');
  const repairBoard = document.getElementById('repair-board');
  const recentList = document.getElementById('recent-list');

  if (!isLoggedIn()) {
    if (statTotal) statTotal.textContent = '—';
    if (statFinished) statFinished.textContent = '—';
    if (statFav) statFav.textContent = '—';
    if (trendBars) trendBars.innerHTML = '<div style="font-size:11px;color:var(--muted);text-align:center;width:100%">登录后查看</div>';
    if (weakList) weakList.innerHTML = '<div style="font-size:12px;color:var(--muted)">登录后查看薄弱点</div>';
    if (repairBoard) repairBoard.innerHTML = '<div class="empty">登录后查看最值得修补的知识点</div>';
    if (recentList) recentList.innerHTML = '<div class="empty">登录后查看最近诊断记录</div>';
    return;
  }

  try {
    const [dashData, histData] = await Promise.all([
      api('/dashboard'),
      api('/history')
    ]);

    const totalDiag = dashData.diagnosis?.total_diagnoses || 0;
    const totalPrac = dashData.practice?.total_sessions || 0;
    const favCount = (histData.records || []).filter(r => r.is_favorite).length;

    if (statTotal) statTotal.textContent = totalDiag;
    if (statFinished) statFinished.textContent = totalPrac;
    if (statFav) statFav.textContent = favCount;

    // 7天活跃度柱形图
    if (trendBars) {
      const records = histData.records || [];
      const days = [];
      for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const dateStr = `${y}-${m}-${day}`;
        const count = records.filter(r => (r.created_at || '').startsWith(dateStr)).length;
        days.push(count);
      }
      const maxCount = Math.max(...days, 1);
      trendBars.innerHTML = days.map(c =>
        `<div class="trend-bar" style="height:${Math.max(c / maxCount * 100, 5)}%" title="${c}次"></div>`
      ).join('');
    }

    // 薄弱点列表（首页卡片内）
    const weaknessData = dashData.weakness_distribution || [];
    if (weakList) {
      if (weaknessData.length === 0) {
        weakList.innerHTML = '<div style="font-size:12px;color:var(--muted)">暂无薄弱点数据</div>';
      } else {
        weakList.innerHTML = weaknessData.slice(0, 3).map(w => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 13px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.5)">
            <span style="font-size:13px;font-weight:600">${escapeHtml(w.weakness)}</span>
            <span style="font-size:11px;color:var(--clay);font-weight:700">${w.count}次</span>
          </div>
        `).join('');
      }
    }

    // 薄弱点分布看板
    const kpStats = dashData.knowledge_stats || [];
    if (repairBoard) {
      if (kpStats.length === 0) {
        repairBoard.innerHTML = '<div class="empty">暂无薄弱点数据，开始诊断后这里会展示最值得修补的知识点</div>';
      } else {
        repairBoard.innerHTML = kpStats.slice(0, 8).map(k => {
          const pct = Math.round((k.avg_mastery || 0) * 100);
          return `
            <div class="repair-card">
              <div class="kp">KP</div>
              <h3>${escapeHtml(k.knowledge_point)}</h3>
              <div class="repair-meter"><i style="width:${pct}%"></i></div>
              <p>掌握度 ${pct}% · ${k.count || 0}次诊断</p>
            </div>
          `;
        }).join('');
      }
    }

    // 最近记录（取4条）
    const records = histData.records || [];
    if (recentList) {
      if (records.length === 0) {
        recentList.innerHTML = '<div class="empty">暂无诊断记录</div>';
      } else {
        recentList.innerHTML = records.slice(0, 4).map(r => {
          const dateStr = r.created_at || '';
          const dateDisplay = dateStr.length >= 16 ? dateStr.slice(5, 16).replace('-', '/') : dateStr;
          return `
            <div class="record-card" onclick="viewHistoryDetail(${r.id})">
              <div>
                <h3 class="math-text">${escapeHtml(r.question || '')}</h3>
                <div class="record-meta">
                  <span class="meta-chip">${escapeHtml(r.knowledge_point || '未知')}</span>
                  <span class="meta-chip">${escapeHtml(r.weakness || '')}</span>
                  <span class="meta-chip">${dateDisplay}</span>
                </div>
              </div>
              <div class="record-tools">
                <button class="icon-btn" onclick="event.stopPropagation();viewHistoryDetail(${r.id})">↗</button>
              </div>
            </div>
          `;
        }).join('');
        // 渲染数学公式
        renderMathInList('recent-list');
      }
    }
  } catch (err) {
    console.error('加载首页数据失败:', err);
  }
}

// ===== 导航栏渲染 =====
function renderNavMenu() {
  const navMenu = document.getElementById('nav-menu');
  const topbar = document.getElementById('topbar');
  if (!navMenu) return;
  if (isLoggedIn() && currentUser) {
    topbar.style.display = 'flex';
    const role = currentUser.role || 'student';
    let navItems = '';
    if (role === 'teacher') {
      navItems = `
        <button onclick="goTo('home')">首页</button>
        <button onclick="loadTeacherPage()">班级管理</button>
        <button onclick="loadGraphPage()">知识图谱</button>
        <button class="ghost-btn" onclick="showUserMenu(event)">${currentUser.nickname} ▾</button>
      `;
    } else {
      const classBadge = currentUser.class_code
        ? `<span style="font-size:11px;color:var(--green);background:var(--green-2);padding:2px 8px;border-radius:6px;margin-left:4px">${escapeHtml(currentUser.class_name || currentUser.class_code)}</span>`
        : '';
      navItems = `
        <button onclick="goTo('home')">首页</button>
        <button onclick="goTo('input')">录题</button>
        <button onclick="loadHistory()">记录</button>
        <button onclick="loadNotebook()">错题本</button>
        <button onclick="loadDashboard()">看板</button>
        <button onclick="loadGraphPage()">知识图谱</button>
        <button class="ghost-btn" onclick="showUserMenu(event)">${currentUser.nickname}${classBadge} ▾</button>
      `;
    }
    navMenu.innerHTML = navItems;
  } else {
    topbar.style.display = 'flex';
    navMenu.innerHTML = `<button onclick="goTo('auth')">登录</button>`;
  }
}

// ===== 角色选择 =====
function selectRole(role) {
  document.getElementById('reg-role').value = role;
  document.querySelectorAll('.role-card').forEach(c => c.classList.toggle('active', c.dataset.role === role));
  const classField = document.getElementById('reg-class-field');
  if (classField) classField.style.display = role === 'student' ? 'block' : 'none';
}

function updateNavForGuest() {
  const topbar = document.getElementById('topbar');
  const navMenu = document.getElementById('nav-menu');
  if (topbar) topbar.style.display = 'flex';
  if (navMenu) {
    navMenu.innerHTML = `<button onclick="goTo('auth')">登录</button>`;
  }
}

// ===== 认证 =====
function switchAuthTab(tab) {
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  document.getElementById('auth-form-login').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('auth-form-register').style.display = tab === 'register' ? 'block' : 'none';
}

function checkRegForm() {
  const pwd = document.getElementById('reg-password').value;
  const pwd2 = document.getElementById('reg-password2').value;
  const hint = document.getElementById('password-strength-hint');

  if (pwd.length === 0) { hint.style.display = 'none'; return; }

  let strength = 0;
  if (pwd.length >= 6) strength++;
  if (pwd.length >= 10) strength++;
  if (/[a-zA-Z]/.test(pwd) && /[0-9]/.test(pwd)) strength++;
  if (/[^a-zA-Z0-9]/.test(pwd)) strength++;

  const levels = ['太弱', '较弱', '中等', '较强', '很强'];
  const colors = ['var(--danger)', 'var(--danger)', 'var(--gold)', 'var(--green)', 'var(--green)'];
  hint.style.display = 'block';
  hint.textContent = `密码强度：${levels[strength]}`;
  hint.style.color = colors[strength];

  if (pwd2 && pwd !== pwd2) {
    hint.textContent += ' | 两次密码不一致';
    hint.style.color = 'var(--danger)';
  }
}

async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  errEl.classList.remove('show');
  if (!username || !password) {
    errEl.textContent = '请输入用户名和密码';
    errEl.classList.add('show');
    return;
  }
  try {
    const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    setToken(data.token);
    currentUser = data.user;
    renderNavMenu();
    goTo('home');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

async function doRegister() {
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const password2 = document.getElementById('reg-password2').value;
  const errEl = document.getElementById('reg-error');
  errEl.classList.remove('show');

  if (!username || !password) {
    errEl.textContent = '请填写所有字段';
    errEl.classList.add('show');
    return;
  }
  if (username.length < 3 || username.length > 20) {
    errEl.textContent = '用户名需要3-20个字符';
    errEl.classList.add('show');
    return;
  }
  if (password.length < 6) {
    errEl.textContent = '密码至少6位';
    errEl.classList.add('show');
    return;
  }
  if (!/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) {
    errEl.textContent = '密码需要包含字母和数字';
    errEl.classList.add('show');
    return;
  }
  if (password !== password2) {
    errEl.textContent = '两次输入的密码不一致';
    errEl.classList.add('show');
    return;
  }

  try {
    const role = document.getElementById('reg-role').value || 'student';
    const classCode = (document.getElementById('reg-class-code') || {}).value || '';
    const data = await api('/auth/register', { method: 'POST', body: JSON.stringify({ username, password, role, class_code: classCode }) });
    setToken(data.token);
    currentUser = data.user;
    renderNavMenu();
    goTo('home');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

function doLogout() {
  clearToken();
  goTo('auth');
}

// ===== 图片上传 + 裁剪 + OCR 识别 =====
let originalImage = null;
let cropSelection = null;
let cropDragging = false;
let cropStart = null;
let autoScanTimer = null;

function handleImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (file.size > 10 * 1024 * 1024) {
    toast('图片大小不能超过10MB');
    return;
  }

  // 上传到服务器（保留原图路径用于诊断记录）
  const formData = new FormData();
  formData.append('file', file);
  fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => { if (data.path) uploadedImagePath = data.path; })
    .catch(err => console.error('图片上传失败:', err));

  // 读取图片并显示裁剪 UI
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = document.getElementById('crop-image');
    originalImage = new Image();
    originalImage.onload = () => {
      document.getElementById('upload-area').style.display = 'none';
      document.getElementById('crop-container').style.display = 'block';
      document.getElementById('crop-hint').style.display = 'block';
      document.getElementById('scan-result').style.display = 'none';
      document.getElementById('scan-loading').style.display = 'none';
      document.getElementById('btn-scan').style.display = 'block';
      document.getElementById('btn-scan').disabled = false;
      document.getElementById('btn-rescan').style.display = 'none';
      cropSelection = null;
      setTimeout(() => {
        setupCropCanvas();
      }, 100);
    };
    originalImage.src = e.target.result;
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function setupCropCanvas() {
  const img = document.getElementById('crop-image');
  const canvas = document.getElementById('crop-overlay');
  const rect = img.getBoundingClientRect();
  if (rect.width === 0) { setTimeout(setupCropCanvas, 100); return; }

  canvas.width = rect.width;
  canvas.height = rect.height;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';

  canvas.onmousedown = onCropStart;
  canvas.onmousemove = onCropMove;
  canvas.onmouseup = onCropEnd;
  canvas.onmouseleave = onCropEnd;
  canvas.ontouchstart = (e) => { e.preventDefault(); onCropStart(e.touches[0]); };
  canvas.ontouchmove = (e) => { e.preventDefault(); onCropMove(e.touches[0]); };
  canvas.ontouchend = onCropEnd;
}

function getCanvasPos(e) {
  const canvas = document.getElementById('crop-overlay');
  const rect = canvas.getBoundingClientRect();
  return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

function onCropStart(e) {
  if (autoScanTimer) { clearTimeout(autoScanTimer); autoScanTimer = null; }
  cropDragging = true;
  cropStart = getCanvasPos(e);
  cropSelection = { x: cropStart.x, y: cropStart.y, w: 0, h: 0 };
}

function onCropMove(e) {
  if (!cropDragging) return;
  const pos = getCanvasPos(e);
  cropSelection = {
    x: Math.min(cropStart.x, pos.x),
    y: Math.min(cropStart.y, pos.y),
    w: Math.abs(pos.x - cropStart.x),
    h: Math.abs(pos.y - cropStart.y)
  };
  drawCropOverlay();
}

function onCropEnd() {
  if (!cropDragging) return;
  cropDragging = false;
  if (cropSelection && (cropSelection.w > 10 && cropSelection.h > 10)) {
    // 用户框选了区域，更新提示文字
    document.getElementById('crop-hint').textContent = '✅ 已框选区域，点击「扫描识别」开始识别';
  } else {
    cropSelection = null;
    drawCropOverlay();
  }
}

function drawCropOverlay() {
  const canvas = document.getElementById('crop-overlay');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!cropSelection) return;

  ctx.fillStyle = 'rgba(0,0,0,0.4)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.clearRect(cropSelection.x, cropSelection.y, cropSelection.w, cropSelection.h);

  ctx.strokeStyle = '#4F6BED';
  ctx.lineWidth = 2;
  ctx.strokeRect(cropSelection.x, cropSelection.y, cropSelection.w, cropSelection.h);

  ctx.fillStyle = '#4F6BED';
  const hs = 6;
  const s = cropSelection;
  ctx.fillRect(s.x - hs/2, s.y - hs/2, hs, hs);
  ctx.fillRect(s.x + s.w - hs/2, s.y - hs/2, hs, hs);
  ctx.fillRect(s.x - hs/2, s.y + s.h - hs/2, hs, hs);
  ctx.fillRect(s.x + s.w - hs/2, s.y + s.h - hs/2, hs, hs);
}

// 加载动画状态
let scanBarTimer = null;
function startScanAnimation() {
  const texts = ['正在上传图片...', 'AI 正在识别文字...', '正在提取数学公式...', '正在拆分题目和答案...'];
  const textEl = document.getElementById('scan-steps-text');
  const barEl = document.getElementById('scan-bar-fill');
  let step = 0;
  let progress = 0;
  textEl.textContent = texts[0];
  barEl.style.width = '5%';
  scanBarTimer = setInterval(() => {
    progress += Math.random() * 15;
    if (progress > 92) progress = 92;
    barEl.style.width = progress + '%';
    const newStep = Math.min(Math.floor(progress / 25), texts.length - 1);
    if (newStep !== step) { step = newStep; textEl.textContent = texts[step]; }
  }, 600);
}
function stopScanAnimation() {
  if (scanBarTimer) { clearInterval(scanBarTimer); scanBarTimer = null; }
  document.getElementById('scan-bar-fill').style.width = '100%';
  setTimeout(() => {
    const textEl = document.getElementById('scan-steps-text');
    if (textEl) textEl.textContent = '识别完成！';
  }, 200);
}

async function scanImage(isAuto) {
  const btn = document.getElementById('btn-scan');
  const loadingEl = document.getElementById('scan-loading');
  const resultEl = document.getElementById('scan-result');

  if (btn) btn.disabled = true;
  loadingEl.style.display = 'block';
  resultEl.style.display = 'none';
  document.getElementById('crop-hint').style.display = 'none';
  document.getElementById('btn-scan').style.display = 'none';
  document.getElementById('btn-rescan').style.display = 'none';

  startScanAnimation();

  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const dispImg = document.getElementById('crop-image');
    const scaleX = originalImage.naturalWidth / dispImg.width;
    const scaleY = originalImage.naturalHeight / dispImg.height;

    if (cropSelection && cropSelection.w > 10 && cropSelection.h > 10) {
      canvas.width = cropSelection.w * scaleX;
      canvas.height = cropSelection.h * scaleY;
      ctx.drawImage(originalImage,
        cropSelection.x * scaleX, cropSelection.y * scaleY,
        cropSelection.w * scaleX, cropSelection.h * scaleY,
        0, 0, canvas.width, canvas.height);
    } else {
      canvas.width = originalImage.naturalWidth;
      canvas.height = originalImage.naturalHeight;
      ctx.drawImage(originalImage, 0, 0);
    }

    const imageB64 = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];

    const resp = await fetch(`${API_BASE}/ocr/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: imageB64, subject: '高等数学' })
    });
    const data = await resp.json();

    stopScanAnimation();

    if (data.error) throw new Error(data.error.message || '识别失败');

    // 自动填入输入框
    if (data.question) {
      document.getElementById('input-question').value = data.question;
      document.getElementById('err-question')?.classList.remove('show');
    }
    if (data.student_answer) {
      document.getElementById('input-student').value = data.student_answer;
      document.getElementById('err-student')?.classList.remove('show');
    }
    if (data.correct_answer) {
      document.getElementById('input-correct').value = data.correct_answer;
      document.getElementById('err-correct')?.classList.remove('show');
    }

    // 更新预览
    updatePreview('input-question');
    updatePreview('input-student');
    updatePreview('input-correct');

    // 切换到预览模式（显示渲染好的数学公式）
    ['question', 'student', 'correct'].forEach(function(field) {
      var editArea = document.getElementById('edit-area-' + field);
      var previewBox = document.getElementById('preview-box-' + field);
      if (editArea && previewBox) {
        editArea.style.display = 'none';
        previewBox.style.display = 'flex';
      }
    });

    // 显示结果卡片（内部已渲染 KaTeX）
    buildResultCard(data);
    document.getElementById('btn-rescan').style.display = 'block';
  } catch (err) {
    stopScanAnimation();
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<div class="scan-error">❌ 识别失败：${err.message}<br>请手动输入题目信息，或重新选择图片</div>`;
    document.getElementById('btn-scan').style.display = 'block';
    document.getElementById('btn-scan').disabled = false;
  } finally {
    loadingEl.style.display = 'none';
  }
}

function buildResultCard(data) {
  let html = '<div class="scan-result-card"><div class="scan-result-title">✅ 识别成功</div>';
  if (data.question) {
    html += `<div class="scan-result-row"><span class="scan-label">题目</span><div class="scan-content scan-math">${escapeHtml(data.question)}</div></div>`;
  }
  if (data.student_answer) {
    html += `<div class="scan-result-row"><span class="scan-label">你的答案</span><div class="scan-content scan-math">${escapeHtml(data.student_answer)}</div></div>`;
  }
  if (data.correct_answer) {
    html += `<div class="scan-result-row"><span class="scan-label">标准答案</span><div class="scan-content scan-math">${escapeHtml(data.correct_answer)}</div></div>`;
  }
  html += '<div class="scan-result-tip">已自动填入下方输入框，预览实时渲染，可直接修改</div></div>';
  const el = document.getElementById('scan-result');
  el.innerHTML = html;
  el.style.display = 'block';
  // 用 KaTeX 渲染识别结果中的数学公式
  el.querySelectorAll('.scan-math').forEach(function(node) {
    if (typeof renderMathInElement === 'function') {
      renderMathInElement(node, {
        delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }],
        throwOnError: false
      });
    }
  });
  return html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function rescanWithCrop() {
  cropSelection = null;
  drawCropOverlay();
  document.getElementById('crop-hint').style.display = 'block';
  document.getElementById('crop-hint').textContent = '✋ 拖拽框选要识别的区域（不选则识别整图）';
  document.getElementById('scan-result').style.display = 'none';
  document.getElementById('btn-rescan').style.display = 'none';
  document.getElementById('btn-scan').style.display = 'block';
  document.getElementById('btn-scan').disabled = false;
}

// 输入框 KaTeX 实时预览（同时更新大预览框和旧版小预览）
function updatePreview(textareaId) {
  const textarea = document.getElementById(textareaId);
  if (!textarea) return;
  const text = textarea.value;

  // 提取字段名：input-xxx → xxx
  const field = textareaId.replace('input-', '');
  const previewEl = document.getElementById('math-preview-' + field);
  if (previewEl) {
    if (!text.trim()) {
      previewEl.innerHTML = '<span class="preview-placeholder">请输入内容</span>';
    } else {
      previewEl.innerHTML = escapeHtml(text);
      if (typeof renderMathInElement === 'function' && text.includes('$')) {
        renderMathInElement(previewEl, {
          delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }],
          throwOnError: false
        });
      }
    }
  }

  // 旧版小预览（兼容已有逻辑）
  const previewId = 'preview-' + textareaId;
  let preview = document.getElementById(previewId);
  if (!preview) {
    preview = document.createElement('div');
    preview.id = previewId;
    preview.className = 'input-preview';
    textarea.parentNode.insertBefore(preview, textarea.nextSibling);
  }
  if (!text.trim()) { preview.style.display = 'none'; return; }
  preview.style.display = 'block';
  if (typeof renderMathInElement === 'function' && text.includes('$')) {
    preview.innerHTML = '<span class="preview-label">效果预览</span>' + escapeHtml(text);
    renderMathInElement(preview, {
      delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }],
      throwOnError: false
    });
  } else {
    preview.innerHTML = '<span class="preview-label">效果预览</span>' + escapeHtml(text);
  }
}

// 切换预览/编辑模式
function toggleEdit(field) {
  const editArea = document.getElementById('edit-area-' + field);
  const previewBox = document.getElementById('preview-box-' + field);
  const textarea = document.getElementById('input-' + field);

  if (editArea.style.display === 'none') {
    editArea.style.display = 'block';
    previewBox.style.display = 'none';
    textarea.focus();
    // 光标移到末尾
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  } else {
    editArea.style.display = 'none';
    previewBox.style.display = 'flex';
  }
}

function resetImageUpload() {
  if (autoScanTimer) { clearTimeout(autoScanTimer); autoScanTimer = null; }
  uploadedImagePath = null;
  originalImage = null;
  cropSelection = null;
  cropDragging = false;

  const fileInput = document.getElementById('input-image');
  if (fileInput) fileInput.value = '';

  document.getElementById('upload-area').style.display = 'block';
  document.getElementById('crop-container').style.display = 'none';
  document.getElementById('input-image').value = '';
  document.getElementById('crop-image').src = '';
  document.getElementById('scan-loading').style.display = 'none';
  document.getElementById('scan-result').style.display = 'none';
  document.getElementById('crop-hint').style.display = 'block';
  document.getElementById('btn-scan').style.display = 'block';
  document.getElementById('btn-scan').disabled = false;
  document.getElementById('btn-rescan').style.display = 'none';
}

function removeUploadedImage() {
  resetImageUpload();
}

// ===== 使用示例题 =====
function useExampleData() {
  goTo('input');
  document.getElementById('input-question').value = '求函数 f(x)=sin(x²) 的导数';
  document.getElementById('input-student').value = "f'(x)=cos(x²)";
  document.getElementById('input-correct').value = "f'(x)=2x cos(x²)";
  removeUploadedImage();
  ['question', 'student', 'correct'].forEach(f => {
    document.getElementById('err-' + f)?.classList.remove('show');
  });
}

// ===== 表单验证 =====
function validateInput() {
  const q = document.getElementById('input-question').value.trim();
  const s = document.getElementById('input-student').value.trim();
  const c = document.getElementById('input-correct').value.trim();
  let valid = true;
  ['question', 'student', 'correct'].forEach(field => {
    document.getElementById('err-' + field).classList.remove('show');
  });
  if (!q) { document.getElementById('err-question').classList.add('show'); valid = false; }
  if (!s) { document.getElementById('err-student').classList.add('show'); valid = false; }
  if (!c) { document.getElementById('err-correct').classList.add('show'); valid = false; }
  return valid;
}

// ===== 开始诊断（SSE 流式 + Loading Layer） =====
async function startDiagnosis() {
  if (!validateInput()) return;
  const btn = document.getElementById('btn-start-diagnosis');
  btn.disabled = true;
  btn.textContent = '诊断中...';

  const question = document.getElementById('input-question').value.trim();
  const studentAnswer = document.getElementById('input-student').value.trim();
  const correctAnswer = document.getElementById('input-correct').value.trim();
  const subject = document.getElementById('input-subject').value;

  analysisAnimDone = false;
  diagnosisResult = null;

  // 显示 Loading Layer
  const layer = document.getElementById('loading-layer');
  const streamOutput = document.getElementById('stream-output');
  const streamText = document.getElementById('stream-text');
  streamOutput.style.display = 'none';
  layer.classList.add('show');
  animateLoading();

  try {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`${API_BASE}/diagnosis/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question, student_answer: studentAnswer, correct_answer: correctAnswer, subject, image_path: uploadedImagePath })
    });

    if (!resp.ok) throw new Error('诊断请求失败');

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') continue;

        try {
          const msg = JSON.parse(payload);

          if (msg.type === 'chunk') {
            if (streamOutput.style.display === 'none') {
              streamOutput.style.display = 'block';
              streamText.textContent = '';
            }
            fullText += msg.content;
            streamText.textContent = fullText.slice(-500);
            if (!analysisAnimDone) {
              document.querySelectorAll('.loading-step').forEach(s => {
                s.classList.remove('active');
                s.classList.add('done');
                s.querySelector('i').textContent = '✓';
              });
              analysisAnimDone = true;
            }
          } else if (msg.type === 'done') {
            diagnosisResult = msg.result;
            streamOutput.style.display = 'none';
            layer.classList.remove('show');
            proceedToReport();
          } else if (msg.type === 'error') {
            throw new Error(msg.message || '诊断失败');
          }
        } catch (e) {
          if (e.message) throw e;
        }
      }
    }

    if (!diagnosisResult) {
      throw new Error('诊断结果未完成');
    }

  } catch (err) {
    toast(err.message);
    layer.classList.remove('show');
  } finally {
    btn.disabled = false;
    btn.textContent = '定位这次错误 →';
    streamOutput.style.display = 'none';
  }
}

function proceedToReport() {
  if (!diagnosisResult) return;
  currentDiagnosis = diagnosisResult;
  renderReport(diagnosisResult);
  historyCache = null;
  document.getElementById('chat-panel-card').style.display = 'block';
  document.getElementById('chat-messages').innerHTML = '';
  chatOpen = false;
  document.getElementById('chat-panel-body').style.display = 'none';
  document.getElementById('practice-wrap').style.display = 'none';
  goTo('report');
}

function showError(message) {
  toast(message || '发生错误');
}

// ===== Loading Layer 动画 =====
function animateLoading() {
  const bar = document.getElementById('progress-bar');
  const steps = [...document.querySelectorAll('.loading-step')];
  bar.style.width = '8%';
  steps.forEach(s => s.className = 'loading-step');
  [0, 1, 2, 3].forEach((idx) => {
    setTimeout(() => {
      steps.forEach((s, i) => {
        if (i < idx) { s.className = 'loading-step done'; s.querySelector('i').textContent = '✓'; }
        else if (i === idx) { s.className = 'loading-step active'; }
      });
      bar.style.width = (25 + idx * 25) + '%';
    }, idx * 420);
  });
}

// ===== 渲染诊断报告 =====
function renderReport(data) {
  // Report Lead
  document.getElementById('report-weakness').textContent = data.weakness;
  document.getElementById('report-lead-text').textContent =
    `这次不需要把整章重学。最值得优先修补的是「${data.weakness}」。`;
  document.getElementById('report-kp').textContent =
    `${data.primary_knowledge_point.id || ''} · ${data.primary_knowledge_point.name}`;
  document.getElementById('report-error-type').textContent =
    `${data.error_type.id || ''} · ${data.error_type.name}`;

  // Side cards
  document.getElementById('priority-text').textContent = data.weakness;
  document.getElementById('mastered-text').textContent =
    data.recommendation?.[0] || '保留当前作答中已经正确的步骤。';

  // Evidence rows
  document.getElementById('evidence-good').textContent =
    data.recommendation?.[0] || '保留已掌握部分。';
  renderFormatted(data.error_reason, document.getElementById('evidence-error'));
  document.getElementById('evidence-impact').textContent =
    `因此本题归为 ${data.error_type.name}，优先修补「${data.weakness}」，而不是把相关知识全部重学。`;

  // Learning path
  renderLearningPath(data.recommendation);

  // Mastery ring
  const masteryPct = Math.round(data.mastery_estimate * 100);
  renderMasteryRing(masteryPct);

  // Related knowledge points
  const relatedCard = document.getElementById('related-card');
  const relatedTags = document.getElementById('related-tags');
  if (data.related_knowledge_points && data.related_knowledge_points.length > 0) {
    relatedCard.style.display = 'block';
    relatedTags.innerHTML = data.related_knowledge_points.map(kp =>
      `<span class="tag accent">${kp.name}</span>`).join('');
  } else {
    relatedCard.style.display = 'none';
  }

  // Favorite button
  const favBtn = document.getElementById('fav-btn');
  if (favBtn && currentDiagnosis) {
    favBtn.textContent = currentDiagnosis.is_favorite ? '★ 已收藏' : '☆ 收藏这道错题';
  }
}

function renderMasteryRing(pct) {
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (pct / 100) * circumference;
  const fillEl = document.getElementById('mastery-fill');
  fillEl.style.strokeDasharray = circumference;
  fillEl.style.strokeDashoffset = circumference;
  setTimeout(() => { fillEl.style.strokeDashoffset = offset; }, 300);
  animateNumber(document.getElementById('mastery-percent'), 0, pct, 1500, '%');
  document.getElementById('mastery-level').textContent = getMasteryLevel(pct);
}

function animateNumber(el, from, to, duration, suffix) {
  const start = Date.now();
  const tick = () => {
    const elapsed = Date.now() - start;
    const progress = Math.min(elapsed / duration, 1);
    const value = Math.round(from + (to - from) * progress);
    el.textContent = value + (suffix || '');
    if (progress < 1) requestAnimationFrame(tick);
  };
  tick();
}

function getMasteryLevel(pct) {
  if (pct <= 40) return '需要重点复习';
  if (pct <= 60) return '需要加强';
  if (pct <= 80) return '基本掌握';
  return '掌握良好';
}

function renderLearningPath(recommendations) {
  if (!recommendations || recommendations.length === 0) {
    document.getElementById('learning-path').innerHTML = '<div class="empty">暂未生成学习建议</div>';
    return;
  }
  const stageLabels = ['保留正确部分', '修补当前薄弱点', '用练习当场验证'];
  document.getElementById('learning-path').innerHTML = recommendations.map((rec, i) => `
    <div class="path-step ${i === 1 ? 'current' : ''}">
      <div class="dot">${i + 1}</div>
      <div>
        <h4>${stageLabels[i] || '下一步'}</h4>
        <p>${rec}</p>
      </div>
    </div>
  `).join('');
}

// ===== 练习逻辑（内嵌在报告页） =====
function showPracticeOptions() {
  if (!currentDiagnosis) { goTo('home'); return; }
  document.getElementById('practice-source-modal').style.display = 'flex';
}

async function startPractice(source = 'auto') {
  if (!currentDiagnosis) { goTo('home'); return; }
  document.getElementById('practice-source-modal').style.display = 'none';
  practiceIndex = 0; practiceCorrect = 0;
  const wrap = document.getElementById('practice-wrap');
  const loadingEl = document.getElementById('practice-loading');
  const mainEl = document.getElementById('practice-main');
  const scoreEl = document.getElementById('score-card');
  wrap.style.display = 'block';
  loadingEl.style.display = 'block';
  mainEl.style.display = 'none';
  scoreEl.classList.remove('show');
  setTimeout(() => wrap.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);

  try {
    const data = await api('/practice', {
      method: 'POST',
      body: JSON.stringify({
        weakness: currentDiagnosis.weakness,
        count: 3,
        diagnosis_id: currentDiagnosis.record_id || null,
        subject: '高等数学',
        source: source
      })
    });
    practiceQuestions = data.questions || [];
    if (practiceQuestions.length === 0) throw new Error('暂无练习题');
    loadingEl.style.display = 'none';
    mainEl.style.display = 'block';
    renderPracticeQuestion();
  } catch (err) {
    loadingEl.style.display = 'none';
    mainEl.style.display = 'none';
    toast('获取练习题失败：' + err.message);
  }
}

async function practiceAgain() {
  const wrap = document.getElementById('practice-wrap');
  const loadingEl = document.getElementById('practice-loading');
  const mainEl = document.getElementById('practice-main');
  const scoreEl = document.getElementById('score-card');
  practiceIndex = 0; practiceCorrect = 0;
  scoreEl.classList.remove('show');
  document.getElementById('score-actions').style.display = 'none';
  loadingEl.style.display = 'block';
  mainEl.style.display = 'none';

  try {
    const data = await api('/practice', {
      method: 'POST',
      body: JSON.stringify({
        weakness: currentDiagnosis.weakness,
        count: 3,
        diagnosis_id: currentDiagnosis.record_id || null,
        subject: '高等数学',
        source: 'auto'
      })
    });
    practiceQuestions = data.questions || [];
    if (practiceQuestions.length === 0) throw new Error('暂无练习题');
    loadingEl.style.display = 'none';
    mainEl.style.display = 'block';
    renderPracticeQuestion();
  } catch (err) {
    loadingEl.style.display = 'none';
    toast('获取练习题失败：' + err.message);
  }
}

function renderPracticeQuestion() {
  const q = practiceQuestions[practiceIndex];
  const topic = currentDiagnosis ? currentDiagnosis.weakness : '链式法则';
  document.getElementById('practice-topic').textContent = `${topic} · 针对性训练`;
  document.getElementById('practice-count').textContent = `第 ${practiceIndex + 1} / ${practiceQuestions.length} 题`;
  document.getElementById('practice-progress').style.width = `${((practiceIndex) / practiceQuestions.length) * 100}%`;

  // 渲染分段进度点
  const dotsEl = document.getElementById('practice-dots');
  if (dotsEl) {
    dotsEl.innerHTML = practiceQuestions.map((_, i) => {
      let cls = 'practice-dot';
      if (i < practiceIndex) cls += ' correct';
      else if (i === practiceIndex) cls += ' active';
      return `<div class="${cls}"></div>`;
    }).join('');
  }

  renderFormatted(q.question, document.getElementById('practice-question'));
  document.getElementById('practice-options').innerHTML = q.options.map((opt, i) => `
    <button class="option" data-idx="${i}" onclick="selectOption(${i})">${String.fromCharCode(65 + i)}. ${escapeHtml(opt)}</button>
  `).join('');
  document.querySelectorAll('.option').forEach(el => {
    if (typeof renderMathInElement !== 'undefined') {
      renderMathInElement(el, { delimiters: [{left:'$',right:'$',display:false}], throwOnError: false });
    }
  });
  const expEl = document.getElementById('practice-explanation');
  expEl.classList.remove('show');
  expEl.innerHTML = '';
  selectedOption = -1; answered = false;
  const btn = document.getElementById('btn-submit-practice');
  btn.textContent = '提交答案'; btn.style.display = 'inline-block';
  btn.disabled = false;
  document.getElementById('btn-next-practice').style.display = 'none';

  const prevBtn = document.getElementById('btn-prev-practice');
  prevBtn.style.display = practiceIndex > 0 ? 'inline-block' : 'none';

  document.getElementById('score-actions').style.display = 'none';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function selectOption(idx) {
  if (answered) return;
  selectedOption = idx;
  document.querySelectorAll('.option').forEach((el, i) => {
    el.classList.toggle('selected', i === idx);
  });
}

function submitPractice() {
  if (!answered) {
    if (selectedOption === -1) { toast('请先选择一个答案'); return; }
    answered = true;
    const q = practiceQuestions[practiceIndex];
    const options = document.querySelectorAll('.option');
    const isCorrect = selectedOption === q.correct;
    if (isCorrect) practiceCorrect++;
    options.forEach((el, i) => {
      el.classList.remove('selected');
      el.classList.add('disabled');
      if (i === q.correct) el.classList.add('correct');
      if (i === selectedOption && !isCorrect) el.classList.add('wrong');
    });

    // 更新进度点颜色
    const dots = document.querySelectorAll('.practice-dot');
    if (dots[practiceIndex]) {
      dots[practiceIndex].classList.remove('active');
      dots[practiceIndex].classList.add(isCorrect ? 'correct' : 'wrong');
    }

    const expEl = document.getElementById('practice-explanation');
    expEl.innerHTML = `<strong>${isCorrect ? '✅ 正确' : '❌ 错误'}</strong><br>`;
    const expContent = document.createElement('div');
    expContent.className = 'formatted-content';
    expEl.appendChild(expContent);
    renderFormatted(q.explanation || '暂无解答', expContent);
    expEl.classList.add('show');
    const btn = document.getElementById('btn-submit-practice');
    btn.style.display = 'none';
    const nextBtn = document.getElementById('btn-next-practice');
    nextBtn.style.display = 'inline-block';
    nextBtn.textContent = practiceIndex < practiceQuestions.length - 1 ? '下一题 →' : '查看结果 →';
  }
}

function nextPractice() {
  practiceIndex++;
  if (practiceIndex < practiceQuestions.length) renderPracticeQuestion();
  else showPracticeResult();
}

function prevPractice() {
  if (practiceIndex > 0) {
    practiceIndex--;
    renderPracticeQuestion();
  }
}

function showPracticeResult() {
  const score = practiceCorrect;
  const total = practiceQuestions.length;
  const scoreCard = document.getElementById('score-card');
  document.getElementById('score-text').textContent = `${score}/${total}`;
  document.getElementById('score-advice').textContent =
    score >= 2 ? '这一轮已经达到验证标准。如果这道题已收藏，下一次复盘会自动拉长间隔。'
    : '当前薄弱点还需要一次短复盘。如果这道题已收藏，系统会把下一次复盘安排得更近。';
  scoreCard.classList.add('show');

  document.getElementById('practice-progress').style.width = '100%';
  document.getElementById('btn-next-practice').style.display = 'none';
  document.getElementById('btn-submit-practice').style.display = 'none';
  document.getElementById('btn-prev-practice').style.display = 'none';

  document.getElementById('score-actions').style.display = 'flex';

  const weakness = currentDiagnosis ? currentDiagnosis.weakness : '该知识点';
  const accuracy = Math.round((score / total) * 100);
  if (currentDiagnosis && currentDiagnosis.record_id) {
    api('/practice/record', {
      method: 'POST',
      body: JSON.stringify({ diagnosis_id: currentDiagnosis.record_id, weakness, accuracy, total, correct: score, subject: '高等数学', results: practiceQuestions.map((q, i) => ({ correct: i < practiceCorrect })) })
    }).catch(err => console.error('保存练习记录失败:', err));
  }
}

// ===== AI 追问 =====
function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById('chat-panel-body').style.display = chatOpen ? 'block' : 'none';
  document.getElementById('chat-arrow').textContent = chatOpen ? '▲' : '▼';
  if (chatOpen && currentDiagnosis && currentDiagnosis.record_id) {
    loadChatHistory();
  }
}

async function loadChatHistory() {
  try {
    const data = await api(`/chat/${currentDiagnosis.record_id}`);
    const container = document.getElementById('chat-messages');
    if (data.messages.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:var(--muted);font-size:13px;padding:20px">向 AI 老师提问，深入理解这道题</div>';
      return;
    }
    container.innerHTML = '';
    for (const m of data.messages) {
      const msgEl = createChatMsg(m.role, m.content);
      container.appendChild(msgEl);
    }
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    console.error('加载对话历史失败:', err);
  }
}

function createChatMsg(role, content) {
  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `chat-msg ${isUser ? 'user' : 'ai'}`;
  div.innerHTML = `<div class="cm-avatar">${isUser ? '我' : 'AI'}</div><div class="cm-bubble formatted-content"></div>`;
  const bubble = div.querySelector('.cm-bubble');
  if (isUser) {
    bubble.textContent = content;
  } else {
    renderFormatted(content, bubble);
  }
  return div;
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message || !currentDiagnosis || !currentDiagnosis.record_id) return;

  const sendBtn = document.getElementById('chat-send-btn');
  sendBtn.disabled = true;

  const container = document.getElementById('chat-messages');
  container.appendChild(createChatMsg('user', message));
  input.value = '';
  container.scrollTop = container.scrollHeight;

  // 显示"正在思考"
  const typingDiv = document.createElement('div');
  typingDiv.className = 'chat-msg ai';
  typingDiv.innerHTML = '<div class="cm-avatar">AI</div><div class="cm-bubble" style="color:var(--muted)">正在思考...</div>';
  container.appendChild(typingDiv);
  container.scrollTop = container.scrollHeight;

  try {
    const data = await api(`/chat/${currentDiagnosis.record_id}`, {
      method: 'POST',
      body: JSON.stringify({ message })
    });
    typingDiv.remove();
    container.appendChild(createChatMsg('assistant', data.reply));
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    typingDiv.querySelector('.cm-bubble').textContent = '回答失败：' + err.message;
    typingDiv.querySelector('.cm-bubble').style.color = 'var(--danger)';
  } finally {
    sendBtn.disabled = false;
  }
}

// ===== 从报告页收藏 =====
async function toggleFavoriteFromReport() {
  if (!currentDiagnosis || !currentDiagnosis.record_id) { toast('无法收藏'); return; }
  const next = !(currentDiagnosis.is_favorite);
  try {
    await api(`/history/${currentDiagnosis.record_id}/favorite`, { method: 'POST', body: JSON.stringify({ is_favorite: next }) });
    currentDiagnosis.is_favorite = next;
    document.getElementById('fav-btn').textContent = next ? '★ 已收藏' : '☆ 收藏这道错题';
    toast(next ? '已加入错题收藏' : '已取消收藏');
  } catch (err) {
    toast('操作失败：' + err.message);
  }
}

// ===== 历史记录 =====
async function loadHistory() {
  const listEl = document.getElementById('history-list');
  const searchEl = document.getElementById('history-search');
  const q = searchEl ? searchEl.value.trim() : '';
  listEl.innerHTML = '<div class="empty">加载中...</div>';
  goTo('history');
  try {
    const data = await api('/history');
    let records = data.records || [];
    if (q) {
      records = records.filter(r =>
        (r.question || '').includes(q) ||
        (r.knowledge_point || '').includes(q) ||
        (r.weakness || '').includes(q)
      );
    }
    historyCache = records;
    renderHistoryList(records);
  } catch (err) {
    listEl.innerHTML = `<div class="empty">${err.message}</div>`;
  }
}

function renderHistoryList(records) {
  const listEl = document.getElementById('history-list');
  if (!records || records.length === 0) {
    listEl.innerHTML = '<div class="empty"><div style="font-size:36px;margin-bottom:10px;opacity:.4">📝</div>暂无诊断记录<br><span style="font-size:12px">开始你的第一次诊断吧！</span></div>';
    return;
  }
  listEl.innerHTML = records.map(r => {
    const dateStr = r.created_at || '';
    let dateDisplay = dateStr.length >= 16 ? dateStr.slice(5, 16).replace('-', '/') : dateStr;
    const errShort = (r.result_json ? JSON.parse(r.result_json).error_reason : r.error_reason) || '';
    const errDisplay = errShort.length > 80 ? errShort.slice(0, 80) + '...' : errShort;
    return `
      <div class="record-card" onclick="viewHistoryDetail(${r.id})">
        <div>
          <h3 class="math-text">${escapeHtml(r.question || '')}</h3>
          <p>${escapeHtml(errDisplay)}</p>
          <div class="record-meta">
            <span class="meta-chip">${escapeHtml(r.knowledge_point || '未知')}</span>
            <span class="meta-chip">${escapeHtml(r.weakness || '')}</span>
            <span class="meta-chip">${dateDisplay}</span>
          </div>
        </div>
        <div class="record-tools">
          <button class="icon-btn" onclick="event.stopPropagation();viewHistoryDetail(${r.id})">↗</button>
        </div>
      </div>
    `;
  }).join('');

  // 批量渲染数学公式
  renderMathInList('history-list');
}

async function viewHistoryDetail(recordId) {
  try {
    const data = await api(`/history/${recordId}`);
    currentDiagnosis = data.result;
    currentDiagnosis.record_id = data.id;
    renderReport(currentDiagnosis);
    document.getElementById('chat-panel-card').style.display = 'block';
    document.getElementById('chat-messages').innerHTML = '';
    chatOpen = false;
    document.getElementById('chat-panel-body').style.display = 'none';
    goTo('report');
  } catch (err) {
    toast('获取诊断详情失败：' + err.message);
  }
}

// ===== 错题本 =====
async function loadNotebook() {
  const listEl = document.getElementById('notebook-list');
  const filterEl = document.getElementById('notebook-filters');
  listEl.innerHTML = '<div class="empty">加载中...</div>';
  goTo('notebook');

  try {
    const data = await api('/history');
    notebookData = data.records || [];

    if (notebookData.length === 0) {
      filterEl.innerHTML = '';
      listEl.innerHTML = '<div class="empty"><div style="font-size:36px;margin-bottom:10px;opacity:.4">📖</div>错题本还是空的<br><span style="font-size:12px">去诊断一道题吧！</span></div>';
      return;
    }

    const kps = [...new Set(notebookData.map(r => r.knowledge_point).filter(k => k))];
    filterEl.innerHTML = `<div class="filter-chip active" onclick="filterNotebook('all', this)">全部 (${notebookData.length})</div>` +
      kps.map(kp => `<div class="filter-chip" onclick="filterNotebook('kp:${kp}', this)">${kp}</div>`).join('') +
      `<div class="filter-chip" onclick="filterNotebook('favorite', this)">⭐ 收藏</div>` +
      `<button class="solid-btn" style="padding:8px 14px;font-size:12px;margin-left:auto" onclick="exportNotebookPDF()">📄 导出PDF</button>`;
    currentFilter = 'all';
    renderNotebookList(notebookData);
  } catch (err) {
    listEl.innerHTML = `<div class="empty">${err.message}</div>`;
  }
}

function filterNotebook(filter, el) {
  currentFilter = filter;
  document.querySelectorAll('#notebook-filters .filter-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  let filtered = notebookData;
  if (filter === 'favorite') filtered = notebookData.filter(r => r.is_favorite);
  else if (filter.startsWith('kp:')) filtered = notebookData.filter(r => r.knowledge_point === filter.slice(3));
  renderNotebookList(filtered);
}

function renderNotebookList(records) {
  const listEl = document.getElementById('notebook-list');
  if (!records || records.length === 0) {
    listEl.innerHTML = '<div class="empty">该筛选下暂无记录</div>';
    return;
  }
  listEl.innerHTML = records.map(r => {
    const dateStr = r.created_at || '';
    let dateDisplay = dateStr.length >= 16 ? dateStr.slice(5, 16).replace('-', '/') : dateStr;
    const notesDisplay = r.notes ? `<div class="note">复盘备注：${escapeHtml(r.notes)}</div>` : '';
    return `
      <div class="record-card notebook-item" data-id="${r.id}">
        <div onclick="viewHistoryDetail(${r.id})">
          <h3 class="math-text">${escapeHtml(r.question || '')}</h3>
          <p>${escapeHtml(r.knowledge_point || '未知')} · ${escapeHtml(r.weakness || '')}</p>
          <div class="record-meta">
            <span class="meta-chip">${dateDisplay}</span>
            <span class="meta-chip">${Math.round((r.mastery_estimate || 0) * 100)}% 掌握</span>
            ${r.is_favorite ? '<span class="meta-chip" style="background:var(--clay-2);color:var(--gold)">⭐ 收藏</span>' : ''}
          </div>
          ${notesDisplay}
        </div>
        <div class="record-tools">
          <button class="icon-btn" title="收藏" onclick="event.stopPropagation();toggleFavorite(${r.id}, ${!r.is_favorite}, this)">${r.is_favorite ? '⭐' : '☆'}</button>
          <button class="icon-btn" title="备注" onclick="event.stopPropagation();toggleNotes(${r.id})">✎</button>
          <button class="icon-btn" title="删除" onclick="event.stopPropagation();deleteRecord(${r.id}, this)">🗑</button>
        </div>
        <div class="notes-editor" id="notes-editor-${r.id}" style="display:none">
          <textarea class="textarea" id="notes-input-${r.id}" placeholder="写一句复盘备注..." rows="2">${escapeHtml(r.notes || '')}</textarea>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button class="solid-btn" style="padding:6px 12px;font-size:12px" onclick="saveNotes(${r.id})">保存</button>
            <button class="ghost-btn" style="padding:6px 12px;font-size:12px" onclick="document.getElementById('notes-editor-${r.id}').style.display='none'">取消</button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  // 批量渲染数学公式
  renderMathInList('notebook-list');
}

async function toggleFavorite(recordId, isFav, el) {
  try {
    await api(`/history/${recordId}/favorite`, { method: 'POST', body: JSON.stringify({ is_favorite: isFav }) });
    el.textContent = isFav ? '⭐' : '☆';
    if (notebookData) {
      const r = notebookData.find(r => r.id === recordId);
      if (r) r.is_favorite = isFav;
    }
    toast(isFav ? '已收藏' : '已取消收藏');
  } catch (err) {
    toast('操作失败：' + err.message);
  }
}

function toggleNotes(recordId) {
  const editor = document.getElementById('notes-editor-' + recordId);
  if (editor.style.display === 'none') {
    editor.style.display = 'block';
    setTimeout(() => document.getElementById('notes-input-' + recordId)?.focus(), 100);
  } else {
    editor.style.display = 'none';
  }
}

async function saveNotes(recordId) {
  const notes = document.getElementById('notes-input-' + recordId).value.trim();
  try {
    await api(`/history/${recordId}/notes`, { method: 'POST', body: JSON.stringify({ notes }) });
    document.getElementById('notes-editor-' + recordId).style.display = 'none';
    if (notebookData) {
      const r = notebookData.find(r => r.id === recordId);
      if (r) r.notes = notes;
    }
    toast('备注已保存');
  } catch (err) {
    toast('保存失败：' + err.message);
  }
}

async function deleteRecord(recordId, btn) {
  if (!confirm('确定删除这条记录吗？删除后不可恢复。')) return;
  try {
    await api(`/history/${recordId}`, { method: 'DELETE' });
    notebookData = notebookData.filter(r => r.id !== recordId);
    historyCache = null;
    const item = btn.closest('.record-card');
    item.style.opacity = '0';
    item.style.transform = 'translateX(-20px)';
    setTimeout(() => item.remove(), 300);
    toast('记录已删除');
  } catch (err) {
    toast('删除失败：' + err.message);
  }
}

// ===== 学习看板 =====
async function loadDashboard() {
  goTo('dashboard');
  try {
    const data = await api('/dashboard');
    renderDashboard(data);
  } catch (err) {
    document.getElementById('dashboard-stats').innerHTML = `<div class="empty-state">${err.message}</div>`;
  }
}

function renderDashboard(data) {
  const diag = data.diagnosis || {};
  const prac = data.practice || {};
  const totalDiag = diag.total_diagnoses || 0;
  const avgMastery = diag.avg_mastery ? Math.round(diag.avg_mastery * 100) : 0;
  const totalSessions = prac.total_sessions || 0;
  const avgAccuracy = prac.avg_accuracy ? Math.round(prac.avg_accuracy) : 0;
  const favorites = diag.favorites || 0;

  // 概览卡片（带进度条）
  document.getElementById('dashboard-stats').innerHTML = `
    <div class="dash-stat green">
      <div class="ds-icon">📝</div>
      <div class="ds-value">${totalDiag}</div>
      <div class="ds-label">累计诊断次数</div>
      <div class="ds-bar"><i style="width:${Math.min(totalDiag * 10, 100)}%"></i></div>
    </div>
    <div class="dash-stat gold">
      <div class="ds-icon">📊</div>
      <div class="ds-value">${avgMastery}%</div>
      <div class="ds-label">平均掌握度</div>
      <div class="ds-bar"><i style="width:${avgMastery}%"></i></div>
    </div>
    <div class="dash-stat blue">
      <div class="ds-icon">🎯</div>
      <div class="ds-value">${totalSessions}</div>
      <div class="ds-label">练习次数</div>
      <div class="ds-bar"><i style="width:${Math.min(totalSessions * 20, 100)}%"></i></div>
    </div>
    <div class="dash-stat clay">
      <div class="ds-icon">✅</div>
      <div class="ds-value">${avgAccuracy}%</div>
      <div class="ds-label">平均练习正确率</div>
      <div class="ds-bar"><i style="width:${avgAccuracy}%"></i></div>
    </div>
  `;

  // 掌握度趋势
  const trendData = data.mastery_trend || [];
  const trendEl = document.getElementById('mastery-trend-chart');
  if (trendData.length > 0) {
    const chart1 = echarts.init(trendEl);
    chart1.setOption({
      tooltip: { trigger: 'axis', formatter: p => `第${p[0].dataIndex + 1}次诊断<br/>掌握度: ${p[0].value}%` },
      xAxis: { type: 'category', data: trendData.map((_, i) => `第${i + 1}次`), axisLabel: { fontSize: 11, color: '#7b8a84' }, axisLine: { lineStyle: { color: '#e4ddd0' } } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%', fontSize: 11, color: '#7b8a84' }, splitLine: { lineStyle: { color: '#f0ebe0' } } },
      series: [{
        data: trendData.map(d => Math.round(d.mastery_estimate * 100)),
        type: 'line', smooth: true,
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(40,91,73,0.25)' }, { offset: 1, color: 'rgba(40,91,73,0.02)' }] } },
        lineStyle: { color: '#285b49', width: 3 },
        itemStyle: { color: '#285b49', borderColor: '#fff', borderWidth: 2 },
        symbolSize: 8
      }],
      grid: { left: 40, right: 15, top: 15, bottom: 30 }
    });
  } else {
    trendEl.innerHTML = '<div class="empty-state"><div class="es-icon">📈</div><div class="es-title">暂无掌握度数据</div><div class="es-desc">完成第一次诊断后，这里会展示你的掌握度变化趋势</div></div>';
  }

  // 知识点掌握详情（进度条）
  const kpStats = data.knowledge_stats || [];
  const kpBarsEl = document.getElementById('knowledge-bars');
  if (kpStats.length === 0) {
    kpBarsEl.innerHTML = '<div class="empty-state"><div class="es-icon">📚</div><div class="es-title">暂无知识点数据</div><div class="es-desc">完成诊断后，这里会展示各知识点的掌握详情</div></div>';
  } else {
    kpBarsEl.innerHTML = kpStats.slice(0, 12).map(k => {
      const pct = Math.round((k.avg_mastery || 0) * 100);
      const color = pct >= 70 ? 'var(--green)' : pct >= 40 ? 'var(--gold)' : 'var(--clay)';
      return `
        <div class="kp-bar-item">
          <span class="kp-name">${escapeHtml(k.knowledge_point)}</span>
          <span class="kp-val" style="color:${color}">${pct}%</span>
          <div class="kp-bar-track"><i style="width:${pct}%;background:${color}"></i></div>
        </div>
      `;
    }).join('');
  }

  // 雷达图
  const radarEl = document.getElementById('radar-chart');
  if (kpStats.length >= 3) {
    const chart2 = echarts.init(radarEl);
    chart2.setOption({
      tooltip: { formatter: p => p.value.map((v, i) => `${kpStats[i]?.knowledge_point || ''}: ${v}%`).join('<br/>') },
      radar: {
        indicator: kpStats.slice(0, 8).map(k => ({ name: k.knowledge_point.length > 6 ? k.knowledge_point.slice(0, 6) + '…' : k.knowledge_point, max: 100 })),
        shape: 'polygon',
        splitArea: { areaStyle: { color: ['rgba(40,91,73,0.03)', 'rgba(40,91,73,0.06)'] } },
        axisName: { fontSize: 11, color: '#7b8a84' },
        splitLine: { lineStyle: { color: '#e4ddd0' } },
        axisLine: { lineStyle: { color: '#e4ddd0' } }
      },
      series: [{
        type: 'radar',
        data: [{
          value: kpStats.slice(0, 8).map(k => Math.round(k.avg_mastery * 100)),
          name: '掌握度',
          areaStyle: { color: 'rgba(40,91,73,0.15)' },
          lineStyle: { color: '#285b49', width: 2 },
          itemStyle: { color: '#285b49' }
        }]
      }]
    });
  } else {
    radarEl.innerHTML = '<div class="empty-state"><div class="es-icon">🎯</div><div class="es-title">数据不足</div><div class="es-desc">至少诊断3个不同知识点后，雷达图会展示你的知识覆盖面</div></div>';
  }

  // 练习正确率趋势
  const practiceTrend = data.practice_trend || [];
  const ptEl = document.getElementById('practice-trend-chart');
  if (practiceTrend.length > 0) {
    const chart3 = echarts.init(ptEl);
    chart3.setOption({
      tooltip: { trigger: 'axis', formatter: p => `第${p[0].dataIndex + 1}次练习<br/>正确率: ${p[0].value}%` },
      xAxis: { type: 'category', data: practiceTrend.map((_, i) => `第${i + 1}次`), axisLabel: { fontSize: 11, color: '#7b8a84' }, axisLine: { lineStyle: { color: '#e4ddd0' } } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%', fontSize: 11, color: '#7b8a84' }, splitLine: { lineStyle: { color: '#f0ebe0' } } },
      series: [{
        data: practiceTrend.map(d => d.accuracy || 0),
        type: 'bar',
        barWidth: '40%',
        itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#b96549' }, { offset: 1, color: '#f3e3dc' }] }, borderRadius: [6, 6, 0, 0] }
      }],
      grid: { left: 40, right: 15, top: 15, bottom: 30 }
    });
  } else {
    ptEl.innerHTML = '<div class="empty-state"><div class="es-icon">✅</div><div class="es-title">暂无练习记录</div><div class="es-desc">完成练习后，这里会展示你的正确率变化趋势</div></div>';
  }

  // 薄弱点分布
  const weaknessData = data.weakness_distribution || [];
  const weaknessEl = document.getElementById('weakness-distribution');
  if (weaknessEl) {
    if (weaknessData.length === 0) {
      weaknessEl.innerHTML = '<div class="empty-state"><div class="es-icon">🔍</div><div class="es-title">暂无薄弱点数据</div><div class="es-desc">完成诊断后，系统会自动统计你的高频薄弱点</div></div>';
    } else {
      const maxCount = Math.max(...weaknessData.map(w => w.count));
      weaknessEl.innerHTML = weaknessData.map(w => `
        <div class="weakness-bar">
          <div class="wb-name">${escapeHtml(w.weakness)}</div>
          <div class="wb-bar-bg"><div class="wb-bar-fill" style="width:${(w.count / maxCount) * 100}%"></div></div>
          <div class="wb-count">${w.count}</div>
        </div>
      `).join('');
    }
  }

  // ===== 智能学习建议 =====
  const adviceEl = document.getElementById('dash-advice-body');
  if (adviceEl) {
    const adviceList = [];

    // 1. 优先修补建议（掌握度最低的知识点）
    if (kpStats.length > 0) {
      const weakest = [...kpStats].sort((a, b) => (a.avg_mastery || 0) - (b.avg_mastery || 0));
      const w1 = weakest[0];
      const w1Pct = Math.round((w1.avg_mastery || 0) * 100);
      if (w1Pct < 40) {
        adviceList.push({
          level: 'urgent', icon: '!',
          title: `优先修补「${w1.knowledge_point}」`,
          desc: `当前掌握度仅 ${w1Pct}%，这是你最薄弱的知识点。建议先看教材对应章节，再做一道相关错题诊断。`
        });
      } else if (w1Pct < 70) {
        adviceList.push({
          level: 'warning', icon: '↑',
          title: `巩固「${w1.knowledge_point}」`,
          desc: `掌握度 ${w1Pct}%，还有提升空间。建议做 2-3 道针对性练习巩固。`
        });
      }
    }

    // 2. 练习正确率趋势建议
    if (practiceTrend.length >= 2) {
      const recent = practiceTrend.slice(-2);
      if (recent[1].accuracy >= recent[0].accuracy + 20) {
        adviceList.push({
          level: 'good', icon: '↑',
          title: '进步明显！可以挑战更难的题',
          desc: `最近两次练习正确率从 ${recent[0].accuracy}% 提升到 ${recent[1].accuracy}%，建议尝试更高难度的题目。`
        });
      } else if (recent[1].accuracy < recent[0].accuracy - 20) {
        adviceList.push({
          level: 'warning', icon: '↓',
          title: '最近练习正确率下降',
          desc: `正确率从 ${recent[0].accuracy}% 降到 ${recent[1].accuracy}%，建议重新复习相关知识点后再练习。`
        });
      }
    }

    // 3. 诊断频次建议
    if (totalDiag === 0) {
      adviceList.push({
        level: 'urgent', icon: '!',
        title: '还没有诊断记录',
        desc: '录入一道错题开始诊断，系统会帮你定位第一次偏离的位置并给出修补路径。'
      });
    } else if (totalDiag >= 5 && avgMastery < 50) {
      adviceList.push({
        level: 'warning', icon: '☉',
        title: '诊断次数不少，但整体掌握度偏低',
        desc: '建议放慢节奏，每道错题诊断后认真完成 3 道验证练习，确保真正修补。'
      });
    } else if (totalDiag >= 10) {
      adviceList.push({
        level: 'good', icon: '★',
        title: '已经积累了丰富的学习数据',
        desc: `共完成 ${totalDiag} 次诊断，平均掌握度 ${avgMastery}%。可以导出错题本 PDF 做阶段性复习。`
      });
    }

    // 4. 收藏错题提醒
    if (favorites === 0 && totalDiag > 0) {
      adviceList.push({
        level: 'warning', icon: '☆',
        title: '还没有收藏错题',
        desc: '去错题本收藏重要错题，方便后续复盘。导出 PDF 随时打印复习。'
      });
    }

    if (adviceList.length === 0) {
      adviceEl.innerHTML = '<div class="dac-empty">继续保持！当前学习状态良好 🎉</div>';
    } else {
      adviceEl.innerHTML = adviceList.map(a => `
        <div class="dac-item">
          <div class="dac-level dac-level-${a.level}">${a.icon}</div>
          <div class="dac-text">
            <b>${escapeHtml(a.title)}</b>
            <p>${escapeHtml(a.desc)}</p>
          </div>
        </div>
      `).join('');
    }
  }
}

// ===== 导出错题本 PDF =====
function exportNotebookPDF() {
  const records = notebookData;
  if (!records || records.length === 0) {
    toast('错题本为空，无法导出');
    return;
  }

  // 筛选当前过滤后的记录
  let toExport = records;
  if (currentFilter === 'favorite') toExport = records.filter(r => r.is_favorite);
  else if (currentFilter.startsWith('kp:')) toExport = records.filter(r => r.knowledge_point === currentFilter.slice(3));

  if (toExport.length === 0) {
    toast('当前筛选下无错题可导出');
    return;
  }

  // 构建打印区域
  const dateStr = new Date().toLocaleDateString('zh-CN');
  const printArea = document.createElement('div');
  printArea.id = 'pdf-print-area';
  printArea.style.cssText = 'position:fixed;left:-9999px;top:0;width:800px;background:#fff;padding:30px';

  let html = `
    <div class="pdf-header">
      <h1>知径 · 高数错题本</h1>
      <p>导出日期：${dateStr} ｜ 共 ${toExport.length} 道错题</p>
    </div>
  `;

  toExport.forEach((r, i) => {
    const masteryPct = Math.round((r.mastery_estimate || 0) * 100);
    html += `
      <div class="pdf-item" style="page-break-inside:avoid;margin-bottom:20px;padding:16px;border:1px solid #e4ddd0;border-radius:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <span style="font-size:14px;font-weight:600;color:#17352b">第 ${i + 1} 题</span>
          <span style="font-size:11px;color:#7b8a84">${r.knowledge_point || ''} · ${masteryPct}% 掌握</span>
        </div>
        <div class="pdf-q"><div class="pdf-q-label">题目</div><div class="pdf-q-content">${escapeHtml(r.question || '')}</div></div>
        <div class="pdf-q"><div class="pdf-q-label">我的作答</div><div class="pdf-q-content">${escapeHtml(r.student_answer || '')}</div></div>
        <div class="pdf-q"><div class="pdf-q-label">正确答案</div><div class="pdf-q-content">${escapeHtml(r.correct_answer || '')}</div></div>
        <div class="pdf-q"><div class="pdf-q-label">薄弱点</div><div class="pdf-q-content" style="color:#b96549;font-weight:600">${escapeHtml(r.weakness || '')}</div></div>
        <div class="pdf-divider"></div>
        <div class="pdf-q"><div class="pdf-q-label">诊断分析</div><div class="pdf-q-content">${escapeHtml(r.error_reason || '')}</div></div>
        ${r.notes ? `<div class="pdf-q"><div class="pdf-q-label">备注</div><div class="pdf-q-content">${escapeHtml(r.notes)}</div></div>` : ''}
      </div>
    `;
  });

  printArea.innerHTML = html;
  document.body.appendChild(printArea);

  // 触发打印
  window.print();

  // 打印后清理
  setTimeout(() => {
    document.body.removeChild(printArea);
  }, 500);
}

// ===== 用户菜单 + 班级管理 =====
function showUserMenu(e) {
  e.stopPropagation();
  closeUserMenu();
  const menu = document.createElement('div');
  menu.id = 'user-dropdown';
  const role = currentUser.role || 'student';
  let items = '';
  if (role === 'student') {
    const classLabel = currentUser.class_code
      ? `班级：${currentUser.class_name || currentUser.class_code}`
      : '尚未加入班级';
    items += `<div class="ud-item" onclick="closeUserMenu();showClassManager()"><span>🏫</span> ${classLabel}</div>`;
  }
  items += `<div class="ud-item ud-danger" onclick="closeUserMenu();doLogout()"><span>⏻</span> 退出登录</div>`;
  menu.innerHTML = items;
  menu.style.cssText = 'position:fixed;top:60px;right:20px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 0;box-shadow:var(--shadow-lg);z-index:200;min-width:180px;animation:fadeIn .15s ease';
  document.body.appendChild(menu);
  setTimeout(() => document.addEventListener('click', closeUserMenu, { once: true }), 0);
}

function closeUserMenu() {
  const m = document.getElementById('user-dropdown');
  if (m) m.remove();
}

function showClassManager() {
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:200;display:flex;align-items:center;justify-content:center;animation:fadeIn .2s ease';
  overlay.setAttribute('data-overlay', '');
  const currentClass = currentUser.class_code;
  overlay.innerHTML = `
    <div style="background:var(--card);border-radius:20px;padding:28px;width:min(440px,90%);box-shadow:var(--shadow-xl)">
      <h3 style="font-size:18px;font-weight:700;margin-bottom:16px">🏫 班级管理</h3>
      ${currentClass
        ? `<div style="background:var(--green-2);border-radius:12px;padding:14px;margin-bottom:16px">
            <div style="font-size:13px;color:var(--muted);margin-bottom:4px">当前班级</div>
            <div style="font-size:18px;font-weight:700;color:var(--green)">${escapeHtml(currentUser.class_name || '未知班级')}</div>
            <div style="font-size:12px;color:var(--muted);margin-top:2px">班级码：${currentClass}</div>
          </div>
          <button class="ghost-btn btn-block" style="margin-bottom:12px" onclick="leaveClass()">退出当前班级</button>`
        : `<div style="background:var(--paper);border-radius:12px;padding:14px;margin-bottom:16px;text-align:center;color:var(--muted);font-size:14px">你还没有加入任何班级</div>`
      }
      <div style="border-top:1px solid var(--line);padding-top:16px;margin-top:4px">
        <label style="font-size:14px;font-weight:600;display:block;margin-bottom:8px">加入新班级</label>
        <div style="display:flex;gap:8px">
          <input type="text" class="form-input" id="dialog-class-code" placeholder="输入班级码" style="flex:1;text-transform:uppercase">
          <button class="solid-btn" id="dialog-join-btn">加入</button>
        </div>
        ${currentClass ? '<p style="font-size:12px;color:var(--muted);margin-top:8px">加入新班级将自动退出当前班级</p>' : ''}
      </div>
      <div style="text-align:right;margin-top:16px">
        <button class="ghost-btn" onclick="this.closest('[data-overlay]').remove()">关闭</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  const input = document.getElementById('dialog-class-code');
  input.focus();
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') document.getElementById('dialog-join-btn').click(); });
  document.getElementById('dialog-join-btn').onclick = async () => {
    const code = input.value.trim().toUpperCase();
    if (!code) { toast('请输入班级码'); return; }
    overlay.remove();
    await joinClass(code);
  };
}

async function joinClass(code) {
  try {
    const data = await api('/student/join-class', { method: 'POST', body: JSON.stringify({ class_code: code }) });
    currentUser.class_code = code;
    currentUser.class_name = data.class?.name || null;
    renderNavMenu();
    toast(`已加入班级 ${currentUser.class_name || code}`);
  } catch (err) {
    toast(err.message);
  }
}

async function leaveClass() {
  try {
    await api('/student/join-class', { method: 'POST', body: JSON.stringify({ class_code: '' }) });
    currentUser.class_code = null;
    document.querySelector('[data-overlay]')?.remove();
    renderNavMenu();
    toast('已退出班级');
  } catch (err) {
    toast(err.message);
  }
}

// ===== 教师功能 =====
let currentClassCode = null;

async function loadTeacherPage() {
  goTo('teacher');
  if (!isLoggedIn()) {
    toast('请先登录');
    goTo('auth');
    return;
  }
  if (!currentUser) {
    try {
      const data = await api('/auth/me');
      currentUser = data.user;
    } catch (err) {
      toast('请重新登录');
      goTo('auth');
      return;
    }
  }
  if (currentUser.role !== 'teacher') {
    toast('仅教师可访问此页面');
    goTo('home');
    return;
  }
  try {
    const data = await api('/teacher/classes');
    renderClassList(data.classes || []);
  } catch (err) {
    toast('加载班级列表失败');
  }
}

function renderClassList(classes) {
  const container = document.getElementById('teacher-class-list');
  const detailEl = document.getElementById('teacher-detail');
  const listEl = document.getElementById('teacher-classes');
  listEl.style.display = 'block';
  detailEl.style.display = 'none';

  if (!classes.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">📚</div><p>还没有班级，点击上方按钮创建</p></div>`;
    return;
  }
  container.innerHTML = classes.map(c => `
    <div class="card" style="padding:18px;cursor:pointer" onclick="viewClassDetail('${c.code}')">
      <div style="display:flex;justify-content:space-between;align-items:start">
        <div>
          <h3 style="font-size:17px;font-weight:600;margin-bottom:4px">${escapeHtml(c.name)}</h3>
          <p style="color:var(--muted);font-size:13px">班级码：<b style="color:var(--green);letter-spacing:1px">${c.code}</b></p>
        </div>
        <div style="text-align:right">
          <div style="font-size:24px;font-weight:700;color:var(--green)">${c.student_count}</div>
          <div style="font-size:12px;color:var(--muted)">学生</div>
        </div>
      </div>
    </div>
  `).join('');
}

function showCreateClassDialog() {
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:200;display:flex;align-items:center;justify-content:center;animation:fadeIn .2s ease';
  overlay.innerHTML = `
    <div style="background:var(--card);border-radius:20px;padding:28px;width:min(420px,90%);box-shadow:var(--shadow-xl)">
      <h3 style="font-size:18px;font-weight:700;margin-bottom:16px">创建班级</h3>
      <input type="text" class="form-input" id="dialog-class-name" placeholder="输入班级名称（如：2025级高数A班）" style="margin-bottom:16px">
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button class="ghost-btn" onclick="this.closest('[data-overlay]').remove()">取消</button>
        <button class="solid-btn" id="dialog-create-btn">创建</button>
      </div>
    </div>
  `;
  overlay.setAttribute('data-overlay', '');
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  const input = document.getElementById('dialog-class-name');
  input.focus();
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') document.getElementById('dialog-create-btn').click(); });
  document.getElementById('dialog-create-btn').onclick = async () => {
    const name = input.value.trim();
    if (!name) { toast('请输入班级名称'); return; }
    overlay.remove();
    await createClass(name);
  };
}

async function createClass(name) {
  try {
    await api('/teacher/class', { method: 'POST', body: JSON.stringify({ name }) });
    toast('班级创建成功');
    loadTeacherPage();
  } catch (err) {
    toast(err.message);
  }
}

async function viewClassDetail(code) {
  currentClassCode = code;
  document.getElementById('teacher-classes').style.display = 'none';
  document.getElementById('teacher-detail').style.display = 'block';

  try {
    const data = await api(`/teacher/class/${code}`);
    const cls = data.class_info;
    const dash = data.dashboard;

    document.getElementById('teacher-class-name').textContent = cls.name;
    document.getElementById('teacher-class-meta').textContent =
      `班级码：${cls.code} · ${dash.total_students} 名学生 · ${dash.total_diagnoses} 次诊断`;

    // 概览卡片
    const statsRow = document.getElementById('teacher-stats-row');
    statsRow.innerHTML = `
      <div class="stat-card"><div class="stat-num">${dash.total_students}</div><div class="stat-label">学生人数</div></div>
      <div class="stat-card"><div class="stat-num">${dash.total_diagnoses}</div><div class="stat-label">累计诊断</div></div>
      <div class="stat-card"><div class="stat-num">${dash.weakness_distribution.length}</div><div class="stat-label">薄弱点种类</div></div>
      <div class="stat-card"><div class="stat-num">${dash.knowledge_distribution.length}</div><div class="stat-label">涉及知识点</div></div>
    `;

    // 薄弱点图表
    renderTeacherWeaknessChart(dash.weakness_distribution);
    // 知识点分布
    renderTeacherKpChart(dash.knowledge_distribution);
    // 学生列表
    renderStudentList(dash.student_stats);
  } catch (err) {
    toast('加载班级详情失败');
  }
}

function renderTeacherWeaknessChart(data) {
  const el = document.getElementById('teacher-weakness-chart');
  if (!data || !data.length) {
    el.innerHTML = '<div class="empty-state"><p>暂无薄弱点数据</p></div>';
    return;
  }
  const top5 = data.slice(0, 5);
  el.innerHTML = top5.map((w, i) => {
    const pct = Math.min(100, w.count * 10);
    const colors = ['#9d493d', '#b96549', '#b68842', '#536a66', '#285b49'];
    return `
      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <span style="font-size:13px;font-weight:500">${i + 1}. ${escapeHtml(w.weakness)}</span>
          <span style="font-size:13px;color:var(--muted)">${w.count}次</span>
        </div>
        <div style="height:8px;background:var(--paper);border-radius:4px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:${colors[i]};border-radius:4px;transition:width .6s ease"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderTeacherKpChart(data) {
  const el = document.getElementById('teacher-kp-chart');
  if (!data || !data.length) {
    el.innerHTML = '<div class="empty-state"><p>暂无知识点数据</p></div>';
    return;
  }
  if (typeof echarts === 'undefined') {
    el.innerHTML = top5Html(data);
    return;
  }
  const chart = echarts.init(el);
  chart.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}: {c}次' },
    grid: { left: 100, right: 30, top: 10, bottom: 20 },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#e4ddd0' } } },
    yAxis: { type: 'category', data: data.map(d => d.knowledge_point).reverse(), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: data.map(d => d.count).reverse(),
      itemStyle: { color: '#285b49', borderRadius: [0, 4, 4, 0] },
      barWidth: 16
    }]
  });
}

function top5Html(data) {
  return data.slice(0, 8).map(d => `
    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line)">
      <span style="font-size:13px">${escapeHtml(d.knowledge_point)}</span>
      <span style="font-size:13px;color:var(--muted)">${d.count}次</span>
    </div>
  `).join('');
}

function renderStudentList(students) {
  const el = document.getElementById('teacher-student-list');
  if (!students || !students.length) {
    el.innerHTML = '<div class="empty-state"><p>暂无学生数据</p></div>';
    return;
  }
  el.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="border-bottom:2px solid var(--line)">
          <th style="text-align:left;padding:8px">学生</th>
          <th style="text-align:center;padding:8px">诊断次数</th>
          <th style="text-align:center;padding:8px">平均掌握度</th>
        </tr>
      </thead>
      <tbody>
        ${students.map(s => {
          const mastery = s.avg_mastery ? Math.round(s.avg_mastery * 100) : 0;
          const color = mastery >= 70 ? '#285b49' : mastery >= 40 ? '#b68842' : '#9d493d';
          return `
            <tr style="border-bottom:1px solid var(--line)">
              <td style="padding:8px">${escapeHtml(s.nickname || s.username)}</td>
              <td style="text-align:center;padding:8px">${s.diag_count || 0}</td>
              <td style="text-align:center;padding:8px">
                <span style="font-weight:600;color:${color}">${mastery}%</span>
              </td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function backToClassList() {
  document.getElementById('teacher-classes').style.display = 'block';
  document.getElementById('teacher-detail').style.display = 'none';
}

// ===== 知识图谱 =====
let graphChart = null;
let graphData = null;
let graphAllNodes = null;

async function loadGraphPage() {
  goTo('graph');
  if (!graphData) {
    try {
      graphData = await api('/knowledge-graph');
      populateChapterFilter(graphData.nodes);
    } catch (err) {
      toast('加载知识图谱失败');
      return;
    }
  }
  renderGraph();
}

function populateChapterFilter(nodes) {
  const select = document.getElementById('graph-chapter-filter');
  const chapters = [...new Set(nodes.map(n => n.chapter))];
  select.innerHTML = '<option value="">全部章节</option>' +
    chapters.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}

function renderGraph() {
  const container = document.getElementById('graph-container');
  if (!container || !graphData) return;

  if (typeof echarts === 'undefined') {
    container.innerHTML = '<p style="text-align:center;color:var(--muted)">需要加载 ECharts 库</p>';
    return;
  }

  if (graphChart) graphChart.dispose();
  graphChart = echarts.init(container);

  const chapterFilter = document.getElementById('graph-chapter-filter').value;
  const visibleNodes = chapterFilter
    ? graphData.nodes.filter(n => n.chapter === chapterFilter)
    : graphData.nodes;
  const visibleIds = new Set(visibleNodes.map(n => n.id));

  const nodes = visibleNodes.map(n => {
    const mastery = n.mastery || 0;
    let color = '#7b8a84';
    if (mastery >= 70) color = '#285b49';
    else if (mastery >= 40) color = '#b68842';
    else if (mastery > 0) color = '#b96549';
    const diff = n.difficulty || 1;
    const stars = '⭐'.repeat(diff);
    let statusIcon = '○';
    if (mastery >= 70) statusIcon = '✓';
    else if (mastery > 0) statusIcon = '!';
    return {
      id: n.id,
      name: n.name,
      symbolSize: mastery > 0 ? 38 + mastery * 0.25 : 30,
      itemStyle: { color, borderColor: mastery > 0 ? color : '#d0d0d0', borderWidth: 2 },
      label: { fontSize: 11,
        formatter: `{name|${n.name}}\n{status|${statusIcon} ${stars}}`,
        rich: { name: { fontSize: 11, color: '#333' }, status: { fontSize: 9, color: '#999' } }
      },
      data: n
    };
  });

  const links = graphData.edges
    .filter(e => visibleIds.has(e.from) && visibleIds.has(e.to))
    .map(e => ({ source: e.from, target: e.to }));

  graphChart.setOption({
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'node') {
          const d = params.data.data;
          const masteryText = d.mastery ? `掌握度：${d.mastery}%` : '暂无数据';
          const diffStars = '⭐'.repeat(d.difficulty || 1);
          const diagText = d.diag_count ? `诊断次数：${d.diag_count}` : '尚无诊断记录';
          return `<b>${d.name}</b> ${diffStars}<br/>${d.chapter}<br/>${masteryText}<br/>${diagText}`;
        }
        return '';
      }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      roam: true,
      draggable: true,
      force: { repulsion: 220, edgeLength: [100, 140], gravity: 0.08 },
      label: { show: true, position: 'right', fontSize: 11 },
      edgeStyle: { color: '#ccc', width: 1.5, curveness: 0.1 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3, color: '#285b49' } }
    }]
  });

  graphChart.on('click', (params) => {
    if (params.dataType === 'node') {
      showGraphDetail(params.data.data);
    }
  });
}

function filterGraph() {
  renderGraph();
}

function searchGraph() {
  const query = document.getElementById('graph-search').value.trim().toLowerCase();
  if (!query || !graphData) { renderGraph(); return; }

  const matched = graphData.nodes.filter(n =>
    n.name.toLowerCase().includes(query) ||
    (n.keywords && n.keywords.some(k => k.toLowerCase().includes(query)))
  );

  if (!matched.length) {
    toast('未找到匹配的知识点');
    return;
  }

  if (matched.length === 1) {
    showGraphDetail(matched[0]);
    return;
  }

  const matchedIds = new Set(matched.map(n => n.id));
  const container = document.getElementById('graph-container');
  if (graphChart) graphChart.dispose();
  graphChart = echarts.init(container);

  const nodes = graphData.nodes.map(n => {
    const isMatch = matchedIds.has(n.id);
    const mastery = n.mastery || 0;
    let color = '#7b8a84';
    if (mastery >= 70) color = '#285b49';
    else if (mastery >= 40) color = '#b68842';
    else if (mastery > 0) color = '#b96549';
    return {
      id: n.id, name: n.name,
      symbolSize: isMatch ? 50 : 20,
      itemStyle: { color: isMatch ? color : '#e0e0e0', borderColor: isMatch ? '#285b49' : 'transparent', borderWidth: isMatch ? 3 : 0 },
      label: { fontSize: isMatch ? 13 : 10, color: isMatch ? '#17352b' : '#bbb' },
      data: n
    };
  });
  const links = graphData.edges.map(e => ({ source: e.from, target: e.to }));

  graphChart.setOption({
    tooltip: { formatter: p => p.dataType === 'node' ? `<b>${p.data.data.name}</b>` : '' },
    series: [{ type: 'graph', layout: 'force', data: nodes, links, roam: true, draggable: true,
      force: { repulsion: 220, edgeLength: [80, 120], gravity: 0.08 },
      label: { show: true, position: 'right' },
      edgeStyle: { color: '#eee', width: 1 },
      emphasis: { focus: 'adjacency' }
    }]
  });
  graphChart.on('click', p => { if (p.dataType === 'node') showGraphDetail(p.data.data); });
}

function highlightLearningPath() {
  if (!graphData) { toast('图谱未加载'); return; }

  const weakNodes = graphData.nodes.filter(n => n.mastery > 0 && n.mastery < 40);
  if (!weakNodes.length) {
    const hintBar = document.getElementById('graph-smart-hint');
    hintBar.style.display = 'flex';
    hintBar.innerHTML = '<span style="color:var(--green)">✓ 暂无薄弱知识点，继续保持！</span>';
    hintBar.style.background = 'var(--green-2)';
    setTimeout(() => { hintBar.style.display = 'none'; }, 4000);
    return;
  }

  const weakest = weakNodes.reduce((a, b) => a.mastery < b.mastery ? a : b);

  const pathNodes = new Set([weakest.id]);
  const pathEdges = [];
  function traceBack(nid) {
    for (const edge of graphData.edges) {
      if (edge.to === nid) {
        pathNodes.add(edge.from);
        pathEdges.push({ source: edge.from, target: edge.to });
        traceBack(edge.from);
      }
    }
  }
  traceBack(weakest.id);

  const hintBar = document.getElementById('graph-smart-hint');
  hintBar.style.display = 'flex';
  hintBar.style.background = 'var(--clay-2)';
  hintBar.innerHTML = `<span style="color:var(--clay)">🧭 建议路径：你的薄弱点「<b>${escapeHtml(weakest.name)}</b>」掌握度仅 ${weakest.mastery}%，建议从前置知识开始修补（图中高亮路径）</span>`;

  const container = document.getElementById('graph-container');
  if (graphChart) graphChart.dispose();
  graphChart = echarts.init(container);

  const nodes = graphData.nodes.map(n => {
    const mastery = n.mastery || 0;
    let color = '#7b8a84';
    if (mastery >= 70) color = '#285b49';
    else if (mastery >= 40) color = '#b68842';
    else if (mastery > 0) color = '#b96549';
    const isOnPath = pathNodes.has(n.id);
    return {
      id: n.id, name: n.name,
      symbolSize: isOnPath ? 48 : (mastery > 0 ? 35 + mastery * 0.2 : 28),
      itemStyle: { color: isOnPath ? (mastery < 40 ? '#b96549' : '#285b49') : color,
        borderColor: isOnPath ? '#17352b' : 'transparent', borderWidth: isOnPath ? 3 : 0,
        shadowBlur: isOnPath ? 20 : 0, shadowColor: isOnPath ? 'rgba(184,101,73,.4)' : 'transparent' },
      label: { fontSize: isOnPath ? 13 : 10, color: isOnPath ? '#17352b' : '#888', fontWeight: isOnPath ? 'bold' : 'normal' },
      data: n
    };
  });

  const links = graphData.edges.map(e => {
    const isPath = pathEdges.some(pe => pe.source === e.from && pe.target === e.to);
    return { source: e.from, target: e.to,
      lineStyle: isPath ? { color: '#b96549', width: 3.5, curveness: 0.15 } : { color: '#eee', width: 1 }
    };
  });

  graphChart.setOption({
    tooltip: { formatter: p => p.dataType === 'node' ? `<b>${p.data.data.name}</b><br/>${p.data.data.chapter}<br/>掌握度：${p.data.data.mastery || 0}%` : '' },
    series: [{ type: 'graph', layout: 'force', data: nodes, links, roam: true, draggable: true,
      force: { repulsion: 220, edgeLength: [100, 140], gravity: 0.08 },
      label: { show: true, position: 'right' },
      edgeStyle: { curveness: 0.1 },
      emphasis: { focus: 'adjacency' }
    }]
  });
  graphChart.on('click', p => { if (p.dataType === 'node') showGraphDetail(p.data.data); });
}

function showGraphDetail(node) {
  const detailEl = document.getElementById('graph-detail');
  detailEl.style.display = 'block';

  document.getElementById('graph-detail-name').textContent = node.name;
  document.getElementById('graph-detail-chapter').textContent = node.chapter;

  const diffStars = '⭐'.repeat(node.difficulty || 1);
  const diffLabel = node.difficulty === 1 ? '基础' : node.difficulty === 2 ? '进阶' : '高阶';
  document.getElementById('graph-detail-difficulty').innerHTML =
    `<span style="background:var(--gold);color:#fff;padding:2px 8px;border-radius:6px;font-size:11px">${diffStars} ${diffLabel}</span>`;

  const masteryEl = document.getElementById('graph-detail-mastery');
  const mastery = node.mastery || 0;
  const diagCount = node.diag_count || 0;
  const color = mastery >= 70 ? '#285b49' : mastery >= 40 ? '#b68842' : mastery > 0 ? '#b96549' : '#7b8a84';
  masteryEl.innerHTML = `
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <div style="flex:1;min-width:200px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <span style="font-size:13px;color:var(--muted)">当前掌握度</span>
          <span style="font-size:22px;font-weight:700;color:${color}">${mastery}%</span>
          <span style="font-size:12px;color:var(--muted)">· 诊断 ${diagCount} 次</span>
        </div>
        <div style="height:8px;background:var(--paper);border-radius:4px;overflow:hidden">
          <div style="height:100%;width:${mastery}%;background:${color};border-radius:4px;transition:width .6s ease"></div>
        </div>
      </div>
    </div>`;

  document.getElementById('graph-detail-concept').textContent = node.concept || '暂无内容';

  const examsEl = document.getElementById('graph-detail-exams');
  if (node.common_exams && node.common_exams.length) {
    examsEl.innerHTML = node.common_exams.map(e => `<li>${escapeHtml(e)}</li>`).join('');
  } else {
    examsEl.innerHTML = '<li style="color:var(--muted)">暂无内容</li>';
  }

  document.getElementById('graph-detail-errors').textContent = node.common_errors || '暂无内容';
  document.getElementById('graph-detail-advice').textContent = node.advice || '暂无内容';

  const prereqEl = document.getElementById('graph-detail-prereqs');
  const prereqs = node.prerequisites || [];
  if (!prereqs.length) {
    prereqEl.innerHTML = '<span style="color:var(--muted);font-size:14px">该知识点没有前置依赖，是基础起点。</span>';
  } else {
    prereqEl.innerHTML = prereqs.map(p => `
      <div class="graph-tag" onclick="showGraphDetailById('${p.id}')">
        <span>${escapeHtml(p.name)}</span>
        <small>${escapeHtml(p.chapter)}</small>
      </div>`).join('');
  }

  const succEl = document.getElementById('graph-detail-successors');
  const successors = node.successors || [];
  if (!successors.length) {
    succEl.innerHTML = '<span style="color:var(--muted);font-size:14px">暂无后续延伸知识点。</span>';
  } else {
    succEl.innerHTML = successors.map(p => `
      <div class="graph-tag graph-tag-next" onclick="showGraphDetailById('${p.id}')">
        <span>${escapeHtml(p.name)}</span>
        <small>${escapeHtml(p.chapter)}</small>
      </div>`).join('');
  }

  const practiceBtn = document.getElementById('graph-detail-practice');
  practiceBtn.onclick = () => { startPracticeForKp(node.name); };

  detailEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showGraphDetailByName(name) {
  if (!graphData) return;
  const node = graphData.nodes.find(n => n.name === name);
  if (node) showGraphDetail(node);
}

function showGraphDetailById(id) {
  if (!graphData) return;
  const node = graphData.nodes.find(n => n.id === id);
  if (node) showGraphDetail(node);
}

// ===== 图谱内嵌练习 =====
let gpQuestions = [];
let gpIndex = 0;
let gpCorrect = 0;
let gpSelected = -1;
let gpAnswered = false;
let gpKpName = '';

async function startPracticeForKp(kpName) {
  if (!isLoggedIn()) {
    toast('请先登录');
    goTo('auth');
    return;
  }

  const node = graphData?.nodes.find(n => n.name === kpName);
  const kpId = node?.id || '';
  gpKpName = kpName;

  const modal = document.getElementById('gp-modal');
  const loadingEl = document.getElementById('gp-loading');
  const mainEl = document.getElementById('gp-main');
  const resultEl = document.getElementById('gp-result');

  modal.style.display = 'flex';
  loadingEl.style.display = 'block';
  mainEl.style.display = 'none';
  resultEl.style.display = 'none';
  document.getElementById('gp-title').textContent = `${kpName} · 针对性训练`;

  try {
    const body = { weakness: kpName, count: 3, source: 'auto' };
    if (kpId) body.kp_id = kpId;

    const data = await api('/practice', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (data.questions && data.questions.length) {
      gpQuestions = data.questions;
      gpIndex = 0;
      gpCorrect = 0;
      loadingEl.style.display = 'none';
      mainEl.style.display = 'block';
      gpRenderQuestion();
    } else {
      loadingEl.style.display = 'none';
      toast('该知识点暂无练习题');
      setTimeout(() => { modal.style.display = 'none'; }, 1500);
    }
  } catch (err) {
    loadingEl.style.display = 'none';
    toast(err.message);
    setTimeout(() => { modal.style.display = 'none'; }, 1500);
  }
}

function gpRenderQuestion() {
  const q = gpQuestions[gpIndex];
  document.getElementById('gp-count').textContent = `第 ${gpIndex + 1} / ${gpQuestions.length} 题`;
  document.getElementById('gp-progress').style.width = `${(gpIndex / gpQuestions.length) * 100}%`;

  const dotsEl = document.getElementById('gp-dots');
  if (dotsEl) {
    dotsEl.innerHTML = gpQuestions.map((_, i) => {
      let cls = 'practice-dot';
      if (i < gpIndex) cls += ' correct';
      else if (i === gpIndex) cls += ' active';
      return `<div class="${cls}"></div>`;
    }).join('');
  }

  renderFormatted(q.question, document.getElementById('gp-question'));
  document.getElementById('gp-options').innerHTML = q.options.map((opt, i) =>
    `<button class="option" data-idx="${i}" onclick="gpSelect(${i})">${String.fromCharCode(65 + i)}. ${escapeHtml(opt)}</button>`
  ).join('');
  document.querySelectorAll('#gp-options .option').forEach(el => {
    if (typeof renderMathInElement !== 'undefined') {
      renderMathInElement(el, { delimiters: [{ left: '$', right: '$', display: false }], throwOnError: false });
    }
  });

  const expEl = document.getElementById('gp-explanation');
  expEl.classList.remove('show');
  expEl.innerHTML = '';
  gpSelected = -1; gpAnswered = false;

  document.getElementById('gp-submit').textContent = '提交答案';
  document.getElementById('gp-submit').style.display = 'inline-block';
  document.getElementById('gp-submit').disabled = false;
  document.getElementById('gp-next').style.display = 'none';
  document.getElementById('gp-prev').style.display = gpIndex > 0 ? 'inline-block' : 'none';
  document.getElementById('gp-result').style.display = 'none';
}

function gpSelect(idx) {
  if (gpAnswered) return;
  gpSelected = idx;
  document.querySelectorAll('#gp-options .option').forEach((el, i) => {
    el.classList.toggle('selected', i === idx);
  });
}

function gpSubmit() {
  if (gpAnswered) return;
  if (gpSelected === -1) { toast('请先选择一个答案'); return; }
  gpAnswered = true;

  const q = gpQuestions[gpIndex];
  const isCorrect = gpSelected === q.correct;
  if (isCorrect) gpCorrect++;

  document.querySelectorAll('#gp-options .option').forEach((el, i) => {
    if (i === q.correct) { el.classList.add('correct'); }
    else if (i === gpSelected) { el.classList.add('wrong'); }
    el.style.pointerEvents = 'none';
  });

  const expEl = document.getElementById('gp-explanation');
  let html = isCorrect
    ? '<div class="explain-tag correct">✓ 回答正确</div>'
    : `<div class="explain-tag wrong">✗ 回答错误 · 正确答案：${String.fromCharCode(65 + q.correct)}</div>`;
  if (q.explanation) html += `<div class="explain-body"></div>`;
  expEl.innerHTML = html;
  expEl.classList.add('show');

  if (q.explanation) {
    const bodyEl = expEl.querySelector('.explain-body');
    renderFormatted(q.explanation, bodyEl);
    if (typeof renderMathInElement !== 'undefined') {
      renderMathInElement(bodyEl, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true }
        ],
        throwOnError: false
      });
    }
  }

  document.getElementById('gp-submit').style.display = 'none';
  document.getElementById('gp-next').textContent = gpIndex < gpQuestions.length - 1 ? '下一题 →' : '查看结果 →';
  document.getElementById('gp-next').style.display = 'inline-block';
}

function gpNext() {
  gpIndex++;
  if (gpIndex < gpQuestions.length) gpRenderQuestion();
  else gpShowResult();
}

function gpPrev() {
  if (gpIndex > 0) { gpIndex--; gpRenderQuestion(); }
}

function gpShowResult() {
  const score = gpCorrect;
  const total = gpQuestions.length;
  document.getElementById('gp-score').textContent = `${score}/${total}`;
  document.getElementById('gp-advice').textContent =
    score >= 2 ? '已达到验证标准，这个知识点可以暂时放心了。'
    : '还需要继续巩固，建议查看学习建议后再练一组。';

  document.getElementById('gp-progress').style.width = '100%';
  document.getElementById('gp-submit').style.display = 'none';
  document.getElementById('gp-next').style.display = 'none';
  document.getElementById('gp-prev').style.display = 'none';
  document.getElementById('gp-result').style.display = 'block';
  document.getElementById('gp-result').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function gpRestart() {
  document.getElementById('gp-result').style.display = 'none';
  document.getElementById('gp-main').style.display = 'none';
  document.getElementById('gp-loading').style.display = 'block';

  const node = graphData?.nodes.find(n => n.name === gpKpName);
  const kpId = node?.id || '';

  try {
    const body = { weakness: gpKpName, count: 3, source: 'auto' };
    if (kpId) body.kp_id = kpId;
    const data = await api('/practice', { method: 'POST', body: JSON.stringify(body) });
    if (data.questions && data.questions.length) {
      gpQuestions = data.questions;
      gpIndex = 0;
      gpCorrect = 0;
      document.getElementById('gp-loading').style.display = 'none';
      document.getElementById('gp-main').style.display = 'block';
      gpRenderQuestion();
    } else {
      toast('生成失败，请稍后重试');
    }
  } catch (err) {
    toast(err.message);
  }
}

function closeGraphPractice() {
  document.getElementById('gp-modal').style.display = 'none';
}

function closeGraphDetail() {
  document.getElementById('graph-detail').style.display = 'none';
}

// ===== 初始化 =====
async function init() {
  // 上传区域点击触发文件选择
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('input-image');
  if (uploadArea && fileInput) {
    // 阻止 input 自身 click 冒泡到 upload-area，避免重复触发文件选择器
    fileInput.addEventListener('click', (e) => e.stopPropagation());
    // 点击上传区域时触发文件选择
    uploadArea.addEventListener('click', () => fileInput.click());
    // 文件选择后处理
    fileInput.addEventListener('change', handleImageUpload);
  }

  // 检查登录状态
  const token = getToken();
  if (token) {
    try {
      const data = await api('/auth/me');
      currentUser = data.user;
      renderNavMenu();
      goTo('home');
    } catch (err) {
      clearToken();
      goTo('auth');
    }
  } else {
    goTo('auth');
  }

  // 绑定输入框事件（含 KaTeX 实时预览）
  document.querySelectorAll('.textarea').forEach(t => {
    t.addEventListener('input', () => {
      const id = t.id.replace('input-', '');
      const errEl = document.getElementById('err-' + id);
      if (errEl) errEl.classList.remove('show');
      updatePreview(t.id);
    });
  });

  // 聊天输入框回车发送
  document.getElementById('chat-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });
}

init();
