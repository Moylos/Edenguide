(function () {
  "use strict";

  var searchInput = document.getElementById("library-search");
  var characterSelect = document.getElementById("library-character");
  var mapSelect = document.getElementById("library-map");
  var roleSelect = document.getElementById("library-role");
  var sideSelect = document.getElementById("library-side");
  var grid = document.getElementById("library-grid");
  var emptyState = document.getElementById("library-empty");
  var emptyText = document.getElementById("library-empty-text");

  if (!grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll(".article-card"));
  var totalCount = cards.length;

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function getParams() {
    try {
      return new URLSearchParams(window.location.search || "");
    } catch (e) {
      return new URLSearchParams();
    }
  }

  function ensureOption(select, name) {
    if (!select) return "";
    var target = normalize(name);
    if (!target) return "";
    var options = select.options;
    for (var i = 0; i < options.length; i++) {
      if (normalize(options[i].value) === target || normalize(options[i].textContent) === target) {
        select.value = options[i].value;
        return options[i].value;
      }
    }
    var opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
    select.value = name;
    return name;
  }

  function cardCharacters(card) {
    var raw = card.getAttribute("data-characters") || "";
    if (!raw) return [];
    return raw.split("|").map(function (s) { return normalize(s); }).filter(Boolean);
  }

  function cardText(card) {
    var parts = [];
    parts.push(card.getAttribute("data-title") || "");
    parts.push(card.getAttribute("data-map") || "");
    parts.push(card.getAttribute("data-role") || "");
    parts.push(card.getAttribute("data-side") || "");
    parts.push(card.getAttribute("data-characters") || "");
    var title = card.querySelector(".article-title");
    var desc = card.querySelector(".article-desc");
    var meta = card.querySelector(".article-meta");
    if (title) parts.push(title.textContent || "");
    if (desc) parts.push(desc.textContent || "");
    if (meta) parts.push(meta.textContent || "");
    return normalize(parts.join(" "));
  }

  function hasActiveFilters() {
    var query = normalize(searchInput ? searchInput.value : "");
    var character = normalize(characterSelect ? characterSelect.value : "");
    var map = normalize(mapSelect ? mapSelect.value : "");
    var role = normalize(roleSelect ? roleSelect.value : "");
    var side = normalize(sideSelect ? sideSelect.value : "");
    return !!(query || character || map || role || side);
  }

  function applyFilters() {
    var query = normalize(searchInput ? searchInput.value : "");
    var character = normalize(characterSelect ? characterSelect.value : "");
    var map = normalize(mapSelect ? mapSelect.value : "");
    var role = normalize(roleSelect ? roleSelect.value : "");
    var side = normalize(sideSelect ? sideSelect.value : "");
    var visible = 0;

    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var cardMap = normalize(card.getAttribute("data-map"));
      var cardRole = normalize(card.getAttribute("data-role"));
      var cardSide = normalize(card.getAttribute("data-side"));
      var chars = cardCharacters(card);
      var text = cardText(card);

      var matchQuery = !query || text.indexOf(query) !== -1;
      var matchCharacter = !character || chars.indexOf(character) !== -1 || text.indexOf(character) !== -1;
      var matchMap = !map || cardMap === map;
      var matchRole = !role || cardRole === role;
      var matchSide = !side || cardSide === side;
      var show = matchQuery && matchCharacter && matchMap && matchRole && matchSide;

      card.hidden = !show;
      if (show) visible += 1;
    }

    if (emptyState) {
      var showEmpty = visible === 0;
      emptyState.hidden = !showEmpty;
      if (showEmpty && emptyText) {
        var titleEl = emptyState.querySelector(".library-empty-title");
        var eyebrowEl = emptyState.querySelector(".eyebrow");
        if (totalCount === 0) {
          if (eyebrowEl) eyebrowEl.textContent = "Пока пусто";
          if (titleEl) titleEl.textContent = "Статей пока нет";
          emptyText.textContent = "Новые гайды и разборы появятся здесь, как только будут опубликованы.";
        } else {
          if (eyebrowEl) eyebrowEl.textContent = "Нет результатов";
          if (titleEl) titleEl.textContent = "Материалы не найдены";
          var activeCharacter = characterSelect ? String(characterSelect.value || "").trim() : "";
          if (activeCharacter && !query && !map && !role && !side) {
            emptyText.textContent = "Материалы по агенту " + activeCharacter + " пока не найдены. Попробуй изменить фильтры.";
          } else if (hasActiveFilters()) {
            emptyText.textContent = "Попробуй изменить фильтры или поисковый запрос.";
          } else {
            emptyText.textContent = "Материалы не найдены.";
          }
        }
      }
    }
  }

  function initToggles() {
    var toggles = grid.querySelectorAll(".article-toggle");
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener("click", function (e) {
        var btn = e.currentTarget;
        var targetId = btn.getAttribute("data-target");
        var body = targetId ? document.getElementById(targetId) : null;
        if (!body) return;
        var expanded = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", expanded ? "false" : "true");
        btn.textContent = expanded ? "Читать" : "Свернуть";
        body.hidden = expanded;
        var card = btn.closest(".article-card");
        if (card) {
          if (expanded) card.classList.remove("is-open");
          else card.classList.add("is-open");
        }
      });
    }
  }

  function initFromQuery() {
    var params = getParams();
    var agent = params.get("agent") || params.get("character");
    if (agent && String(agent).trim()) {
      ensureOption(characterSelect, String(agent).trim());
    }
    var map = params.get("map");
    if (map && String(map).trim()) {
      ensureOption(mapSelect, String(map).trim());
    }
    var role = params.get("role");
    if (role && String(role).trim()) {
      ensureOption(roleSelect, String(role).trim());
    }
    var side = params.get("side");
    if (side && String(side).trim()) {
      ensureOption(sideSelect, String(side).trim());
    }
    var q = params.get("q");
    if (q && String(q).trim() && searchInput) {
      searchInput.value = String(q).trim();
    }
  }

  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (characterSelect) characterSelect.addEventListener("change", applyFilters);
  if (mapSelect) mapSelect.addEventListener("change", applyFilters);
  if (roleSelect) roleSelect.addEventListener("change", applyFilters);
  if (sideSelect) sideSelect.addEventListener("change", applyFilters);

  initToggles();
  initFromQuery();
  applyFilters();
})();