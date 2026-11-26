(function () {
  "use strict";

  var app = document.getElementById("admin-panel-app");
  if (!app) return;

  var csrfToken = app.getAttribute("data-csrf") || "";

  var refs = { roles: [], sides: [], maps: [], characters: [] };
  var articles = [];
  var characters = [];

  var els = {
    globalStatus: document.getElementById("admin-global-status"),
    tabs: Array.prototype.slice.call(app.querySelectorAll(".admin-tab")),
    panels: Array.prototype.slice.call(app.querySelectorAll(".admin-panel-section")),

    articlesLoading: document.getElementById("articles-loading"),
    articlesError: document.getElementById("articles-error"),
    articlesEmpty: document.getElementById("articles-empty"),
    articlesList: document.getElementById("articles-list"),
    articleNewBtn: document.getElementById("article-new-btn"),
    articleForm: document.getElementById("article-form"),
    articleId: document.getElementById("article-id"),
    articleTitle: document.getElementById("article-title"),
    articleContent: document.getElementById("article-content"),
    articleMap: document.getElementById("article-map"),
    articleSide: document.getElementById("article-side"),
    articleRole: document.getElementById("article-role"),
    articleCharacters: document.getElementById("article-characters"),
    articleFormTitle: document.getElementById("article-form-title"),
    articleFormEyebrow: document.getElementById("article-form-eyebrow"),
    articleFormStatus: document.getElementById("article-form-status"),
    articleSaveBtn: document.getElementById("article-save-btn"),
    articleResetBtn: document.getElementById("article-reset-btn"),
    articleDeleteBtn: document.getElementById("article-delete-btn"),

    agentsLoading: document.getElementById("agents-loading"),
    agentsError: document.getElementById("agents-error"),
    agentsEmpty: document.getElementById("agents-empty"),
    agentsList: document.getElementById("agents-list"),
    characterForm: document.getElementById("character-form"),
    characterId: document.getElementById("character-id"),
    characterName: document.getElementById("character-name"),
    characterRole: document.getElementById("character-role"),
    characterIconUrl: document.getElementById("character-icon-url"),
    characterDescription: document.getElementById("character-description"),
    characterFormTitle: document.getElementById("character-form-title"),
    characterFormStatus: document.getElementById("character-form-status"),
    characterSaveBtn: document.getElementById("character-save-btn"),
    characterResetBtn: document.getElementById("character-reset-btn")
  };

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function setStatus(node, message, kind) {
    if (!node) return;
    node.textContent = message || "";
    node.className = "admin-form-status" + (kind ? " is-" + kind : "");
  }

  function setGlobalStatus(message, kind) {
    if (!els.globalStatus) return;
    els.globalStatus.textContent = message || "";
    els.globalStatus.className = "admin-status" + (kind ? " is-" + kind : "");
  }

  function fmtDate(value) {
    if (!value) return "";
    var s = String(value);
    return s.length >= 10 ? s.slice(0, 10) : s;
  }

  function toIntOrNull(value) {
    if (value === "" || value == null) return null;
    var n = parseInt(value, 10);
    return isFinite(n) ? n : null;
  }

  function fetchJson(url, options) {
    var opts = options || {};
    opts.headers = opts.headers || {};
    if (!opts.headers.Accept) opts.headers.Accept = "application/json";
    return fetch(url, opts).then(function (res) {
      var ct = res.headers.get("content-type") || "";
      var parse = ct.indexOf("application/json") !== -1
        ? res.json().catch(function () { return null; })
        : res.text().then(function (t) { return { message: t }; }).catch(function () { return null; });
      return parse.then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function apiError(result, fallback) {
    var d = result && result.data;
    if (d && typeof d === "object") {
      return d.detail || d.error || d.message || fallback;
    }
    if (typeof d === "string" && d.trim()) return d.trim().slice(0, 180);
    if (result && result.status === 403) return "Недостаточно прав или неверный CSRF-токен.";
    if (result && result.status === 503) return "База данных недоступна. Попробуй позже.";
    return fallback;
  }

  function postJson(url, method, body) {
    var payload = body || {};
    if (csrfToken && !payload.csrf_token) payload.csrf_token = csrfToken;
    return fetchJson(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken
      },
      body: JSON.stringify(payload)
    });
  }

  /* Tabs */
  function activateTab(name) {
    for (var i = 0; i < els.tabs.length; i++) {
      var tab = els.tabs[i];
      var active = tab.getAttribute("data-tab") === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.tabIndex = active ? 0 : -1;
    }
    for (var j = 0; j < els.panels.length; j++) {
      var panel = els.panels[j];
      var show = panel.id === "panel-" + name;
      panel.hidden = !show;
    }
  }

  els.tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      activateTab(tab.getAttribute("data-tab"));
    });
    tab.addEventListener("keydown", function (e) {
      var idx = els.tabs.indexOf(tab);
      if (idx < 0) return;
      var nextIdx = idx;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") nextIdx = (idx + 1) % els.tabs.length;
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") nextIdx = (idx - 1 + els.tabs.length) % els.tabs.length;
      else if (e.key === "Home") nextIdx = 0;
      else if (e.key === "End") nextIdx = els.tabs.length - 1;
      else return;
      e.preventDefault();
      els.tabs[nextIdx].focus();
      activateTab(els.tabs[nextIdx].getAttribute("data-tab"));
    });
  });

  /* Reference selects */
  function fillSelect(select, items, placeholder) {
    if (!select) return;
    var current = select.value;
    select.innerHTML = "";
    var opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder || "Не выбрано";
    select.appendChild(opt0);
    for (var i = 0; i < (items || []).length; i++) {
      var it = items[i];
      var opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.name || ("ID " + it.id);
      select.appendChild(opt);
    }
    if (current) select.value = current;
  }

  function renderCharacterCheckboxes(selectedIds) {
    if (!els.articleCharacters) return;
    var selected = {};
    for (var s = 0; s < (selectedIds || []).length; s++) selected[String(selectedIds[s])] = true;
    var list = refs.characters && refs.characters.length ? refs.characters : characters;
    if (!list || !list.length) {
      els.articleCharacters.innerHTML = '<p class="muted admin-muted-sm">Нет доступных персонажей.</p>';
      return;
    }
    var html = "";
    for (var i = 0; i < list.length; i++) {
      var c = list[i];
      var id = String(c.id);
      var checked = selected[id] ? " checked" : "";
      var inputId = "article-char-" + id;
      html += '<label class="admin-check" for="' + esc(inputId) + '">';
      html += '<input type="checkbox" id="' + esc(inputId) + '" name="character_ids" value="' + esc(id) + '"' + checked + '>';
      html += '<span class="admin-check-label">' + esc(c.name || ("ID " + id)) + '</span>';
      html += '</label>';
    }
    els.articleCharacters.innerHTML = html;
  }

  function getSelectedCharacterIds() {
    var nodes = els.articleCharacters ? els.articleCharacters.querySelectorAll('input[name="character_ids"]:checked') : [];
    var ids = [];
    for (var i = 0; i < nodes.length; i++) {
      var n = toIntOrNull(nodes[i].value);
      if (n != null) ids.push(n);
    }
    return ids;
  }

  function applyRefs() {
    fillSelect(els.articleMap, refs.maps, "Не выбрана");
    fillSelect(els.articleSide, refs.sides, "Не выбрана");
    fillSelect(els.articleRole, refs.roles, "Не выбрана");
    fillSelect(els.characterRole, refs.roles, "Выбери роль");
    var selected = getSelectedCharacterIds();
    var currentArticleId = toIntOrNull(els.articleId.value);
    if (currentArticleId != null) {
      var a = findArticle(currentArticleId);
      if (a && Array.isArray(a.character_ids)) selected = a.character_ids;
    }
    renderCharacterCheckboxes(selected);
  }

  /* Articles */
  function findArticle(id) {
    for (var i = 0; i < articles.length; i++) {
      if (String(articles[i].id) === String(id)) return articles[i];
    }
    return null;
  }

  function renderArticles() {
    if (!els.articlesList) return;
    if (!articles.length) {
      els.articlesLoading.hidden = true;
      els.articlesError.hidden = true;
      els.articlesEmpty.hidden = false;
      els.articlesList.hidden = true;
      els.articlesList.innerHTML = "";
      return;
    }
    var activeId = String(els.articleId.value || "");
    var html = "";
    for (var i = 0; i < articles.length; i++) {
      var a = articles[i];
      var id = String(a.id);
      var isActive = id === activeId;
      var meta = [];
      if (a.map_name) meta.push(a.map_name);
      if (a.side_name) meta.push(a.side_name);
      if (a.role_name) meta.push(a.role_name);
      var chars = Array.isArray(a.characters) ? a.characters : [];
      for (var c = 0; c < chars.length && c < 3; c++) {
        if (chars[c] && chars[c].name) meta.push(chars[c].name);
      }
      if (chars.length > 3) meta.push("+" + (chars.length - 3));
      html += '<button type="button" class="admin-list-item' + (isActive ? ' is-active' : '') + '" data-article-id="' + esc(id) + '">';
      html += '<span class="admin-list-title">' + esc(a.title || "Без названия") + '</span>';
      html += '<span class="admin-list-meta">' + esc(meta.length ? meta.join(" · ") : "Без привязок") + '</span>';
      html += '<span class="admin-list-date">' + esc(fmtDate(a.created_at) || "—") + '</span>';
      html += '</button>';
    }
    els.articlesList.innerHTML = html;
    els.articlesLoading.hidden = true;
    els.articlesError.hidden = true;
    els.articlesEmpty.hidden = true;
    els.articlesList.hidden = false;
  }

  function resetArticleForm() {
    els.articleId.value = "";
    els.articleTitle.value = "";
    els.articleContent.value = "";
    els.articleMap.value = "";
    els.articleSide.value = "";
    els.articleRole.value = "";
    renderCharacterCheckboxes([]);
    els.articleFormTitle.textContent = "Новая статья";
    els.articleFormEyebrow.textContent = "Редактор";
    els.articleSaveBtn.textContent = "Создать статью";
    els.articleDeleteBtn.hidden = true;
    setStatus(els.articleFormStatus, "", "");
    renderArticles();
  }

  function fillArticleForm(article) {
    els.articleId.value = String(article.id);
    els.articleTitle.value = article.title || "";
    els.articleContent.value = article.content || "";
    els.articleMap.value = article.map_id != null ? String(article.map_id) : "";
    els.articleSide.value = article.side_id != null ? String(article.side_id) : "";
    els.articleRole.value = article.role_id != null ? String(article.role_id) : "";
    renderCharacterCheckboxes(article.character_ids || []);
    els.articleFormTitle.textContent = "Редактирование статьи";
    els.articleFormEyebrow.textContent = "Статья #" + article.id;
    els.articleSaveBtn.textContent = "Сохранить изменения";
    els.articleDeleteBtn.hidden = false;
    setStatus(els.articleFormStatus, "", "");
    renderArticles();
  }

  function loadArticles() {
    els.articlesLoading.hidden = false;
    els.articlesError.hidden = true;
    els.articlesEmpty.hidden = true;
    els.articlesList.hidden = true;
    return fetchJson("/api/admin/articles").then(function (r) {
      if (!r.ok) {
        els.articlesLoading.hidden = true;
        els.articlesError.textContent = apiError(r, "Не удалось загрузить статьи.");
        els.articlesError.hidden = false;
        return;
      }
      var data = r.data || {};
      articles = Array.isArray(data.articles) ? data.articles : [];
      renderArticles();
      var currentId = toIntOrNull(els.articleId.value);
      if (currentId != null) {
        var current = findArticle(currentId);
        if (current) fillArticleForm(current);
        else resetArticleForm();
      }
    }).catch(function () {
      els.articlesLoading.hidden = true;
      els.articlesError.textContent = "Ошибка сети при загрузке статей.";
      els.articlesError.hidden = false;
    });
  }

  function submitArticle(e) {
    e.preventDefault();
    var title = String(els.articleTitle.value || "").trim();
    var content = String(els.articleContent.value || "").trim();
    if (!title) {
      setStatus(els.articleFormStatus, "Укажи заголовок статьи.", "error");
      els.articleTitle.focus();
      return;
    }
    if (!content) {
      setStatus(els.articleFormStatus, "Добавь содержание статьи.", "error");
      els.articleContent.focus();
      return;
    }

    var id = toIntOrNull(els.articleId.value);
    var payload = {
      title: title,
      content: content,
      map_id: toIntOrNull(els.articleMap.value),
      side_id: toIntOrNull(els.articleSide.value),
      role_id: toIntOrNull(els.articleRole.value),
      character_ids: getSelectedCharacterIds()
    };

    els.articleSaveBtn.disabled = true;
    setStatus(els.articleFormStatus, id ? "Сохранение изменений..." : "Создание статьи...", "loading");

    var url = id ? "/api/admin/articles/" + id : "/api/admin/articles";
    var method = id ? "PUT" : "POST";
    postJson(url, method, payload).then(function (r) {
      els.articleSaveBtn.disabled = false;
      if (!r.ok) {
        setStatus(els.articleFormStatus, apiError(r, "Не удалось сохранить статью."), "error");
        return;
      }
      var article = r.data && r.data.article ? r.data.article : null;
      setStatus(els.articleFormStatus, id ? "Статья сохранена." : "Статья создана.", "success");
      setGlobalStatus(id ? "Статья обновлена." : "Статья создана.", "success");
      loadArticles().then(function () {
        if (article && article.id != null) {
          var fresh = findArticle(article.id);
          if (fresh) fillArticleForm(fresh);
        } else if (!id) {
          resetArticleForm();
        }
      });
    }).catch(function () {
      els.articleSaveBtn.disabled = false;
      setStatus(els.articleFormStatus, "Ошибка сети при сохранении статьи.", "error");
    });
  }

  function deleteArticle() {
    var id = toIntOrNull(els.articleId.value);
    if (id == null) return;
    var article = findArticle(id);
    var title = article ? article.title : ("#" + id);
    if (!window.confirm('Удалить статью "' + title + '"? Это действие нельзя отменить.')) return;

    els.articleDeleteBtn.disabled = true;
    setStatus(els.articleFormStatus, "Удаление статьи...", "loading");
    postJson("/api/admin/articles/" + id, "DELETE", {}).then(function (r) {
      els.articleDeleteBtn.disabled = false;
      if (!r.ok) {
        setStatus(els.articleFormStatus, apiError(r, "Не удалось удалить статью."), "error");
        return;
      }
      setGlobalStatus("Статья удалена.", "success");
      resetArticleForm();
      loadArticles();
    }).catch(function () {
      els.articleDeleteBtn.disabled = false;
      setStatus(els.articleFormStatus, "Ошибка сети при удалении статьи.", "error");
    });
  }

  /* Characters */
  function findCharacter(id) {
    for (var i = 0; i < characters.length; i++) {
      if (String(characters[i].id) === String(id)) return characters[i];
    }
    return null;
  }

  function renderCharacters() {
    if (!els.agentsList) return;
    if (!characters.length) {
      els.agentsLoading.hidden = true;
      els.agentsError.hidden = true;
      els.agentsEmpty.hidden = false;
      els.agentsList.hidden = true;
      els.agentsList.innerHTML = "";
      return;
    }
    var activeId = String(els.characterId.value || "");
    var html = "";
    for (var i = 0; i < characters.length; i++) {
      var c = characters[i];
      var id = String(c.id);
      var isActive = id === activeId;
      var meta = c.role_name || "Роль не указана";
      var desc = String(c.description || "").trim();
      if (desc) {
        desc = desc.length > 70 ? desc.slice(0, 70) + "..." : desc;
        meta += " · " + desc;
      }
      html += '<button type="button" class="admin-list-item' + (isActive ? ' is-active' : '') + '" data-character-id="' + esc(id) + '">';
      html += '<span class="admin-list-title">' + esc(c.name || "Без имени") + '</span>';
      html += '<span class="admin-list-meta">' + esc(meta) + '</span>';
      html += '<span class="admin-list-date">ID ' + esc(id) + '</span>';
      html += '</button>';
    }
    els.agentsList.innerHTML = html;
    els.agentsLoading.hidden = true;
    els.agentsError.hidden = true;
    els.agentsEmpty.hidden = true;
    els.agentsList.hidden = false;
  }

  function resetCharacterForm() {
    els.characterId.value = "";
    els.characterName.value = "";
    els.characterRole.value = "";
    els.characterIconUrl.value = "";
    els.characterDescription.value = "";
    els.characterFormTitle.textContent = "Выбери агента";
    els.characterSaveBtn.disabled = true;
    setStatus(els.characterFormStatus, "", "");
    renderCharacters();
  }

  function fillCharacterForm(character) {
    els.characterId.value = String(character.id);
    els.characterName.value = character.name || "";
    els.characterRole.value = character.role_id != null ? String(character.role_id) : "";
    els.characterIconUrl.value = character.icon_url || "";
    els.characterDescription.value = character.description || "";
    els.characterFormTitle.textContent = "Редактирование: " + (character.name || "агент");
    els.characterSaveBtn.disabled = false;
    setStatus(els.characterFormStatus, "", "");
    renderCharacters();
  }

  function loadCharacters() {
    els.agentsLoading.hidden = false;
    els.agentsError.hidden = true;
    els.agentsEmpty.hidden = true;
    els.agentsList.hidden = true;
    return fetchJson("/api/admin/characters").then(function (r) {
      if (!r.ok) {
        els.agentsLoading.hidden = true;
        els.agentsError.textContent = apiError(r, "Не удалось загрузить агентов.");
        els.agentsError.hidden = false;
        return;
      }
      var data = r.data || {};
      characters = Array.isArray(data.characters) ? data.characters : [];
      if ((!refs.characters || !refs.characters.length) && characters.length) {
        refs.characters = characters.map(function (c) { return { id: c.id, name: c.name }; });
        renderCharacterCheckboxes(getSelectedCharacterIds());
      }
      renderCharacters();
      var currentId = toIntOrNull(els.characterId.value);
      if (currentId != null) {
        var current = findCharacter(currentId);
        if (current) fillCharacterForm(current);
        else resetCharacterForm();
      }
    }).catch(function () {
      els.agentsLoading.hidden = true;
      els.agentsError.textContent = "Ошибка сети при загрузке агентов.";
      els.agentsError.hidden = false;
    });
  }

  function submitCharacter(e) {
    e.preventDefault();
    var id = toIntOrNull(els.characterId.value);
    if (id == null) {
      setStatus(els.characterFormStatus, "Выбери агента из списка.", "error");
      return;
    }
    var name = String(els.characterName.value || "").trim();
    var roleId = toIntOrNull(els.characterRole.value);
    var description = String(els.characterDescription.value || "").trim();
    var iconUrl = String(els.characterIconUrl.value || "").trim();

    if (!name) {
      setStatus(els.characterFormStatus, "Укажи имя агента.", "error");
      els.characterName.focus();
      return;
    }
    if (roleId == null) {
      setStatus(els.characterFormStatus, "Выбери роль агента.", "error");
      els.characterRole.focus();
      return;
    }

    els.characterSaveBtn.disabled = true;
    setStatus(els.characterFormStatus, "Сохранение...", "loading");

    postJson("/api/admin/characters/" + id, "PUT", {
      name: name,
      role_id: roleId,
      description: description,
      icon_url: iconUrl
    }).then(function (r) {
      els.characterSaveBtn.disabled = false;
      if (!r.ok) {
        setStatus(els.characterFormStatus, apiError(r, "Не удалось сохранить агента."), "error");
        return;
      }
      var character = r.data && r.data.character ? r.data.character : null;
      setStatus(els.characterFormStatus, "Изменения сохранены.", "success");
      setGlobalStatus("Агент обновлён.", "success");
      loadCharacters().then(function () {
        if (character && character.id != null) {
          var fresh = findCharacter(character.id);
          if (fresh) fillCharacterForm(fresh);
        }
      });
      // refresh refs/checkboxes with updated character names
      loadRefs();
    }).catch(function () {
      els.characterSaveBtn.disabled = false;
      setStatus(els.characterFormStatus, "Ошибка сети при сохранении агента.", "error");
    });
  }

  /* References */
  function loadRefs() {
    return fetchJson("/api/admin/references").then(function (r) {
      if (!r.ok) return;
      var d = r.data || {};
      refs.roles = Array.isArray(d.roles) ? d.roles : refs.roles;
      refs.sides = Array.isArray(d.sides) ? d.sides : refs.sides;
      refs.maps = Array.isArray(d.maps) ? d.maps : refs.maps;
      refs.characters = Array.isArray(d.characters) ? d.characters : refs.characters;
      applyRefs();
    }).catch(function () {});
  }

  /* Events */
  els.articlesList.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-article-id]");
    if (!btn) return;
    var id = btn.getAttribute("data-article-id");
    var article = findArticle(id);
    if (article) fillArticleForm(article);
  });

  els.agentsList.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-character-id]");
    if (!btn) return;
    var id = btn.getAttribute("data-character-id");
    var character = findCharacter(id);
    if (character) fillCharacterForm(character);
  });

  els.articleNewBtn.addEventListener("click", resetArticleForm);
  els.articleResetBtn.addEventListener("click", resetArticleForm);
  els.articleForm.addEventListener("submit", submitArticle);
  els.articleDeleteBtn.addEventListener("click", deleteArticle);

  els.characterForm.addEventListener("submit", submitCharacter);
  els.characterResetBtn.addEventListener("click", function () {
    var id = toIntOrNull(els.characterId.value);
    if (id != null) {
      var c = findCharacter(id);
      if (c) { fillCharacterForm(c); return; }
    }
    resetCharacterForm();
  });

  /* Init */
  activateTab("articles");
  renderCharacterCheckboxes([]);
  resetArticleForm();
  resetCharacterForm();

  loadRefs().then(function () {
    loadArticles();
    loadCharacters();
  });
})();
