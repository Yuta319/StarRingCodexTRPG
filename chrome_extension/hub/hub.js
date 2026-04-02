const APP = document.getElementById("app");

const STATE = {
  drawer: new URLSearchParams(location.search).get("drawer") || "character",
  settings: null,
  cache: null,
  status: "表示データを読み込んでいます。"
};

const TAB_ITEMS = [
  ["character", "Equipment"],
  ["inventory", "Inventory"],
  ["skills", "Skills"],
  ["quest", "Quest"],
  ["codex", "Codex"],
  ["journal", "Journal"],
  ["world", "World"],
  ["dice", "Dice"],
  ["assets", "Assets"],
  ["settings", "Settings"]
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

async function runtimeRequest(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response?.ok) {
    throw new Error(response?.error || "拡張通信に失敗しました。");
  }
  return response.result;
}

function iconUrl(filename) {
  return filename ? chrome.runtime.getURL(`assets/icons/${filename}`) : null;
}

function renderIcon({ filename, fallback, alt, featured = false }) {
  const src = iconUrl(filename);
  const cls = `hub-icon ${featured ? "hub-icon--featured" : ""}`;
  if (!src) {
    return `<div class="${cls}">${escapeHtml(fallback || "?")}</div>`;
  }
  return `<div class="${cls}"><img src="${src}" alt="${escapeHtml(alt || fallback || "icon")}" loading="lazy" /></div>`;
}

function renderTags(values = []) {
  if (!values.length) {
    return `<span class="hub-empty">まだ項目がありません。</span>`;
  }
  return values.map((value) => `<span>${escapeHtml(value)}</span>`).join("");
}

function display() {
  return STATE.cache?.display || {};
}

function cacheInfoRows() {
  const rows = [];
  if (STATE.cache?.updatedAt) {
    rows.push(`<span>updated ${escapeHtml(new Date(STATE.cache.updatedAt).toLocaleString())}</span>`);
  }
  if (STATE.cache?.playSource?.world_json) {
    rows.push("<span>world_json active</span>");
  }
  if (STATE.settings?.seed) {
    rows.push(`<span>seed ${escapeHtml(STATE.settings.seed)}</span>`);
  }
  return rows.join("");
}

