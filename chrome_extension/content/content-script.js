(function bootstrapStarRingShell() {
  if (window.__starRingCodexShellMounted) {
    return;
  }
  window.__starRingCodexShellMounted = true;

  const STATE = {
    visible: false,
    pending: false,
    display: null,
    settings: null,
    playSource: { seed: 1729, world_json: null },
    saveRef: { saveId: null, savePath: null },
    drawer: "quest",
    freeActionDraft: "",
    status: { tone: "idle", text: "シェルは待機中です。" }
  };

  const host = document.createElement("div");
  host.id = "star-ring-codex-shell-host";
  document.documentElement.append(host);
  const shadow = host.attachShadow({ mode: "open" });

  const stylesheet = document.createElement("link");
  stylesheet.rel = "stylesheet";
  stylesheet.href = chrome.runtime.getURL("content/overlay.css");
  shadow.append(stylesheet);

  const mount = document.createElement("div");
  shadow.append(mount);

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

  function currentSourcePayload() {
    if (STATE.playSource.world_json) {
      return { world_json: STATE.playSource.world_json };
    }
    if (STATE.settings.worldJson) {
      return { world_json: STATE.settings.worldJson };
    }
    return {
      seed: Number(STATE.settings.seed || 1729),
      seasons: Number(STATE.settings.seasons || 10),
      archetype: STATE.settings.archetype || "balanced"
    };
  }

  async function apiRequest(path, options = {}) {
    const base = String(STATE.settings.apiBaseUrl || "").replace(/\/+$/, "");
    if (!base) {
      throw new Error("API Base URL が未設定です。");
    }
    const url = options.query
      ? `${base}${path}?${new URLSearchParams(options.query).toString()}`
      : `${base}${path}`;
    const headers = options.body ? { "Content-Type": "application/json" } : {};
    return runtimeRequest({
      type: "api.request",
      url,
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : null
    });
  }

  function setStatus(text, tone = "idle") {
    STATE.status = { text, tone };
    render();
  }

  function describeSource(payload) {
    if (payload?.request?.world_json) {
      return "保存済み world の続きから読み込みました。";
    }
    if (payload?.request?.seed) {
      return `seed ${payload.request.seed} から場面を開きました。`;
    }
    return "場面を更新しました。";
  }

  function applyDisplayPayload(payload, successText) {
    STATE.display = payload.display || STATE.display;
    if (payload.playSource) {
      STATE.playSource = {
        seed: payload.playSource.seed ?? STATE.settings.seed,
        world_json: payload.playSource.world_json ?? payload.playSource.worldJson ?? null
      };
    }
    if (payload.saveMeta || payload.display?.saveMeta) {
      const saveMeta = payload.saveMeta || payload.display?.saveMeta;
      STATE.saveRef = {
        saveId: saveMeta?.saveId ?? null,
        savePath: saveMeta?.savePath ?? null
      };
    }
    setStatus(successText || describeSource(payload), "ok");
  }

  async function loadSnapshot() {
    STATE.pending = true;
    render();
    setStatus("表示データを読み込んでいます。", "loading");
    try {
      const query = STATE.settings.worldJson
        ? { world_json: STATE.settings.worldJson }
        : {
            seed: Number(STATE.settings.seed || 1729),
            seasons: Number(STATE.settings.seasons || 10),
            archetype: STATE.settings.archetype || "balanced"
          };
      const payload = await apiRequest("/api/front/snapshot", { query });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "front snapshot の取得に失敗しました。");
      }
      applyDisplayPayload(payload.data, describeSource(payload.data));
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  async function postChoice(choiceId) {
    STATE.pending = true;
    render();
    setStatus(`${choiceId} を送っています。`, "loading");
    try {
      const payload = await apiRequest("/api/front/play", {
        method: "POST",
        body: {
          choiceId,
          ...currentSourcePayload()
        }
      });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "通常行動の送信に失敗しました。");
      }
      applyDisplayPayload(payload.data, "通常行動を反映しました。");
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  async function postFreeAction() {
    const text = STATE.freeActionDraft.trim();
    if (!text) {
      setStatus("自由行動の内容を入力してください。", "error");
      return;
    }
    STATE.pending = true;
    render();
    setStatus("自由行動を送っています。", "loading");
    try {
      const payload = await apiRequest("/api/front/free-action", {
        method: "POST",
        body: {
          actionText: text,
          ...currentSourcePayload()
        }
      });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "自由行動の送信に失敗しました。");
      }
      STATE.freeActionDraft = "";
      applyDisplayPayload(payload.data, "自由行動を反映しました。");
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  async function saveSession() {
    if (!STATE.playSource.world_json) {
      setStatus("保存対象の world_json がまだありません。", "error");
      return;
    }
    STATE.pending = true;
    render();
    setStatus("このセッションを保存しています。", "loading");
    try {
      const payload = await apiRequest("/api/save-session", {
        method: "POST",
        body: { world_json: STATE.playSource.world_json }
      });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "保存に失敗しました。");
      }
      STATE.saveRef = {
        saveId: payload.data?.saveId ?? null,
        savePath: payload.data?.savePath ?? null
      };
      setStatus(`保存しました: ${payload.data?.saveId || "save"}`, "ok");
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  async function loadSavedSession() {
    STATE.pending = true;
    render();
    setStatus("保存済みセッションを読み込んでいます。", "loading");
    try {
      const body = STATE.saveRef.saveId
        ? { saveId: STATE.saveRef.saveId }
        : STATE.saveRef.savePath
          ? { savePath: STATE.saveRef.savePath }
          : {};
      const payload = await apiRequest("/api/front/load-session", {
        method: "POST",
        body
      });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "保存済みセッションの読込に失敗しました。");
      }
      applyDisplayPayload(payload.data, "保存済みセッションを開きました。");
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  async function nextSession() {
    if (!STATE.playSource.world_json) {
      setStatus("次のセッションへ進む前に world_json が必要です。", "error");
      return;
    }
    STATE.pending = true;
    render();
    setStatus("次のセッションへ進めています。", "loading");
    try {
      const payload = await apiRequest("/api/front/next-session", {
        method: "POST",
        body: { world_json: STATE.playSource.world_json }
      });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "次セッションへの移行に失敗しました。");
      }
      applyDisplayPayload(payload.data, "次のセッションへ進みました。");
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  function readConversationPreview() {
    const nodes = Array.from(document.querySelectorAll("[data-message-author-role]"));
    return nodes.slice(-4).map((node) => {
      const role = node.getAttribute("data-message-author-role") || "message";
      const text = (node.textContent || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 320);
      return {
        role,
        text: text || "まだ読み取れる本文がありません。"
      };
    });
  }

  function renderTags(values, tone = "neutral") {
    const rows = (values || []).map((value) => `<span class="src-tag src-tag--${tone}">${escapeHtml(value)}</span>`);
    return rows.length ? rows.join("") : `<span class="src-empty">まだ項目がありません。</span>`;
  }

  function renderConversation() {
    const items = readConversationPreview();
    if (!items.length) {
      return `<div class="src-conversation__empty">ChatGPT の会話はまだ取得できていません。背面の会話はそのまま進められます。</div>`;
    }
    return items
      .map(
        (item) => `
          <article class="src-conversation__item">
            <p class="src-conversation__role">${escapeHtml(item.role === "assistant" ? "GPT" : item.role === "user" ? "あなた" : item.role)}</p>
            <p>${escapeHtml(item.text)}</p>
          </article>
        `
      )
      .join("");
  }

  function drawerContent(display) {
    const actor = display?.actorRail || {};
    switch (STATE.drawer) {
      case "character":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Status</p>
              <h4>身体性</h4>
              <div class="src-kv">
                <div><span>体力</span><strong>${escapeHtml(actor.hp?.current)}/${escapeHtml(actor.hp?.max)}</strong></div>
                <div><span>霊力</span><strong>${escapeHtml(actor.mp?.current)}/${escapeHtml(actor.mp?.max)}</strong></div>
                <div><span>Vessel</span><strong>${escapeHtml(actor.vessel)}</strong></div>
                <div><span>存在級位</span><strong>${escapeHtml(actor.existenceTitle)}</strong></div>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Blessings</p>
              <h4>状態と加護</h4>
              <div class="src-tag-list">${renderTags((actor.statuses || []).map((item) => item.label), "warning")}</div>
              <div class="src-tag-list">${renderTags((actor.blessings || []).map((item) => item.label), "accent")}</div>
            </section>
          </div>
        `;
      case "inventory":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Inventory</p>
              <h4>所持品</h4>
              <p>InventoryRM はまだ未接続です。ここは次段で item / resource / quest item を受ける前提の器です。</p>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Protected</p>
              <h4>守れたものの候補</h4>
              <div class="src-tag-list">${renderTags(display?.nextSessionHook?.protectedAssets || [], "note")}</div>
            </section>
          </div>
        `;
      case "skills":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Vectors</p>
              <h4>技能ベクトル</h4>
              <div class="src-skill-list">
                ${Object.entries(actor.skills || {})
                  .map(([key, value]) => `<div><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`)
                  .join("")}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Quick Skills</p>
              <h4>即応スロット</h4>
              <div class="src-tag-list">${renderTags((actor.quickSlots || []).map((item) => item.label), "slot")}</div>
            </section>
          </div>
        `;
      case "quest":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Node Board</p>
              <h4>${escapeHtml(display?.activeNode?.title || "現在のノード")}</h4>
              <p>${escapeHtml(display?.activeNodeGuide?.summary || display?.currentEvent?.summaryText || "まだ quest 情報がありません。")}</p>
              <div class="src-tag-list">${renderTags((display?.activeNode?.recommendedVectors || []).map(String), "slot")}</div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Branches</p>
              <h4>分岐候補</h4>
              <div class="src-branch-list">
                ${(display?.currentEvent?.branchPreview || [])
                  .slice(0, 3)
                  .map((branch) => `<article><strong>${escapeHtml(branch.label)}</strong><p>${escapeHtml(branch.summaryText)}</p></article>`)
                  .join("") || "<p class='src-empty'>まだ分岐候補がありません。</p>"}
              </div>
            </section>
          </div>
        `;
      case "codex":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Codex</p>
              <h4>焦点人物</h4>
              ${(display?.namedCast || [])
                .slice(0, 4)
                .map((item) => `<article class="src-codex-row"><strong>${escapeHtml(item.displayName)}</strong><p>${escapeHtml(item.conflictText || item.traceText || "記録待ち")}</p></article>`)
                .join("") || "<p class='src-empty'>まだ人物記録がありません。</p>"}
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Relation Graph</p>
              <h4>相関図</h4>
              <p>相関図は常設ではなく Codex / World Hub で開く設計です。現段階では焦点 NPC と active node を優先表示します。</p>
            </section>
          </div>
        `;
      case "journal":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Journal</p>
              <h4>セッションの持ち越し</h4>
              <div class="src-tag-list">${renderTags(display?.nextSessionHook?.carriedPressures || [], "warning")}</div>
              <div class="src-tag-list">${renderTags(display?.nextSessionHook?.npcCarryOvers || [], "accent")}</div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Ending</p>
              <h4>小結末</h4>
              <p>${escapeHtml(display?.sessionEnding?.summary || display?.endingForecast?.summary || "まだ小結末は確定していません。")}</p>
            </section>
          </div>
        `;
      case "world":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">World</p>
              <h4>世界脈動</h4>
              <div class="src-kv">
                <div><span>主神</span><strong>${escapeHtml(display?.worldSpine?.mainGodLabel)}</strong></div>
                <div><span>連鎖</span><strong>${escapeHtml(display?.worldSpine?.activeChainLabel)}</strong></div>
                <div><span>同期</span><strong>${escapeHtml(display?.worldSpine?.syncState)}</strong></div>
                <div><span>分岐</span><strong>${escapeHtml(display?.worldSpine?.dominantBranch)}</strong></div>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Institution</p>
              <h4>制度圧</h4>
              <p>${escapeHtml(display?.institutionAlertGuide?.summary || display?.institutionAlert?.label || "まだ制度圧は薄いです。")}</p>
            </section>
          </div>
        `;
      case "dice":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Dice</p>
              <h4>Dice Tray</h4>
              <p>Dice Tray は次段で event contract と連携します。現段階では choice / free action の結果表示に専念します。</p>
            </section>
          </div>
        `;
      case "assets":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Assets</p>
              <h4>クライマックス画像生成</h4>
              <p>Quest クライマックス時の生成結果はここに集約します。現在は shell 側の器だけ先に用意しています。</p>
              <div class="src-tag-list">${renderTags(["none", "queued", "rendering", "revealed", "canonical"], "note")}</div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Gallery</p>
              <h4>最新状態</h4>
              <p>${escapeHtml(display?.sessionEnding ? "クライマックス画像生成の条件に近づいています。" : "まだクライマックス条件には届いていません。")}</p>
            </section>
          </div>
        `;
      case "settings":
      default:
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">Settings</p>
              <h4>現在の接続先</h4>
              <div class="src-kv">
                <div><span>API</span><strong>${escapeHtml(STATE.settings.apiBaseUrl)}</strong></div>
                <div><span>seed</span><strong>${escapeHtml(STATE.settings.seed)}</strong></div>
                <div><span>seasons</span><strong>${escapeHtml(STATE.settings.seasons)}</strong></div>
                <div><span>archetype</span><strong>${escapeHtml(STATE.settings.archetype)}</strong></div>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">Panel</p>
              <h4>補助パネル</h4>
              <p>詳細設定は拡張の side panel から変更できます。</p>
              <button class="src-inline-button" data-open-sidepanel="true">side panel で開く</button>
            </section>
          </div>
        `;
    }
  }

  function render() {
    const display = STATE.display;
    const playerFacingLines = display?.scenePacket?.playerFacing?.lines || [];
    const focusBeat = display?.npcBeats?.[0] || {};
    const focusCast = (display?.namedCast || []).find((item) => item.npcId === focusBeat.npcId) || {};
    const hotbarItems = [
      ["character", "Character"],
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

    mount.innerHTML = `
      <div class="src-shell-root ${STATE.visible ? "is-open" : "is-collapsed"}">
        <button class="src-launcher" data-launcher="true">${STATE.visible ? "閉じる" : "Star Ring Codex"}</button>
        <section class="src-shell" aria-hidden="${STATE.visible ? "false" : "true"}">
          <header class="src-world-spine">
            <div class="src-brand">
              <p class="src-eyebrow">Chrome Shell</p>
              <h2>Star Ring Codex</h2>
            </div>
            <div class="src-world-kv">
              <span>${escapeHtml(display?.worldSpine?.worldName || "未読込")}</span>
              <span>${escapeHtml(display?.worldSpine?.eraLabel || "時代待ち")}</span>
              <span>${escapeHtml(display?.worldSpine?.calendarName || "暦待ち")} ${escapeHtml(display?.worldSpine?.year || "")}年</span>
              <span>主神 ${escapeHtml(display?.worldSpine?.mainGodLabel || "-")}</span>
              <span>連鎖 ${escapeHtml(display?.worldSpine?.activeChainLabel || "-")}</span>
              <span class="src-sync src-sync--${escapeHtml(STATE.status.tone)}">${escapeHtml(STATE.status.text)}</span>
            </div>
            <div class="src-control-row">
              <button data-refresh="true" ${STATE.pending ? "disabled" : ""}>再読込</button>
              <button data-save="true" ${STATE.pending ? "disabled" : ""}>保存</button>
              <button data-load-save="true" ${STATE.pending ? "disabled" : ""}>読込</button>
              <button data-next-session="true" ${STATE.pending ? "disabled" : ""}>次セッション</button>
            </div>
          </header>

          <div class="src-main-grid">
            <aside class="src-actor-rail">
              <div class="src-panel">
                <p class="src-eyebrow">Actor Rail</p>
                <h3>${escapeHtml(display?.actorRail?.label || "旅人")}</h3>
                <p class="src-subtitle">${escapeHtml(display?.actorRail?.existenceTitle || "存在級位未設定")}</p>
                <div class="src-meter-grid">
                  <div><span>HP</span><strong>${escapeHtml(display?.actorRail?.hp?.current)}/${escapeHtml(display?.actorRail?.hp?.max)}</strong></div>
                  <div><span>MP</span><strong>${escapeHtml(display?.actorRail?.mp?.current)}/${escapeHtml(display?.actorRail?.mp?.max)}</strong></div>
                  <div><span>Vessel</span><strong>${escapeHtml(display?.actorRail?.vessel)}</strong></div>
                </div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">Status</p>
                <div class="src-tag-list">${renderTags((display?.actorRail?.statuses || []).map((item) => item.label), "warning")}</div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">Blessings</p>
                <div class="src-tag-list">${renderTags((display?.actorRail?.blessings || []).map((item) => item.label), "accent")}</div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">Quick Skills</p>
                <div class="src-tag-list">${renderTags((display?.actorRail?.quickSlots || []).map((item) => item.label), "slot")}</div>
              </div>
            </aside>

            <section class="src-narrative-core">
              <div class="src-panel src-panel--hero">
                <p class="src-eyebrow">Narrative Core</p>
                <h3>${escapeHtml(display?.scenePacket?.focusLabel || "現在の場面")}</h3>
                <p class="src-headline">${escapeHtml(display?.scenePacket?.playerFacing?.headline || "場面データを読んでいます。")}</p>
                <p class="src-location">${escapeHtml(display?.scenePacket?.locationLabel || "")}</p>
                <div class="src-scene-lines">
                  ${playerFacingLines.map((line) => `<p>${escapeHtml(line)}</p>`).join("") || "<p class='src-empty'>まだ player-facing の行はありません。</p>"}
                </div>
              </div>

              <div class="src-panel">
                <p class="src-eyebrow">Conversation Lens</p>
                <h3>ChatGPT 会話の現在地</h3>
                <div class="src-conversation">${renderConversation()}</div>
              </div>

              <div class="src-panel">
                <p class="src-eyebrow">Choice Chips</p>
                <div class="src-choice-list">
                  ${(display?.scenePacket?.playerFacing?.choiceChips || [])
                    .map(
                      (choice) => `
                        <button class="src-choice-chip" data-choice-id="${escapeHtml(choice.choiceId)}" ${STATE.pending ? "disabled" : ""}>
                          ${escapeHtml(choice.label)}
                        </button>
                      `
                    )
                    .join("") || "<p class='src-empty'>choice chips はまだありません。</p>"}
                </div>
              </div>

              <div class="src-panel">
                <p class="src-eyebrow">Free Action</p>
                <textarea class="src-free-action" data-free-action-input="true" placeholder="例: 夜中に裏から入り、裏帳面を盗み見たい">${escapeHtml(STATE.freeActionDraft)}</textarea>
                <div class="src-inline-actions">
                  <button data-free-action-submit="true" ${STATE.pending ? "disabled" : ""}>自由行動を送る</button>
                </div>
              </div>
            </section>

            <aside class="src-context-rail">
              <div class="src-panel">
                <p class="src-eyebrow">NPC Focus</p>
                <h3>${escapeHtml(focusBeat.displayName || "焦点人物")}</h3>
                <p>${escapeHtml(focusBeat.relationBeat || focusCast.traceText || "まだ焦点人物の反応は記録されていません。")}</p>
                <p class="src-muted">${escapeHtml(focusCast.conflictText || "")}</p>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">Active Node</p>
                <h3>${escapeHtml(display?.activeNode?.title || "ノード待ち")}</h3>
                <p>${escapeHtml(display?.activeNode?.questTitle || display?.currentEvent?.summaryText || "現在の node 情報を読んでいます。")}</p>
                <div class="src-tag-list">${renderTags((display?.activeNode?.recommendedVectors || []).map((value) => `#${value}`), "slot")}</div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">Institution Risk</p>
                <h3>${escapeHtml(display?.institutionAlert?.label || "該当なし")}</h3>
                <p>${escapeHtml(display?.institutionAlertGuide?.summary || "制度圧はまだ大きくありません。")}</p>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">World Pulse</p>
                <p>${escapeHtml(display?.worldPulseGuide?.summaryText || display?.storyGuide?.worldState || "世界脈動を読んでいます。")}</p>
                <div class="src-tag-list">${renderTags(display?.worldSpine?.topNotes || [], "note")}</div>
              </div>
            </aside>
          </div>

          <footer class="src-hotbar">
            ${hotbarItems
              .map(
                ([key, label]) => `
                  <button class="src-hotbar__button ${STATE.drawer === key ? "is-active" : ""}" data-drawer="${key}">
                    <span>${escapeHtml(label)}</span>
                  </button>
                `
              )
              .join("")}
          </footer>

          <section class="src-drawer">
            ${drawerContent(display)}
          </section>
        </section>
      </div>
    `;

    mount.querySelector("[data-launcher='true']")?.addEventListener("click", async () => {
      STATE.visible = !STATE.visible;
      if (STATE.visible && !STATE.display && !STATE.pending) {
        await loadSnapshot();
        return;
      }
      if (STATE.settings) {
        await chrome.runtime.sendMessage({ type: "shell.apply-settings", settings: { ...STATE.settings, shellVisible: STATE.visible } }).catch(() => null);
      }
      render();
    });

    mount.querySelectorAll("[data-choice-id]").forEach((button) => {
      button.addEventListener("click", () => postChoice(button.getAttribute("data-choice-id")));
    });
    mount.querySelectorAll("[data-drawer]").forEach((button) => {
      button.addEventListener("click", () => {
        STATE.drawer = button.getAttribute("data-drawer");
        render();
      });
    });
    mount.querySelector("[data-free-action-input='true']")?.addEventListener("input", (event) => {
      STATE.freeActionDraft = event.target.value;
    });
    mount.querySelector("[data-free-action-submit='true']")?.addEventListener("click", () => postFreeAction());
    mount.querySelector("[data-refresh='true']")?.addEventListener("click", () => loadSnapshot());
    mount.querySelector("[data-save='true']")?.addEventListener("click", () => saveSession());
    mount.querySelector("[data-load-save='true']")?.addEventListener("click", () => loadSavedSession());
    mount.querySelector("[data-next-session='true']")?.addEventListener("click", () => nextSession());
    mount.querySelector("[data-open-sidepanel='true']")?.addEventListener("click", async () => {
      try {
        await chrome.runtime.sendMessage({ type: "sidepanel.open-active" });
      } catch {
        setStatus("side panel の起動に失敗しました。", "error");
      }
    });
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    (async () => {
      switch (message?.type) {
        case "shell.toggle":
          STATE.visible = !STATE.visible;
          if (STATE.visible && !STATE.display && !STATE.pending) {
            await loadSnapshot();
          } else {
            render();
          }
          return { visible: STATE.visible };
        case "shell.show":
          STATE.visible = true;
          if (!STATE.display && !STATE.pending) {
            await loadSnapshot();
          } else {
            render();
          }
          return { visible: true };
        case "shell.hide":
          STATE.visible = false;
          render();
          return { visible: false };
        case "shell.refresh":
          await loadSnapshot();
          return { refreshed: true };
        case "shell.settings-updated":
          STATE.settings = { ...STATE.settings, ...(message.settings || {}) };
          if (STATE.visible) {
            await loadSnapshot();
          } else {
            render();
          }
          return { applied: true };
        default:
          return { ignored: true };
      }
    })()
      .then((result) => sendResponse(result))
      .catch((error) => sendResponse({ error: error.message }));
    return true;
  });

  async function init() {
    STATE.settings = await runtimeRequest({ type: "shell.get-settings" });
    STATE.visible = Boolean(STATE.settings.shellVisible);
    render();
    if (STATE.visible) {
      await loadSnapshot();
    }
  }

  init().catch((error) => {
    STATE.settings = {
      apiBaseUrl: "https://starringcodextrpg.onrender.com",
      seed: 1729,
      seasons: 10,
      archetype: "balanced",
      worldJson: "",
      shellVisible: false
    };
    setStatus(error.message, "error");
  });
})();
