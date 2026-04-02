const DEFAULT_SETTINGS = {
  apiBaseUrl: "https://starringcodextrpg.onrender.com",
  seed: 1729,
  seasons: 10,
  archetype: "balanced",
  worldJson: "",
  shellVisible: false
};

async function ensureDefaults() {
  const current = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  await chrome.storage.sync.set({ ...DEFAULT_SETTINGS, ...current });
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab;
}

function isChatGptUrl(url) {
  return String(url || "").startsWith("https://chatgpt.com/") || String(url || "").startsWith("https://chat.openai.com/");
}

async function sendToActiveTab(message) {
  const tab = await getActiveTab();
  if (!tab?.id) {
    throw new Error("アクティブなタブが見つかりません。");
  }
  if (!isChatGptUrl(tab.url)) {
    throw new Error("ChatGPT のタブで実行してください。");
  }
  return chrome.tabs.sendMessage(tab.id, message);
}

chrome.runtime.onInstalled.addListener(async () => {
  await ensureDefaults();
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

chrome.runtime.onStartup.addListener(async () => {
  await ensureDefaults();
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    switch (message?.type) {
      case "shell.get-settings": {
        const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
        return { ...DEFAULT_SETTINGS, ...settings };
      }
      case "shell.apply-settings": {
        const nextSettings = { ...DEFAULT_SETTINGS, ...(message.settings || {}) };
        await chrome.storage.sync.set(nextSettings);
        await sendToActiveTab({ type: "shell.settings-updated", settings: nextSettings }).catch(() => null);
        return nextSettings;
      }
      case "shell.toggle-active":
        return sendToActiveTab({ type: "shell.toggle" });
      case "shell.show-active":
        return sendToActiveTab({ type: "shell.show" });
      case "shell.hide-active":
        return sendToActiveTab({ type: "shell.hide" });
      case "shell.refresh-active":
        return sendToActiveTab({ type: "shell.refresh" });
      case "hub.open-window": {
        const drawer = String(message.drawer || "character");
        const url = chrome.runtime.getURL(`hub/hub.html?drawer=${encodeURIComponent(drawer)}`);
        const created = await chrome.windows.create({
          url,
          type: "popup",
          width: 1380,
          height: 940
        });
        return { windowId: created.id, url };
      }
      case "hub.get-state": {
        const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
        const local = await chrome.storage.local.get({ shellSnapshotCache: null });
        return {
          settings: { ...DEFAULT_SETTINGS, ...settings },
          cache: local.shellSnapshotCache
        };
      }
      case "sidepanel.open-active": {
        const tab = await getActiveTab();
        if (!tab?.windowId) {
          throw new Error("設定パネルを開く対象のウィンドウが見つかりません。");
        }
        await chrome.sidePanel.open({ windowId: tab.windowId });
        return { opened: true };
      }
      case "chatgpt.open-tab": {
        const tab = await chrome.tabs.create({ url: "https://chatgpt.com/" });
        return { tabId: tab.id, url: tab.url };
      }
      case "chatgpt.inspect-active": {
        const tab = await getActiveTab();
        return {
          tabId: tab?.id || null,
          url: tab?.url || null,
          isChatGpt: isChatGptUrl(tab?.url)
        };
      }
      case "api.ping": {
        const baseUrl = String(message.baseUrl || DEFAULT_SETTINGS.apiBaseUrl).replace(/\/+$/, "");
        const [health, snapshot] = await Promise.all([
          fetch(`${baseUrl}/health`).then(async (response) => ({
            ok: response.ok,
            status: response.status,
            body: await response.text()
          })),
          fetch(`${baseUrl}/api/front/snapshot?seed=1729`).then(async (response) => {
            const text = await response.text();
            let data = null;
            try {
              data = text ? JSON.parse(text) : null;
            } catch {
              data = { raw: text };
            }
            return {
              ok: response.ok,
              status: response.status,
              data
            };
          })
        ]);
        return { baseUrl, health, snapshot };
      }
      case "api.request": {
        const response = await fetch(message.url, {
          method: message.method || "GET",
          headers: message.headers || {},
          body: message.body || undefined
        });
        const text = await response.text();
        let data = null;
        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          data = { raw: text };
        }
        return {
          ok: response.ok,
          status: response.status,
          data
        };
      }
      default:
        throw new Error(`未対応のメッセージです: ${message?.type || "unknown"}`);
    }
  })()
    .then((result) => sendResponse({ ok: true, result }))
    .catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});