function sectionCharacter(displayData) {
  const actor = displayData.actorRail || {};
  const equipment = displayData.equipmentHub || {};
  const featured = equipment.featuredItem || {};
  return `
    <div class="hub-grid hub-grid--wide">
      <section class="hub-card">
        <p class="hub-eyebrow">Equipment</p>
        <h3>${escapeHtml(equipment.loadoutName || "旅装")}</h3>
        <div class="hub-meta">
          <span>load ${escapeHtml(equipment.equipLoad?.current)}/${escapeHtml(equipment.equipLoad?.max)}</span>
          <span>${escapeHtml(equipment.equipLoad?.state || "medium")}</span>
        </div>
        <div class="hub-item-list">
          ${(equipment.slots || [])
            .map(
              (item) => `
                <article class="hub-item">
                  ${renderIcon({ filename: item.iconFilename || `${item.iconKey}.png`, fallback: (item.slotLabel || "?")[0], alt: item.name })}
                  <div>
                    <p class="hub-eyebrow">${escapeHtml(item.slotLabel)}</p>
                    <h4>${escapeHtml(item.name)}</h4>
                    <p>${escapeHtml(item.subtitle)}</p>
                    <div class="hub-meta">
                      <span>${escapeHtml(item.rarityLabel || item.rarity || "")}</span>
                      <span>${escapeHtml(item.assetState || "queued")}</span>
                    </div>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Featured</p>
        <div class="hub-featured">
          ${renderIcon({ filename: featured.iconFilename || `${featured.iconKey || ""}.png`, fallback: "装", alt: featured.name, featured: true })}
          <div>
            <h3>${escapeHtml(featured.name || "装備詳細")}</h3>
            <p>${escapeHtml(featured.subtitle || "")}</p>
            <div class="hub-meta">
              <span>${escapeHtml(featured.rarityLabel || featured.rarity || "")}</span>
              <span>${escapeHtml(featured.assetState || "queued")}</span>
            </div>
          </div>
        </div>
        <div class="hub-tags">${renderTags(featured.stats || [])}</div>
        <p>${escapeHtml(featured.flavorText || "装備の記録はまだありません。")}</p>
        <div class="hub-stat-grid">
          <div><span>HP</span><strong>${escapeHtml(actor.hp?.current)}/${escapeHtml(actor.hp?.max)}</strong></div>
          <div><span>MP</span><strong>${escapeHtml(actor.mp?.current)}/${escapeHtml(actor.mp?.max)}</strong></div>
          <div><span>Vessel</span><strong>${escapeHtml(actor.vessel)}</strong></div>
          <div><span>存在級位</span><strong>${escapeHtml(actor.existenceTitle)}</strong></div>
        </div>
        <div class="hub-inline-list">
          ${(equipment.flavorNotes || []).map((line) => `<p>${escapeHtml(line)}</p>`).join("")}
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Relics</p>
        <h3>遺物スロット</h3>
        <div class="hub-item-list">
          ${(equipment.relics || [])
            .map(
              (item) => `
                <article class="hub-item">
                  ${renderIcon({ filename: item.iconFilename || `${item.iconKey}.png`, fallback: "R", alt: item.name })}
                  <div>
                    <h4>${escapeHtml(item.name)}</h4>
                    <div class="hub-meta">
                      <span>${escapeHtml(item.rarityLabel || item.rarity || "")}</span>
                      <span>${escapeHtml(item.assetState || "queued")}</span>
                    </div>
                    <p>${escapeHtml(item.flavorText)}</p>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Attuned Magic</p>
        <h3>記憶魔法</h3>
        <div class="hub-item-list">
          ${(equipment.attunedSpells || [])
            .map(
              (spell) => `
                <article class="hub-item">
                  ${renderIcon({ filename: spell.iconFilename || `${spell.iconKey}.png`, fallback: "M", alt: spell.name })}
                  <div>
                    <h4>${escapeHtml(spell.name)}</h4>
                    <div class="hub-meta">
                      <span>${escapeHtml(spell.attribute)}</span>
                      <span>${escapeHtml(spell.rank)}</span>
                      <span>MP ${escapeHtml(spell.mpCost)}</span>
                    </div>
                    <p>${escapeHtml(spell.description)}</p>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

function sectionInventory(displayData) {
  const inventory = displayData.inventoryHub || {};
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Inventory</p>
        <h3>所持品</h3>
        <div class="hub-meta">
          <span>${escapeHtml(inventory.capacity?.used)}/${escapeHtml(inventory.capacity?.max)}</span>
          <span>quick ${(inventory.quickUse || []).length}</span>
        </div>
        <div class="hub-group-list">
          ${(inventory.groups || [])
            .map(
              (group) => `
                <section class="hub-group">
                  <h4>${escapeHtml(group.label)}</h4>
                  <div class="hub-item-list">
                    ${(group.items || [])
                      .map(
                        (item) => `
                          <article class="hub-item">
                            ${renderIcon({ filename: item.iconFilename || `${item.iconKey}.png`, fallback: (item.category || "?")[0], alt: item.name })}
                            <div>
                              <h4>${escapeHtml(item.name)} ×${escapeHtml(item.quantity)}</h4>
                              <div class="hub-meta">
                                <span>${escapeHtml(item.category)}</span>
                                <span>${escapeHtml(item.assetState || "queued")}</span>
                              </div>
                              <p>${escapeHtml(item.description)}</p>
                            </div>
                          </article>
                        `
                      )
                      .join("")}
                  </div>
                </section>
              `
            )
            .join("")}
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Carry Over</p>
        <h3>守れたものの候補</h3>
        <div class="hub-tags">${renderTags(displayData.nextSessionHook?.protectedAssets || [])}</div>
      </section>
    </div>
  `;
}

function sectionSkills(displayData) {
  const actor = displayData.actorRail || {};
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Vectors</p>
        <h3>技能ベクトル</h3>
        <div class="hub-stat-grid">
          ${Object.entries(actor.skills || {})
            .map(([key, value]) => `<div><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`)
            .join("")}
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Quick Skills</p>
        <h3>即応スロット</h3>
        <div class="hub-tags">${renderTags((actor.quickSlots || []).map((item) => item.label))}</div>
      </section>
    </div>
  `;
}

function sectionQuest(displayData) {
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Node Board</p>
        <h3>${escapeHtml(displayData.activeNode?.title || "現在のノード")}</h3>
        <p>${escapeHtml(displayData.activeNodeGuide?.summary || displayData.currentEvent?.summaryText || "まだ quest 情報がありません。")}</p>
        <div class="hub-tags">${renderTags((displayData.activeNode?.recommendedVectors || []).map((value) => `#${value}`))}</div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Branches</p>
        <h3>分岐候補</h3>
        <div class="hub-branch-list">
          ${(displayData.currentEvent?.branchPreview || [])
            .slice(0, 5)
            .map((branch) => `<article><h4>${escapeHtml(branch.label)}</h4><p>${escapeHtml(branch.summaryText)}</p></article>`)
            .join("") || "<p class='hub-empty'>まだ分岐候補がありません。</p>"}
        </div>
      </section>
    </div>
  `;
}

function sectionCodex(displayData) {
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Codex</p>
        <h3>焦点人物</h3>
        <div class="hub-codex-list">
          ${(displayData.namedCast || [])
            .slice(0, 6)
            .map((item) => `<article><h4>${escapeHtml(item.displayName)}</h4><p>${escapeHtml(item.conflictText || item.traceText || "記録待ち")}</p></article>`)
            .join("") || "<p class='hub-empty'>まだ人物記録がありません。</p>"}
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Relation</p>
        <h3>相関図の前段</h3>
        <p>相関図そのものは次段ですが、ここでは焦点 NPC、対立文、残留圧を読みやすく整理します。</p>
      </section>
    </div>
  `;
}

function sectionJournal(displayData) {
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Journal</p>
        <h3>セッションの持ち越し</h3>
        <div class="hub-tags">${renderTags(displayData.nextSessionHook?.carriedPressures || [])}</div>
        <div class="hub-tags">${renderTags(displayData.nextSessionHook?.npcCarryOvers || [])}</div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Ending</p>
        <h3>小結末</h3>
        <p>${escapeHtml(displayData.sessionEnding?.summary || displayData.endingForecast?.summary || "まだ小結末は確定していません。")}</p>
      </section>
    </div>
  `;
}

function sectionWorld(displayData) {
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">World</p>
        <h3>世界脈動</h3>
        <div class="hub-stat-grid">
          <div><span>主神</span><strong>${escapeHtml(displayData.worldSpine?.mainGodLabel)}</strong></div>
          <div><span>連鎖</span><strong>${escapeHtml(displayData.worldSpine?.activeChainLabel)}</strong></div>
          <div><span>同期</span><strong>${escapeHtml(displayData.worldSpine?.syncState)}</strong></div>
          <div><span>分岐</span><strong>${escapeHtml(displayData.worldSpine?.dominantBranch)}</strong></div>
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Institution</p>
        <h3>制度圧</h3>
        <p>${escapeHtml(displayData.institutionAlertGuide?.summary || displayData.institutionAlert?.label || "まだ制度圧は薄いです。")}</p>
      </section>
    </div>
  `;
}

function sectionAssets(displayData) {
  const pack = displayData.assetPromptPack || {};
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Assets</p>
        <h3>量産用 prompt pack</h3>
        <p>${escapeHtml(pack.visualDirection || "")}</p>
        <div class="hub-meta">
          <span>entries ${escapeHtml(pack.entryCount || 0)}</span>
          <span>${escapeHtml(pack.batchTitle || "asset-pack")}</span>
        </div>
        <p>${escapeHtml(pack.exportCommand || "")}</p>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Prompt Entries</p>
        <h3>生成済みアイコン</h3>
        <div class="hub-item-list">
          ${(pack.entries || [])
            .filter((entry) => String(entry.kind || "").endsWith("_icon"))
            .slice(0, 12)
            .map(
              (entry) => `
                <article class="hub-item">
                  ${renderIcon({ filename: entry.suggestedFilename, fallback: "A", alt: entry.label })}
                  <div>
                    <h4>${escapeHtml(entry.label)}</h4>
                    <div class="hub-meta">
                      <span>${escapeHtml(entry.kind)}</span>
                      <span>${escapeHtml(entry.assetState || "queued")}</span>
                    </div>
                    <p>${escapeHtml(entry.suggestedFilename)}</p>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

function sectionSettings() {
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Settings</p>
        <h3>現在の接続先</h3>
        <div class="hub-stat-grid">
          <div><span>API</span><strong>${escapeHtml(STATE.settings?.apiBaseUrl)}</strong></div>
          <div><span>seed</span><strong>${escapeHtml(STATE.settings?.seed)}</strong></div>
          <div><span>seasons</span><strong>${escapeHtml(STATE.settings?.seasons)}</strong></div>
          <div><span>archetype</span><strong>${escapeHtml(STATE.settings?.archetype)}</strong></div>
        </div>
      </section>
      <section class="hub-card">
        <p class="hub-eyebrow">Status</p>
        <h3>現在の状態</h3>
        <p>${escapeHtml(STATE.status)}</p>
      </section>
    </div>
  `;
}

function sectionDice() {
  return `
    <div class="hub-grid">
      <section class="hub-card">
        <p class="hub-eyebrow">Dice</p>
        <h3>Dice Tray</h3>
        <p>Dice Tray は次段で event contract と連携します。現段階では choice と自由行動の結果を優先しています。</p>
      </section>
    </div>
  `;
}

function renderSection() {
  const data = display();
  switch (STATE.drawer) {
    case "character":
      return sectionCharacter(data);
    case "inventory":
      return sectionInventory(data);
    case "skills":
      return sectionSkills(data);
    case "quest":
      return sectionQuest(data);
    case "codex":
      return sectionCodex(data);
    case "journal":
      return sectionJournal(data);
    case "world":
      return sectionWorld(data);
    case "assets":
      return sectionAssets(data);
    case "settings":
      return sectionSettings();
    case "dice":
    default:
      return sectionDice();
  }
}

function render() {
  APP.innerHTML = `
    <div class="hub-shell">
      <header class="hub-header">
        <div>
          <p class="hub-eyebrow">Star Ring Codex Hub</p>
          <h1>${escapeHtml(TAB_ITEMS.find(([key]) => key === STATE.drawer)?.[1] || "Hub")}</h1>
          <p class="hub-muted">${escapeHtml(STATE.status)}</p>
        </div>
        <div class="hub-actions">
          ${cacheInfoRows()}
          <button id="refresh-hub">現在の状態を再読込</button>
        </div>
      </header>
      <nav class="hub-tabs">
        ${TAB_ITEMS.map(
          ([key, label]) => `<button class="${STATE.drawer === key ? "is-active" : ""}" data-tab="${key}">${escapeHtml(label)}</button>`
        ).join("")}
      </nav>
      ${renderSection()}
    </div>
  `;

  APP.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      STATE.drawer = button.getAttribute("data-tab");
      const url = new URL(location.href);
      url.searchParams.set("drawer", STATE.drawer);
      history.replaceState({}, "", url);
      render();
    });
  });

  APP.querySelector("#refresh-hub")?.addEventListener("click", () => refreshSnapshot());
}

async function refreshSnapshot() {
  const source = STATE.cache?.playSource?.world_json
    ? { world_json: STATE.cache.playSource.world_json }
    : {
        seed: Number(STATE.settings?.seed || 1729),
        seasons: Number(STATE.settings?.seasons || 10),
        archetype: STATE.settings?.archetype || "balanced"
      };
  const base = String(STATE.settings?.apiBaseUrl || "").replace(/\/+$/, "");
  const url = `${base}/api/front/snapshot?${new URLSearchParams(source).toString()}`;
  const response = await runtimeRequest({ type: "api.request", url, method: "GET" });
  if (!response.ok) {
    throw new Error(response.data?.error || "front snapshot の再取得に失敗しました。");
  }
  STATE.cache = {
    ...(STATE.cache || {}),
    display: response.data.display,
    playSource: response.data.playSource,
    settings: STATE.settings,
    updatedAt: new Date().toISOString()
  };
  STATE.status = "現在の状態を再読込しました。";
  await chrome.storage.local.set({ shellSnapshotCache: STATE.cache });
  render();
}

async function init() {
  const result = await runtimeRequest({ type: "hub.get-state" });
  STATE.settings = result.settings;
  STATE.cache = result.cache;
  STATE.status = result.cache?.display ? "保存済みスナップショットを表示しています。" : "まだ shell の読み込み結果がありません。";
  render();
}

init().catch((error) => {
  STATE.status = error.message;
  render();
});
