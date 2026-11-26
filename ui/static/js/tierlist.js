(function () {
  "use strict";

  var AGENTS_API = "https://valorant-api.com/v1/agents?isPlayableCharacter=true";
  var TIERLIST_API = "/api/tierlist";
  var DEFAULT_TIERS = [
    { id: "S", label: "S", color: "#ff4655", items: [] },
    { id: "A", label: "A", color: "#ff8a3d", items: [] },
    { id: "B", label: "B", color: "#ffd166", items: [] },
    { id: "C", label: "C", color: "#4cc9f0", items: [] },
    { id: "D", label: "D", color: "#8b978f", items: [] }
  ];

  var app = document.getElementById("tierlist-app");
  var boardEl = document.getElementById("tierlist-board");
  var poolWrap = document.getElementById("tierlist-pool-wrap");
  var poolEl = document.getElementById("tierlist-pool");
  var poolHint = document.getElementById("tier-pool-hint");
  var loadingEl = document.getElementById("tierlist-loading");
  var errorEl = document.getElementById("tierlist-error");
  var errorMsg = document.getElementById("tierlist-error-message");
  var retryBtn = document.getElementById("tierlist-retry");
  var saveBtn = document.getElementById("tierlist-save");
  var statusEl = document.getElementById("tierlist-status");

  if (!app || !boardEl || !poolEl || !loadingEl) return;

  var isAdmin = app.getAttribute("data-admin") === "1" || !!saveBtn;
  var csrfToken = app.getAttribute("data-csrf") || "";
  var agentsByKey = {};
  var agentOrder = [];
  var dirty = false;

  function slugify(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  }
  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }
  function cloneTiers(tiers) {
    return tiers.map(function (t) {
      return {
        id: String(t.id || t.label || "T").trim() || "T",
        label: String(t.label || t.id || "T").trim() || "T",
        color: String(t.color || "#ff4655").trim() || "#ff4655",
        items: Array.isArray(t.items) ? t.items.slice() : []
      };
    });
  }
  function defaultBoard() {
    return { tiers: cloneTiers(DEFAULT_TIERS), pool: agentOrder.slice() };
  }
  function setStatus(text, kind) {
    if (!statusEl) return;
    statusEl.textContent = text || "";
    statusEl.className = "tierlist-status" + (kind ? " tierlist-status-" + kind : "");
  }
  function setLoading(on) {
    loadingEl.hidden = !on;
    if (on) {
      if (errorEl) errorEl.hidden = true;
      boardEl.hidden = true;
      if (poolWrap) poolWrap.hidden = true;
    }
  }
  function showError(message) {
    loadingEl.hidden = true;
    boardEl.hidden = true;
    if (poolWrap) poolWrap.hidden = true;
    if (errorMsg) errorMsg.textContent = message || "Не удалось загрузить тирлист.";
    if (errorEl) errorEl.hidden = false;
  }
  function markDirty() {
    if (!isAdmin) return;
    dirty = true;
    if (saveBtn) saveBtn.disabled = false;
    setStatus("Есть несохранённые изменения", "warn");
  }
  function markClean(message) {
    dirty = false;
    if (saveBtn) saveBtn.disabled = true;
    setStatus(message || "", message ? "ok" : "");
  }

  function resolveAgentKey(value) {
    var raw = String(value || "").trim();
    if (!raw) return "";
    var s = slugify(raw);
    if (agentsByKey[s]) return s;
    var n = normalize(raw);
    for (var i = 0; i < agentOrder.length; i++) {
      var k = agentOrder[i];
      var a = agentsByKey[k];
      if (!a) continue;
      if (normalize(a.displayName) === n || normalize(a.uuid) === n || normalize(a.developerName) === n) return k;
    }
    return "";
  }

  function normalizeBoard(data) {
    var tiers = [];
    var used = {};
    var srcTiers = data && Array.isArray(data.tiers) && data.tiers.length ? data.tiers : DEFAULT_TIERS;
    for (var i = 0; i < srcTiers.length; i++) {
      var t = srcTiers[i] || {};
      var items = Array.isArray(t.items) ? t.items : [];
      var tier = {
        id: String(t.id || t.label || ("T" + (i + 1))).trim() || ("T" + (i + 1)),
        label: String(t.label || t.id || ("Tier " + (i + 1))).trim() || ("Tier " + (i + 1)),
        color: String(t.color || DEFAULT_TIERS[i % DEFAULT_TIERS.length].color).trim() || DEFAULT_TIERS[i % DEFAULT_TIERS.length].color,
        items: []
      };
      for (var j = 0; j < items.length; j++) {
        var key = resolveAgentKey(items[j]);
        if (!key || !agentsByKey[key] || used[key]) continue;
        used[key] = true;
        tier.items.push(key);
      }
      tiers.push(tier);
    }
    var pool = [];
    if (data && Array.isArray(data.pool)) {
      for (var p = 0; p < data.pool.length; p++) {
        var pk = resolveAgentKey(data.pool[p]);
        if (!pk || !agentsByKey[pk] || used[pk]) continue;
        used[pk] = true;
        pool.push(pk);
      }
    }
    for (var k = 0; k < agentOrder.length; k++) {
      if (!used[agentOrder[k]]) pool.push(agentOrder[k]);
    }
    return { tiers: tiers, pool: pool };
  }

  function getBoardState() {
    var tiers = [];
    var rows = boardEl.querySelectorAll(".tier-row");
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var nodes = row.querySelectorAll(".tier-item");
      var items = [];
      for (var j = 0; j < nodes.length; j++) {
        var key = nodes[j].getAttribute("data-agent-key");
        if (key) items.push(key);
      }
      tiers.push({
        id: row.getAttribute("data-tier-id") || String(i),
        label: row.getAttribute("data-tier-label") || row.getAttribute("data-tier-id") || "Tier",
        color: row.getAttribute("data-tier-color") || "#ff4655",
        items: items
      });
    }
    var pool = [];
    var poolNodes = poolEl.querySelectorAll(".tier-item");
    for (var p = 0; p < poolNodes.length; p++) {
      var pkey = poolNodes[p].getAttribute("data-agent-key");
      if (pkey) pool.push(pkey);
    }
    return { tiers: tiers, pool: pool };
  }

  function updatePoolHint() {
    if (!poolHint) return;
    var count = poolEl.querySelectorAll(".tier-item").length;
    if (count === 0) poolHint.textContent = "Все агенты распределены по тирам.";
    else poolHint.textContent = isAdmin ? "Перетащи агентов в нужный тир. Нераспределённых: " + count : "Нераспределённые агенты: " + count;
  }

  function createIcon(item, agent) {
    var candidates = [];
    [agent.displayIconSmall, agent.displayIcon, agent.killfeedPortrait, agent.bustPortrait, agent.fullPortrait, agent.fullPortraitV2].forEach(function (u) {
      var s = String(u || "").trim();
      if (s && candidates.indexOf(s) === -1) candidates.push(s);
    });

    var wrap = document.createElement("span");
    wrap.className = "tier-item-icon-wrap";

    var fallback = document.createElement("span");
    fallback.className = "tier-item-fallback";
    fallback.textContent = String(agent.displayName || "?").charAt(0).toUpperCase() || "?";
    fallback.setAttribute("aria-hidden", "true");
    wrap.appendChild(fallback);

    item.insertBefore(wrap, item.firstChild);
    if (!candidates.length) return;

    var img = document.createElement("img");
    img.className = "tier-item-icon";
    img.alt = "";
    img.loading = "eager";
    img.decoding = "async";
    img.width = 64;
    img.height = 64;
    img.draggable = false;
    img.referrerPolicy = "no-referrer";
    img.setAttribute("aria-hidden", "true");
    img.style.position = "absolute";
    img.style.top = "0";
    img.style.left = "0";
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.visibility = "hidden";

    var idx = 0, settled = false, attempt = 0, curErr = null, curLoad = null, curTimer = null;
    function clearHandlers() {
      if (curErr) { img.removeEventListener("error", curErr); curErr = null; }
      if (curLoad) { img.removeEventListener("load", curLoad); curLoad = null; }
      if (curTimer) { clearTimeout(curTimer); curTimer = null; }
    }
    function reveal() {
      if (settled) return;
      settled = true;
      clearHandlers();
      img.style.visibility = "visible";
      fallback.style.display = "none";
    }
    function failAll() {
      if (settled) return;
      settled = true;
      clearHandlers();
      if (img.parentNode) img.remove();
    }
    function tryNext() {
      if (settled) return;
      clearHandlers();
      if (idx >= candidates.length) { failAll(); return; }
      var src = candidates[idx++];
      var a = ++attempt;
      curErr = function () { if (a !== attempt || settled) return; tryNext(); };
      curLoad = function () {
        if (a !== attempt || settled) return;
        if (img.naturalWidth > 0) { reveal(); return; }
        tryNext();
      };
      img.addEventListener("error", curErr);
      img.addEventListener("load", curLoad);
      img.src = src;
      curTimer = setTimeout(function () { if (a !== attempt || settled) return; tryNext(); }, 6000);
      if (img.complete) {
        if (img.naturalWidth > 0) { reveal(); }
        else if (a === attempt && !settled) { tryNext(); }
      }
    }

    wrap.appendChild(img);
    tryNext();
  }

  function createAgentItem(key) {
    var agent = agentsByKey[key];
    if (!agent) return null;
    var item = document.createElement("div");
    item.className = "tier-item";
    item.setAttribute("data-agent-key", key);
    item.setAttribute("title", agent.displayName);
    if (isAdmin) {
      item.setAttribute("tabindex", "0");
      item.setAttribute("role", "button");
      item.setAttribute("aria-label", "Агент " + agent.displayName + ". Перетащи для перемещения");
    } else {
      item.setAttribute("aria-label", agent.displayName);
    }
    createIcon(item, agent);
    var name = document.createElement("span");
    name.className = "tier-item-name";
    name.textContent = agent.displayName;
    item.appendChild(name);
    if (isAdmin) attachDrag(item);
    return item;
  }

  function renderBoard(state) {
    boardEl.innerHTML = "";
    poolEl.innerHTML = "";

    for (var i = 0; i < state.tiers.length; i++) {
      var t = state.tiers[i];
      var row = document.createElement("div");
      row.className = "tier-row";
      row.setAttribute("data-tier-id", t.id);
      row.setAttribute("data-tier-label", t.label);
      row.setAttribute("data-tier-color", t.color);

      var label = document.createElement("div");
      label.className = "tier-label";
      label.style.background = t.color;
      label.textContent = t.label;
      label.setAttribute("aria-hidden", "true");

      var items = document.createElement("div");
      items.className = "tier-items";
      items.setAttribute("data-dropzone", "tier");
      items.setAttribute("role", "list");
      items.setAttribute("aria-label", "Тир " + t.label);

      for (var j = 0; j < t.items.length; j++) {
        var node = createAgentItem(t.items[j]);
        if (node) { node.setAttribute("role", "listitem"); items.appendChild(node); }
      }
      row.appendChild(label);
      row.appendChild(items);
      boardEl.appendChild(row);
    }

    poolEl.setAttribute("data-dropzone", "pool");
    for (var p = 0; p < state.pool.length; p++) {
      var pnode = createAgentItem(state.pool[p]);
      if (pnode) { pnode.setAttribute("role", "listitem"); poolEl.appendChild(pnode); }
    }
    updatePoolHint();
    boardEl.hidden = false;
    if (poolWrap) poolWrap.hidden = false;
  }

  function closestDropzone(x, y) {
    var zones = boardEl.querySelectorAll(".tier-items");
    var best = null, bestDist = Infinity;
    function check(zone) {
      var r = zone.getBoundingClientRect();
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) { best = zone; bestDist = -1; return true; }
      var cx = Math.max(r.left, Math.min(x, r.right));
      var cy = Math.max(r.top, Math.min(y, r.bottom));
      var dx = x - cx, dy = y - cy, d = dx * dx + dy * dy;
      if (d < bestDist) { bestDist = d; best = zone; }
      return false;
    }
    for (var i = 0; i < zones.length; i++) { if (check(zones[i])) return best; }
    if (poolEl) check(poolEl);
    return best;
  }

  function findInsertBefore(zone, x, y) {
    var items = zone.querySelectorAll(".tier-item:not(.dragging)");
    for (var i = 0; i < items.length; i++) {
      var r = items[i].getBoundingClientRect();
      var midX = r.left + r.width / 2;
      if (y < r.top + r.height * 0.7 && x < midX) return items[i];
    }
    for (var j = 0; j < items.length; j++) {
      var rr = items[j].getBoundingClientRect();
      if (y >= rr.top && y <= rr.bottom && x < rr.left + rr.width / 2) return items[j];
    }
    return null;
  }

  function attachDrag(item) {
    var startX = 0, startY = 0, dragging = false, pointerId = null;
    var originZone = null, originNext = null, ghost = null, offsetX = 0, offsetY = 0;

    function cleanupDropTargets() {
      var active = document.querySelectorAll(".drag-over");
      for (var i = 0; i < active.length; i++) active[i].classList.remove("drag-over");
    }
    function onMove(e) {
      if (pointerId === null || e.pointerId !== pointerId) return;
      var dx = e.clientX - startX, dy = e.clientY - startY;
      if (!dragging) {
        if (Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
        dragging = true;
        originZone = item.parentNode;
        originNext = item.nextSibling;
        var rect = item.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        item.classList.add("dragging");
        ghost = item.cloneNode(true);
        ghost.className = "tier-item tier-item-ghost";
        ghost.style.width = rect.width + "px";
        ghost.style.height = rect.height + "px";
        ghost.style.left = rect.left + "px";
        ghost.style.top = rect.top + "px";
        document.body.appendChild(ghost);
        item.style.opacity = "0.35";
        try { item.setPointerCapture(pointerId); } catch (err) {}
      }
      if (ghost) { ghost.style.left = (e.clientX - offsetX) + "px"; ghost.style.top = (e.clientY - offsetY) + "px"; }
      cleanupDropTargets();
      var zone = closestDropzone(e.clientX, e.clientY);
      if (zone) zone.classList.add("drag-over");
      e.preventDefault();
    }
    function finishDrag(e, cancelled) {
      if (pointerId === null || e.pointerId !== pointerId) return;
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointercancel", onCancel);
      item.removeEventListener("lostpointercapture", onLostCapture);
      cleanupDropTargets();
      if (ghost && ghost.parentNode) ghost.parentNode.removeChild(ghost);
      ghost = null;
      item.style.opacity = "";
      item.classList.remove("dragging");
      try { item.releasePointerCapture(pointerId); } catch (err2) {}
      if (dragging && !cancelled) {
        var zone = closestDropzone(e.clientX, e.clientY);
        if (zone) {
          var before = findInsertBefore(zone, e.clientX, e.clientY);
          if (before) zone.insertBefore(item, before); else zone.appendChild(item);
          if (item.parentNode !== originZone || item.nextSibling !== originNext) markDirty();
          updatePoolHint();
        }
      } else if (dragging && cancelled && originZone) {
        if (originNext) originZone.insertBefore(item, originNext); else originZone.appendChild(item);
      }
      dragging = false;
      pointerId = null;
    }
    function onUp(e) { finishDrag(e, false); }
    function onCancel(e) { finishDrag(e, true); }
    function onLostCapture(e) { finishDrag(e, true); }

    item.addEventListener("pointerdown", function (e) {
      if (!isAdmin) return;
      if (e.button !== 0) return;
      pointerId = e.pointerId;
      startX = e.clientX;
      startY = e.clientY;
      dragging = false;
      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
      document.addEventListener("pointercancel", onCancel);
      item.addEventListener("lostpointercapture", onLostCapture);
    });
  }

  function fetchJson(url, options) {
    return fetch(url, options).then(function (res) {
      var ct = res.headers.get("content-type") || "";
      var parse = ct.indexOf("application/json") !== -1 ? res.json() : res.text();
      return parse.then(function (data) { return { ok: res.ok, status: res.status, data: data }; });
    });
  }

  function loadAgents() {
    return fetchJson(AGENTS_API, { headers: { "Accept": "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("Agents HTTP " + r.status);
      var list = r.data && r.data.data ? r.data.data : [];
      var map = {};
      for (var i = 0; i < list.length; i++) {
        var a = list[i];
        if (!a || !a.isPlayableCharacter) continue;
        var name = String(a.displayName || "").trim();
        if (!name) continue;
        var key = slugify(name);
        if (!key) continue;
        if (!map[key]) map[key] = a;
      }
      agentsByKey = map;
      agentOrder = Object.keys(map).sort(function (a, b) {
        return String(map[a].displayName).localeCompare(String(map[b].displayName), "en", { sensitivity: "base" });
      });
    });
  }

  function loadTierlist() {
    return fetchJson(TIERLIST_API, { headers: { "Accept": "application/json" } }).then(function (r) {
      if (!r.ok || !r.data || typeof r.data !== "object") return defaultBoard();
      if (!Array.isArray(r.data.tiers) && !Array.isArray(r.data.pool)) return defaultBoard();
      return normalizeBoard(r.data);
    }).catch(function () { return defaultBoard(); });
  }

  function saveTierlist() {
    if (!isAdmin || !saveBtn) return;
    var state = getBoardState();
    saveBtn.disabled = true;
    setStatus("Сохранение...", "warn");
    return fetchJson(TIERLIST_API, {
      method: "PUT",
      headers: { "Accept": "application/json", "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ tiers: state.tiers, pool: state.pool, csrf_token: csrfToken })
    }).then(function (r) {
      if (!r.ok) {
        var msg = "Ошибка сохранения";
        if (r && r.data && typeof r.data === "object") msg = r.data.detail || r.data.error || r.data.message || msg;
        if (r.status === 401 || r.status === 403) msg = "Недостаточно прав для сохранения тирлиста.";
        setStatus(msg, "error");
        saveBtn.disabled = false;
        dirty = true;
        return;
      }
      markClean("Сохранено");
    }).catch(function () {
      setStatus("Ошибка сети при сохранении.", "error");
      saveBtn.disabled = false;
      dirty = true;
    });
  }

  function init() {
    setLoading(true);
    setStatus("");
    loadAgents()
      .then(function () { return loadTierlist(); })
      .then(function (state) {
        renderBoard(state);
        setLoading(false);
        if (isAdmin) markClean("Расстановка загружена");
        else setStatus("");
      })
      .catch(function () {
        showError("Не удалось загрузить данные агентов. Проверь соединение и попробуй снова.");
      });
  }

  if (retryBtn) retryBtn.addEventListener("click", init);
  if (saveBtn) saveBtn.addEventListener("click", saveTierlist);
  window.addEventListener("beforeunload", function (e) {
    if (!dirty) return;
    e.preventDefault();
    e.returnValue = "";
  });

  init();
})();
