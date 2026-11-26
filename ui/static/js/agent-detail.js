(function () {
  "use strict";

  var API_URL = "https://valorant-api.com/v1/agents?isPlayableCharacter=true";
  var root = document.getElementById("agent-detail");
  var status = document.getElementById("agent-status");
  var statusText = status ? status.querySelector(".agents-status-text") : null;
  var errorBox = document.getElementById("agent-error");
  var errorMessage = document.getElementById("agent-error-message");
  var content = document.getElementById("agent-content");
  var retryBtn = document.getElementById("agent-retry");

  if (!root || !status || !errorBox || !content) return;

  var requestedSlug = slugify(root.getAttribute("data-agent-slug") || "");

  function slugify(name) {
    return String(name || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function setLoading(loading) {
    status.hidden = !loading;
    if (loading) {
      errorBox.hidden = true;
      content.hidden = true;
      if (statusText) statusText.textContent = "Загрузка агента...";
    }
  }

  function showError(message) {
    status.hidden = true;
    content.hidden = true;
    if (errorMessage && message) errorMessage.textContent = message;
    errorBox.hidden = false;
  }

  function getAgentSlug(agent) {
    return slugify(agent && agent.displayName ? agent.displayName : "");
  }

  function findAgent(agents) {
    var list = Array.isArray(agents) ? agents : [];
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      if (!a || !a.isPlayableCharacter) continue;
      if (getAgentSlug(a) === requestedSlug) return a;
    }
    return null;
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value || "";
  }

  function renderAbilities(abilities) {
    var container = document.getElementById("agent-abilities");
    if (!container) return;
    container.innerHTML = "";
    var list = Array.isArray(abilities) ? abilities : [];
    for (var i = 0; i < list.length; i++) {
      var ab = list[i];
      if (!ab) continue;
      var name = String(ab.displayName || "").trim();
      var desc = String(ab.description || "").trim();
      if (!name) continue;

      var card = document.createElement("article");
      card.className = "ability-card";

      if (ab.displayIcon) {
        var icon = document.createElement("img");
        icon.className = "ability-icon";
        icon.src = ab.displayIcon;
        icon.alt = "";
        icon.loading = "lazy";
        icon.decoding = "async";
        icon.width = 48;
        icon.height = 48;
        icon.setAttribute("aria-hidden", "true");
        icon.addEventListener("error", function () { this.remove(); });
        card.appendChild(icon);
      }

      var slot = document.createElement("p");
      slot.className = "ability-slot";
      slot.textContent = String(ab.slot || "Ability").replace("Ability", "Ability ");

      var h3 = document.createElement("h3");
      h3.className = "ability-name";
      h3.textContent = name;

      card.appendChild(slot);
      card.appendChild(h3);

      if (desc) {
        var p = document.createElement("p");
        p.className = "ability-desc";
        p.textContent = desc;
        card.appendChild(p);
      }

      container.appendChild(card);
    }

    if (!container.children.length) {
      var empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Информация о способностях недоступна.";
      container.appendChild(empty);
    }
  }

  function renderAgent(agent) {
    var name = String(agent.displayName || "").trim();
    var roleName = agent.role && agent.role.displayName ? String(agent.role.displayName).trim() : "";
    var description = String(agent.description || "").trim();
    var portrait = agent.fullPortraitV2 || agent.fullPortrait || agent.bustPortrait || agent.displayIcon || "";

    document.title = name + " — Edenguide";
    setText("agent-name", name);
    setText("agent-role", roleName || "Роль неизвестна");
    setText("agent-description", description || "Описание агента недоступно.");

    var portraitImg = document.getElementById("agent-portrait");
    if (portraitImg) {
      if (portrait) {
        portraitImg.src = portrait;
        portraitImg.alt = "Портрет агента " + name;
        portraitImg.hidden = false;
      } else {
        portraitImg.hidden = true;
      }
    }

    renderAbilities(agent.abilities);

    status.hidden = true;
    errorBox.hidden = true;
    content.hidden = false;
  }

  function loadAgent() {
    if (!requestedSlug) {
      showError("Не указан идентификатор агента.");
      return;
    }

    setLoading(true);
    fetch(API_URL, {
      method: "GET",
      headers: { "Accept": "application/json" }
    })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (payload) {
        var agent = findAgent(payload && payload.data);
        if (!agent) {
          showError("Агент с адресом /agent/" + requestedSlug + " не найден. Проверь ссылку или вернись на главную.");
          return;
        }
        renderAgent(agent);
      })
      .catch(function () {
        showError("Не удалось получить данные агента. Проверь соединение или попробуй позже.");
      });
  }

  if (retryBtn) retryBtn.addEventListener("click", loadAgent);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadAgent);
  } else {
    loadAgent();
  }
})();
