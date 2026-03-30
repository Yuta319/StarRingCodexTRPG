async function runtimeRequest(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response?.ok) {
    throw new Error(response?.error || "拡張通信に失敗しました。");
  }
  return response.result;
}

const form = document.getElementById("settings-form");
const statusText = document.getElementById("status-text");
const statusDetail = document.getElementById("status-detail");
const openChatGptButton = document.getElementById("open-chatgpt");
const showShellButton = document.getElementById("show-shell");
const hideShellButton = document.getElementById("hide-shell");
const refreshShellButton = document.getElementById("refresh-shell");
const pingApiButton = document.getElementById("ping-api");
const clearWorldJsonButton = document.getElementById("clear-world-json");

const fields = {
  apiBaseUrl: document.getElementById("api-base-url"),
  seed: document.getElementById("seed"),
  seasons: document.getElementById("seasons"),
  archetype: document.getElementById("archetype"),
  worldJson: document.getElementById("world-json")
};

function setStatus(text, tone = "idle") {
  statusText.textContent = text;
  statusText.dataset.tone = tone;
}

function setDetail(rows = []) {
  statusDetail.innerHTML = rows
    .map((row) => `<div class="status-detail__row">${row}</div>`)
    .join("");
}

function applySettingsToForm(settings) {
  fields.apiBaseUrl.value = settings.apiBaseUrl || "";
  fields.seed.value = settings.seed ?? 1729;
  fields.seasons.value = settings.seasons ?? 10;
  fields.archetype.value = settings.archetype || "balanced";
  fields.worldJson.value = settings.worldJson || "";
}

async function loadSettings() {
  const settings = await runtimeRequest({ type: "shell.get-settings" });
  applySettingsToForm(settings);
  setStatus("現在の設定を読み込みました。", "ok");
  const active = await runtimeRequest({ type: "chatgpt.inspect-active" });
  setDetail([
    `アクティブタブ: ${active.isChatGpt ? "ChatGPT" : "ChatGPT ではありません"}`,
    `URL: ${active.url || "未取得"}`
  ]);
}

async function saveSettings(event) {
  event.preventDefault();
  const nextSettings = {
    apiBaseUrl: fields.apiBaseUrl.value.trim(),
    seed: Number(fields.seed.value || 1729),
    seasons: Number(fields.seasons.value || 10),
    archetype: fields.archetype.value.trim() || "balanced",
    worldJson: fields.worldJson.value.trim()
  };
  await runtimeRequest({ type: "shell.apply-settings", settings: nextSettings });
  setStatus("設定を保存しました。表示中の shell にも反映します。", "ok");
}

form.addEventListener("submit", (event) => {
  saveSettings(event).catch((error) => setStatus(error.message, "error"));
});

openChatGptButton.addEventListener("click", async () => {
  const result = await runtimeRequest({ type: "chatgpt.open-tab" });
  setStatus("ChatGPT タブを開きました。読み込み後に shell を開けます。", "ok");
  setDetail([`新しいタブ: ${result.url || "https://chatgpt.com/"}`]);
});

showShellButton.addEventListener("click", async () => {
  await runtimeRequest({ type: "shell.show-active" });
  setStatus("アクティブな ChatGPT タブで shell を開きました。", "ok");
});

hideShellButton.addEventListener("click", async () => {
  await runtimeRequest({ type: "shell.hide-active" });
  setStatus("アクティブな ChatGPT タブで shell を閉じました。", "ok");
});

refreshShellButton.addEventListener("click", async () => {
  await runtimeRequest({ type: "shell.refresh-active" });
  setStatus("現在の設定で shell を再読込しました。", "ok");
});

pingApiButton.addEventListener("click", async () => {
  const baseUrl = fields.apiBaseUrl.value.trim() || "https://starringcodextrpg.onrender.com";
  const result = await runtimeRequest({ type: "api.ping", baseUrl });
  setStatus(`API 疎通を確認しました: ${result.baseUrl}`, result.health.ok && result.snapshot.ok ? "ok" : "error");
  setDetail([
    `/health: ${result.health.status} / ${String(result.health.body || "").trim() || "empty"}`,
    `/api/front/snapshot?seed=1729: ${result.snapshot.status} / ${result.snapshot.ok ? "OK" : "NG"}`
  ]);
});

clearWorldJsonButton.addEventListener("click", () => {
  fields.worldJson.value = "";
  setStatus("world_json を空にしました。保存すると seed 読み込みへ戻ります。", "ok");
});

loadSettings().catch((error) => setStatus(error.message, "error"));
