(function () {
  "use strict";

  var API_URL = "https://valorant-api.com/v1/agents?isPlayableCharacter=true";
  var listEl = document.getElementById("home-agents-list");
  var statusEl = document.getElementById("home-agents-status");
  var statusText = statusEl ? statusEl.querySelector(".agents-status-text") : null;
  var countEl = document.getElementById("home-agents-count");
  var errorBox = document.getElementById("home-agents-error");
  var errorMessage = document.getElementById("home-agents-error-message");
  var retryBtn = document.getElementById("home-agents-retry");

  if (!listEl || !statusEl || !errorBox) return;

  function setLoading(loading) {
    statusEl.hidden = !loading;
    if (loading) {
      errorBox.hidden = true;
      listEl.innerHTML = "";
      if (countEl) countEl.textContent = "";
      if (statusText) statusText.textContent = "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0430\u0433\u0435\u043d\u0442\u043e\u0432...";
    }
  }

  function showError(message) {
    statusEl.hidden = true;
    listEl.innerHTML = "";
    if (countEl) countEl.textContent = "";
    if (errorMessage && message) errorMessage.textContent = message;
    errorBox.hidden = false;
  }

  function normalizeName(name) {
    return String(name || "").trim().toLowerCase();
  }

  function pickAgent(current, candidate) {
    if (!current) return candidate;
    var currentIcon = current.displayIcon || current.fullPortrait || "";
    var candidateIcon = candidate.displayIcon || candidate.fullPortrait || "";
    if (!currentIcon && candidateIcon) return candidate;
    return current;
  }

  function prepareAgents(data) {
    var byName = {};
    var list = Array.isArray(data) ? data : [];

    for (var i = 0; i < list.length; i++) {
      var agent = list[i];
      if (!agent || !agent.isPlayableCharacter) continue;
      var name = String(agent.displayName || "").trim();
      if (!name) continue;
      var key = normalizeName(name);
      byName[key] = pickAgent(byName[key], agent);
    }

    return Object.keys(byName)
      .map(function (key) { return byName[key]; })
      .sort(function (a, b) {
        return String(a.displayName).localeCompare(String(b.displayName), "en", { sensitivity: "base" });
      });
  }

  function getAgentsWord(count) {
    var mod10 = count % 10;
    var mod100 = count % 100;
    if (mod10 === 1 && mod100 !== 11) return "\u0430\u0433\u0435\u043d\u0442";
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "\u0430\u0433\u0435\u043d\u0442\u0430";
    return "\u0430\u0433\u0435\u043d\u0442\u043e\u0432";
  }

  function createAgentItem(agent) {
    var name = String(agent.displayName || "").trim();
    var item = document.createElement("a");
    item.className = "home-agent-item";
    item.href = "/library?agent=" + encodeURIComponent(name);
    item.setAttribute("aria-label", "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b \u043f\u043e \u0430\u0433\u0435\u043d\u0442\u0443 " + name + " \u0432 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0435");
    item.title = name;

    var icon = agent.displayIcon || agent.fullPortrait || agent.bustPortrait || "";
    if (icon) {
      var img = document.createElement("img");
      img.className = "home-agent-icon";
      img.src = icon;
      img.alt = "";
      img.loading = "lazy";
      img.decoding = "async";
      img.width = 64;
      img.height = 64;
      img.draggable = false;
      img.setAttribute("aria-hidden", "true");
      img.addEventListener("error", function () {
        img.remove();
        var fallback = document.createElement("span");
        fallback.className = "home-agent-fallback";
        fallback.setAttribute("aria-hidden", "true");
        fallback.textContent = name.charAt(0).toUpperCase();
        item.insertBefore(fallback, item.firstChild);
      });
      item.appendChild(img);
    } else {
      var fallbackNoIcon = document.createElement("span");
      fallbackNoIcon.className = "home-agent-fallback";
      fallbackNoIcon.setAttribute("aria-hidden", "true");
      fallbackNoIcon.textContent = name.charAt(0).toUpperCase();
      item.appendChild(fallbackNoIcon);
    }

    var label = document.createElement("span");
    label.className = "home-agent-name";
    label.textContent = name;
    item.appendChild(label);

    return item;
  }

  function renderAgents(agents) {
    listEl.innerHTML = "";
    if (!agents.length) {
      statusEl.hidden = false;
      if (statusText) statusText.textContent = "\u0410\u0433\u0435\u043d\u0442\u044b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b.";
      if (countEl) countEl.textContent = "0 \u0430\u0433\u0435\u043d\u0442\u043e\u0432";
      return;
    }

    var fragment = document.createDocumentFragment();
    for (var i = 0; i < agents.length; i++) {
      fragment.appendChild(createAgentItem(agents[i]));
    }
    listEl.appendChild(fragment);
    statusEl.hidden = true;
    if (countEl) countEl.textContent = agents.length + " " + getAgentsWord(agents.length);
  }

  function loadAgents() {
    setLoading(true);

    fetch(API_URL, {
      method: "GET",
      headers: { "Accept": "application/json" }
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (payload) {
        var agents = prepareAgents(payload && payload.data);
        renderAgents(agents);
      })
      .catch(function () {
        showError("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435 \u0441 valorant-api.com. \u041f\u0440\u043e\u0432\u0435\u0440\u044c \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 \u0438\u043b\u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u043f\u043e\u0437\u0436\u0435.");
      });
  }

  if (retryBtn) {
    retryBtn.addEventListener("click", loadAgents);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadAgents);
  } else {
    loadAgents();
  }
})();
