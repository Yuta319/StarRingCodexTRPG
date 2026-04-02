(function bootstrapStarRingShell() {
  if (window.__starRingCodexShellMounted) {
    return;
  }
  window.__starRingCodexShellMounted = true;
  const SHARED = window.__starRingCodexShared || {};
  const TERM_LABELS = SHARED.TERM_LABELS || {};
  const SKILL_LABELS = SHARED.SKILL_LABELS || {};
  const TENDENCY_LABELS = SHARED.TENDENCY_LABELS || {};
  const ASSET_KIND_LABELS = SHARED.ASSET_KIND_LABELS || {};
  const defaultCharacterDraft = SHARED.defaultCharacterDraft || (() => ({
    name: "",
    race: "human",
    style: "vanguard",
    temperament: "prudence",
    origin: "ford"
  }));
  const creationOptions = SHARED.creationOptions || (() => []);
  const creationOptionLabel = SHARED.creationOptionLabel || (() => null);
  const characterProfileQuery = SHARED.characterProfileQuery || ((draft) => draft);

  const STATE = {
    visible: false,
    pending: false,
    display: null,
    settings: null,
    playSource: { seed: 1729, world_json: null },
    saveRef: { saveId: null, savePath: null },
    drawer: null,
    codexCategory: "people",
    codexFocusNpcId: null,
    start: { step: null, draft: defaultCharacterDraft() },
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


  function presentLabel(value) {
    const raw = String(value ?? "").trim();
    if (!raw) {
      return "";
    }
    const normalized = raw.replace(/《([^》]+)》/g, "（$1）");
    const key = normalized.toLowerCase();
    return TERM_LABELS[key] || normalized;
  }

  function present(value) {
    return escapeHtml(presentLabel(value));
  }

  function shouldOpenCharacterCreation() {
    return !STATE.display && !STATE.playSource.world_json && !STATE.settings?.worldJson;
  }

  function labeledList(values, mapper = (value) => value) {
    return (values || []).map((value) => mapper(value)).filter(Boolean);
  }

  function summarizeSituation(display) {
    const event = display?.currentEvent || {};
    return [
      {
        label: "いま起きていること",
        value: event.summaryText || event.summary || display?.scenePacket?.playerFacing?.headline || "状況を読み込み中です。"
      },
      {
        label: "危険",
        value: event.importanceText || event.stakes || display?.institutionAlertGuide?.consequence || "危険度を読み込み中です。"
      },
      {
        label: "目的",
        value: event.objective || display?.activeNode?.questTitle || display?.storyGuide?.objective || "次の目的を読み込み中です。"
      }
    ];
  }

  function summarizeNpc(item) {
    if (!item) {
      return {
        role: "関係者",
        summary: "人物情報を読み込み中です。",
        conflict: "",
        attitude: ""
      };
    }
    return {
      role: item.roleLabel || item.role || "関係者",
      summary: item.summaryText || item.agenda || item.traceText || "まだ動きが見えていません。",
      conflict: item.conflictText || "",
      attitude: item.attitudeText || item.trustText || item.traceText || ""
    };
  }

  function normalizedLooseText(value) {
    return String(value || "")
      .replace(/[〈〉《》()（）\s・]/g, "")
      .trim();
  }

  function displayNameHasRole(displayName, roleLabel) {
    const name = normalizedLooseText(displayName);
    const role = normalizedLooseText(roleLabel);
    if (!name || !role) {
      return false;
    }
    return name.includes(role);
  }

  function npcMetaLine(item) {
    if (!item) {
      return "関係者";
    }
    const displayName = String(item.displayName || "").trim();
    const roleLabel = String(item.roleLabel || item.role || "").trim();
    const metaParts = [item.locationLabel, item.affiliationLabel].filter(Boolean);
    if (displayNameHasRole(displayName, roleLabel)) {
      return metaParts.join(" / ") || item.function || roleLabel || "関係者";
    }
    return [roleLabel, ...metaParts].filter(Boolean).join(" / ") || "関係者";
  }

  function multilineFromList(values, maxCount = 4) {
    return (values || [])
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .slice(0, maxCount)
      .join("\n");
  }

  function listFromMultiline(value, maxCount = 4) {
    return String(value || "")
      .replace(/\r/g, "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, maxCount);
  }

  function buildGenesisDraft(display) {
    const sessionGuide = display?.sessionOpeningGuide || {};
    const profile = display?.characterProfile || {};
    const equipment = display?.equipmentHub || {};
    const starterBoonSeed = profile?.starterBoonSeed || {};
    return {
      openingHeadline: String(sessionGuide.headline || ""),
      openingLinesText: multilineFromList(sessionGuide.lines || profile.openingLines || [], 4),
      loadoutName: String(equipment.loadoutName || profile.loadoutLabel || ""),
      flavorNotesText: multilineFromList(equipment.flavorNotes || [], 3),
      visibleBoonLabel: String(starterBoonSeed.visibleBoon?.label || ""),
      visibleBoonSummary: String(starterBoonSeed.visibleBoon?.summary || ""),
      dormantGraceLabel: String(starterBoonSeed.dormantGrace?.label || ""),
      dormantGraceSummary: String(starterBoonSeed.dormantGrace?.summary || ""),
      slots: (equipment.slots || []).map((item) => ({
        slotId: String(item.slotId || ""),
        slotLabel: String(item.slotLabel || ""),
        name: String(item.name || ""),
        subtitle: String(item.subtitle || ""),
        flavorText: String(item.flavorText || ""),
        statsText: multilineFromList(item.stats || [], 4)
      }))
    };
  }

  function buildGenesisProposal(draft) {
    const proposal = {};
    const openingHeadline = String(draft?.openingHeadline || "").trim();
    const openingLines = listFromMultiline(draft?.openingLinesText, 4);
    const loadoutName = String(draft?.loadoutName || "").trim();
    const flavorNotes = listFromMultiline(draft?.flavorNotesText, 3);
    if (openingHeadline) {
      proposal.openingHeadline = openingHeadline;
    }
    if (openingLines.length) {
      proposal.openingLines = openingLines;
    }
    if (loadoutName) {
      proposal.loadoutName = loadoutName;
    }
    if (flavorNotes.length) {
      proposal.flavorNotes = flavorNotes;
    }

    const starterLoadout = (draft?.slots || [])
      .map((item) => {
        const slotId = String(item?.slotId || "").trim();
        if (!slotId) {
          return null;
        }
        const entry = { slotId };
        const name = String(item?.name || "").trim();
        const subtitle = String(item?.subtitle || "").trim();
        const flavorText = String(item?.flavorText || "").trim();
        const stats = listFromMultiline(item?.statsText, 4);
        if (name) {
          entry.name = name;
        }
        if (subtitle) {
          entry.subtitle = subtitle;
        }
        if (flavorText) {
          entry.flavorText = flavorText;
        }
        if (stats.length) {
          entry.stats = stats;
        }
        return Object.keys(entry).length > 1 ? entry : null;
      })
      .filter(Boolean);
    if (starterLoadout.length) {
      proposal.starterLoadout = starterLoadout;
    }

    const starterBoonSeed = {};
    const visibleBoonLabel = String(draft?.visibleBoonLabel || "").trim();
    const visibleBoonSummary = String(draft?.visibleBoonSummary || "").trim();
    const dormantGraceLabel = String(draft?.dormantGraceLabel || "").trim();
    const dormantGraceSummary = String(draft?.dormantGraceSummary || "").trim();
    if (visibleBoonLabel) {
      starterBoonSeed.visibleBoon = {
        label: visibleBoonLabel,
        summary: visibleBoonSummary
      };
    }
    if (dormantGraceLabel) {
      starterBoonSeed.dormantGrace = {
        label: dormantGraceLabel,
        summary: dormantGraceSummary
      };
    }
    if (Object.keys(starterBoonSeed).length) {
      proposal.starterBoonSeed = starterBoonSeed;
    }
    const selectedVariantIndex = Number(STATE.start?.selectedOpeningVariant);
    const selectedVariant =
      Number.isInteger(selectedVariantIndex) && selectedVariantIndex >= 0
        ? (STATE.display?.characterProfile?.openingVariants || [])[selectedVariantIndex]
        : null;
    if (selectedVariant?.label && selectedVariant?.summary) {
      proposal.selectedOpeningVariantLabel = String(selectedVariant.label);
      proposal.openingVariants = [
        {
          label: String(selectedVariant.label),
          summary: String(selectedVariant.summary)
        }
      ];
      proposal.openingPromptHint = buildOpeningPromptPreviewText(STATE.display, selectedVariant);
    }
    return proposal;
  }

  function buildOpeningPromptPreviewText(display, selectedVariant = null) {
    const profile = display?.characterProfile || {};
    const genesis = display?.newGameGenesis || {};
    const incident = genesis?.incitingIncident || {};
    const castSeed = (genesis?.castSeed || []).slice(0, 3);
    const variant = selectedVariant || (profile.openingVariants || [])[0] || {};
    const lines = [
      `${profile.name || "主人公"}の導入を 2〜4 文で語る。`,
      variant.label ? `導入の調子は「${variant.label}」。` : "",
      variant.summary ? `核にするニュアンス: ${variant.summary}` : "",
      incident.label ? `最初の火種は「${incident.label}」。` : "",
      incident.summary ? `状況: ${incident.summary}` : "",
      genesis?.hub?.label ? `拠点は ${genesis.hub.label}。` : "",
      genesis?.dungeon?.label ? `坑路は ${genesis.dungeon.label}。` : "",
      castSeed.length
        ? `最初に強く関わるのは ${castSeed.map((item) => `${item.displayName}（${item.roleLabel}）`).join("、")}。`
        : "",
      profile.selectedOpeningVariantLabel ? `選ばれた導入名は ${profile.selectedOpeningVariantLabel}。` : "",
      "意味を先に、雰囲気はその後に置く。truth は増やさず、今ある火種を明確に語る。"
    ].filter(Boolean);
    return lines.join(" ");
  }

  async function copyTextToClipboard(text) {
    const safeText = String(text || "").trim();
    if (!safeText) {
      return false;
    }
    try {
      await navigator.clipboard.writeText(safeText);
      return true;
    } catch (_error) {
      const fallback = document.createElement("textarea");
      fallback.value = safeText;
      fallback.setAttribute("readonly", "true");
      fallback.style.position = "fixed";
      fallback.style.left = "-9999px";
      fallback.style.top = "0";
      document.body.append(fallback);
      fallback.select();
      const copied = document.execCommand("copy");
      fallback.remove();
      return copied;
    }
  }

  function visibleNode(selector) {
    return [...document.querySelectorAll(selector)].find((node) => {
      if (!(node instanceof HTMLElement)) {
        return false;
      }
      const rect = node.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    }) || null;
  }

  function findChatGptComposer() {
    return (
      visibleNode("#prompt-textarea") ||
      visibleNode("textarea[placeholder*='メッセージ']") ||
      visibleNode("textarea[placeholder*='message']") ||
      visibleNode("textarea") ||
      visibleNode("[data-testid='composer-text-input'] [contenteditable='true']") ||
      visibleNode("[contenteditable='true'][data-lexical-editor='true']") ||
      visibleNode("[contenteditable='true'][role='textbox']")
    );
  }

  function fillTextControl(element, text) {
    if (!(element instanceof HTMLElement)) {
      return false;
    }
    element.focus();
    element.scrollIntoView({ block: "center", inline: "nearest" });
    if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
      const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
      descriptor?.set?.call(element, text);
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    if (element.isContentEditable) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(element);
      selection?.removeAllRanges();
      selection?.addRange(range);
      const inserted = document.execCommand("insertText", false, text);
      if (!inserted) {
        element.textContent = text;
      }
      element.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
      return true;
    }
    return false;
  }

  async function sendOpeningPromptToComposer(text) {
    const promptText = String(text || "").trim();
    if (!promptText) {
      throw new Error("導入候補がまだありません。");
    }
    const composer = findChatGptComposer();
    if (!composer) {
      throw new Error("ChatGPT の入力欄が見つかりませんでした。");
    }
    if (!fillTextControl(composer, promptText)) {
      throw new Error("入力欄への反映に失敗しました。");
    }
  }

  function renderGenesisStorySeed(genesis) {
    const incident = genesis?.incitingIncident || {};
    const hub = genesis?.hub || {};
    const dungeon = genesis?.dungeon || {};
    const storyAxes = (genesis?.storyAxes || []).filter(Boolean);
    return `
      <section class="src-card src-card--span-3">
        <p class="src-card__eyebrow">世界の火種</p>
        <h4>${present(incident.label || "今回の火種")}</h4>
        <div class="src-start-seed-meta">
          <div><span>拠点</span><strong>${present(hub.label || "未定")}</strong></div>
          <div><span>坑路</span><strong>${present(dungeon.label || "未定")}</strong></div>
        </div>
        <div class="src-text-list">
          <p>${present(incident.summary || "最初の火種を読み込み中です。")}</p>
          <p>${present(incident.objective || "")}</p>
        </div>
        <div class="src-tag-list">${renderTags(storyAxes, "note")}</div>
      </section>
    `;
  }

  function renderGenesisCastSeed(genesis) {
    const castSeed = genesis?.castSeed || [];
    const preferredFactions = (genesis?.preferredFactions || []).filter(Boolean);
    return `
      <section class="src-card src-card--span-3">
        <p class="src-card__eyebrow">最初の顔ぶれ</p>
        <h4>今回の世界で最初にぶつかる人たち</h4>
        <div class="src-tag-list">${renderTags(preferredFactions, "slot")}</div>
        <div class="src-start-cast-grid">
          ${
            castSeed.length
              ? castSeed
                  .map(
                    (item) => `
                      <article class="src-start-cast-card">
                        <p class="src-card__eyebrow">${present(item.roleLabel || "関係者")}</p>
                        <strong>${present(item.displayName || "？？？")}</strong>
                        <p class="src-muted">${present(item.affiliationLabel || "未所属")}</p>
                        <p>${present(item.agenda || "まだ動きが見えていません。")}</p>
                      </article>
                    `
                  )
                  .join("")
              : "<p class='src-empty'>まだ最初の顔ぶれは固まっていません。</p>"
          }
        </div>
      </section>
    `;
  }

  function applyOpeningVariantToDraft(variant) {
    const currentDraft = STATE.start?.genesisDraft || buildGenesisDraft(STATE.display);
    const lines = [String(variant?.summary || "").trim()].filter(Boolean);
    STATE.start = {
      ...(STATE.start || {}),
      selectedOpeningVariant: Number(variant?.index ?? 0),
      genesisDraft: {
        ...currentDraft,
        openingHeadline: String(variant?.label || "").trim() || currentDraft.openingHeadline,
        openingLinesText: lines.join("\n") || currentDraft.openingLinesText
      }
    };
    render();
  }

  function renderCreationChoices(groupKey, selectedId, attributeName) {
    return creationOptions(groupKey)
      .map(
        (item) => `
          <button type="button" class="src-creation-choice ${selectedId === item.id ? "is-active" : ""}" data-character-choice="${attributeName}" data-character-value="${item.id}">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(item.summary)}</span>
          </button>
        `
      )
      .join("");
  }

  function renderStartOverlay(display) {
    const draft = STATE.start?.draft || defaultCharacterDraft();
    if (STATE.start?.step === "create") {
      const race = creationOptionLabel("races", draft.race);
      const style = creationOptionLabel("styles", draft.style);
      const temperament = creationOptionLabel("temperaments", draft.temperament);
      const origin = creationOptionLabel("origins", draft.origin);
      const loadout = creationOptionLabel("loadouts", draft.loadout);
      const sourceMode = creationOptionLabel("sourceModes", draft.sourceMode);
      const previewName = String(draft.name || "").trim() || "名前はあとで自動で入ります";
      return `
        <section class="src-start-overlay" aria-label="キャラクター作成">
          <div class="src-start-panel">
            <div class="src-start-panel__lead">
              <p class="src-eyebrow">導入</p>
              <h3>新しい旅を始める</h3>
              <p>最初に主人公を組みます。ここで決めた内容が、初回の能力値と導入文へ反映されます。</p>
            </div>
            <div class="src-start-grid">
              <section class="src-card src-card--span-2">
                <p class="src-card__eyebrow">名前</p>
                <h4>呼び名</h4>
                <label class="src-field">
                  <span>主人公の名前</span>
                  <input class="src-text-input" data-character-text="name" type="text" maxlength="24" value="${escapeHtml(draft.name || "")}" placeholder="空欄なら自動で決まります" />
                </label>
              </section>
              <section class="src-card">
                <p class="src-card__eyebrow">組み上がり</p>
                <h4>${escapeHtml(previewName)}</h4>
                <div class="src-tag-list">
                  ${renderTags([race?.label, style?.label, temperament?.label, origin?.label, loadout?.label].filter(Boolean), "note")}
                </div>
                <p class="src-muted">${escapeHtml(sourceMode?.summary || origin?.summary || "")}</p>
              </section>
              <section class="src-card">
                <p class="src-card__eyebrow">恩恵</p>
                <h4>開始時の特権</h4>
                <p class="src-muted">開始時は恩恵1件と潜在恩寵1件まで。強すぎる装備や無制限強化は入りません。</p>
              </section>
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">種族</p>
                <h4>種族を選ぶ</h4>
                <div class="src-creation-grid">
                  ${renderCreationChoices("races", draft.race, "race")}
                </div>
              </section>
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">役回り</p>
                <h4>戦い方を決める</h4>
                <div class="src-creation-grid">
                  ${renderCreationChoices("styles", draft.style, "style")}
                </div>
              </section>
              <section class="src-card">
                <p class="src-card__eyebrow">気質</p>
                <h4>性格の傾き</h4>
                <div class="src-creation-grid src-creation-grid--compact">
                  ${renderCreationChoices("temperaments", draft.temperament, "temperament")}
                </div>
              </section>
              <section class="src-card src-card--span-2">
                <p class="src-card__eyebrow">育ち</p>
                <h4>出自を決める</h4>
                <div class="src-creation-grid src-creation-grid--compact">
                  ${renderCreationChoices("origins", draft.origin, "origin")}
                </div>
              </section>
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">初期装備</p>
                <h4>持ち込みたい型</h4>
                <div class="src-creation-grid">
                  ${renderCreationChoices("loadouts", draft.loadout, "loadout")}
                </div>
              </section>
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">導入の型</p>
                <h4>この世界への入り方</h4>
                <div class="src-creation-grid src-creation-grid--compact">
                  ${renderCreationChoices("sourceModes", draft.sourceMode, "sourceMode")}
                </div>
                <p class="src-muted">あとで参照画像やスクリーンショットを使う前提なら、ここで転生元の要点を決めておくと prompt が安定します。</p>
              </section>
              ${
                draft.sourceMode === "reincarnated"
                  ? `
                    <section class="src-card src-card--span-2">
                      <p class="src-card__eyebrow">転生元</p>
                      <h4>元作品 / 元ゲーム</h4>
                      <label class="src-field">
                        <span>世界やタイトル</span>
                        <input class="src-text-input" data-character-text="sourceTitle" type="text" maxlength="80" value="${escapeHtml(draft.sourceTitle || "")}" placeholder="例: 黒い砂漠 / 自作TRPG / MMOの自キャラ" />
                      </label>
                      <label class="src-field">
                        <span>元キャラクター名</span>
                        <input class="src-text-input" data-character-text="sourceName" type="text" maxlength="80" value="${escapeHtml(draft.sourceName || "")}" placeholder="例: 元の名前や呼び名" />
                      </label>
                    </section>
                    <section class="src-card">
                      <p class="src-card__eyebrow">画風メモ</p>
                      <h4>外見の核</h4>
                      <label class="src-field">
                        <span>顔立ち・髪型・体格・色</span>
                        <textarea class="src-text-input src-text-area" data-character-text="appearanceNotes" rows="6" maxlength="320" placeholder="例: 長い銀髪、眠そうな目、細身、濃紺と金の配色、弓を背負う">${escapeHtml(draft.appearanceNotes || "")}</textarea>
                      </label>
                    </section>
                    <section class="src-card src-card--span-3">
                      <p class="src-card__eyebrow">再解釈</p>
                      <h4>残したい要素</h4>
                      <label class="src-field">
                        <span>この世界でも残したい印象</span>
                        <textarea class="src-text-input src-text-area" data-character-text="reinterpretationNotes" rows="4" maxlength="320" placeholder="例: 元キャラの落ち着いた雰囲気、片目を隠す前髪、白金の装飾、弓使いであることは残したい">${escapeHtml(draft.reinterpretationNotes || "")}</textarea>
                      </label>
                    </section>
                  `
                  : ""
              }
            </div>
            <div class="src-start-panel__actions">
              <button class="src-inline-button" data-start-auto="true" ${STATE.pending ? "disabled" : ""}>おまかせで始める</button>
              <button class="src-choice-chip" data-start-create="true" ${STATE.pending ? "disabled" : ""}>この内容で導入を作る</button>
            </div>
          </div>
        </section>
      `;
    }

    if (STATE.start?.step === "opening" && display) {
      const actor = display.actorRail || {};
      const profile = display?.characterProfile || {};
      const equipment = display?.equipmentHub || {};
      const newGameGenesis = display?.newGameGenesis || {};
      const constraints = profile?.generationConstraints || {};
      const genesisDraft = STATE.start?.genesisDraft || buildGenesisDraft(display);
      const safetyTags = [
        constraints.starterAttackCap ? `攻撃 ${constraints.starterAttackCap}まで` : null,
        constraints.starterDefenseCap ? `防御 ${constraints.starterDefenseCap}まで` : null,
        constraints.starterSupportCap ? `補助 ${constraints.starterSupportCap}まで` : null,
        constraints.visibleBoonCount ? `恩恵 ${constraints.visibleBoonCount}件まで` : null,
        constraints.dormantGraceCount ? `恩寵 ${constraints.dormantGraceCount}件まで` : null,
        constraints.starterLoadoutPieces ? `装備 ${constraints.starterLoadoutPieces}部位まで` : null
      ].filter(Boolean);
      const starterSlots = genesisDraft.slots || [];
      return `
        <section class="src-start-overlay" aria-label="導入確認">
          <div class="src-start-panel src-start-panel--opening">
            <div class="src-start-panel__lead">
              <p class="src-eyebrow">導入</p>
              <h3>${present(display?.sessionOpeningGuide?.headline || "旅の始まり")}</h3>
              <p>主人公の組み上がりと、最初の局面です。問題なければこのまま本編へ入れます。</p>
              ${STATE.start?.appliedGenesis || profile?.genesisApplied ? `<div class="src-tag-list"><span class="src-tag src-tag--accent">仕上げ反映済み</span></div>` : ""}
            </div>
            <div class="src-start-grid">
              <section class="src-card">
                <p class="src-card__eyebrow">主人公</p>
                <h4>${present(actor.label || "旅人")}</h4>
                <p class="src-muted">${present(profile.summaryText || actor.existenceTitle || "")}</p>
                <div class="src-tag-list">
                  ${renderTags([profile.raceLabel, profile.styleLabel, profile.temperamentLabel, profile.originLabel, profile.loadoutLabel].filter(Boolean), "note")}
                </div>
              </section>
              <section class="src-card src-card--span-2">
                <p class="src-card__eyebrow">第1場面</p>
                <h4>${present(display?.currentEvent?.label || display?.scenePacket?.focusLabel || "開始局面")}</h4>
                <div class="src-text-list">
                  ${((display?.sessionOpeningGuide?.lines || []).slice(0, 4)).map((line) => `<p>${present(line)}</p>`).join("")}
                </div>
              </section>
              ${renderGenesisStorySeed(newGameGenesis)}
              ${renderGenesisCastSeed(newGameGenesis)}
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">導入の種</p>
                <h4>Custom GPT が広げられる入り口</h4>
                <div class="src-start-variant-list">
                  ${((profile.openingVariants || []).map((variant, index) => `
                    <button
                      type="button"
                      class="src-start-variant-button ${STATE.start?.selectedOpeningVariant === index ? "is-active" : ""}"
                      data-opening-variant-index="${index}"
                    >
                      <strong>${present(variant.label)}</strong>
                      <p>${present(variant.summary)}</p>
                    </button>
                  `).join("")) || "<p class='src-empty'>まだ導入の種はありません。</p>"}
                </div>
              </section>
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">GPT導入候補</p>
                <h4>選んだ導入から組み立てる語りの指示</h4>
                <p class="src-item-flavor">${present(buildOpeningPromptPreviewText(display, ((profile.openingVariants || [])[STATE.start?.selectedOpeningVariant || 0] || null)))}</p>
                <div class="src-card__actions">
                  <button type="button" class="src-inline-button" data-opening-copy="true">コピー</button>
                  <button type="button" class="src-inline-button" data-opening-to-composer="true">入力欄へ入れる</button>
                </div>
              </section>
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">最初の関係</p>
                <h4>誰と誰が最初にぶつかるか</h4>
                ${renderRelationGraph(display, (display?.namedCast || [])[0] || null)}
              </section>
              <section class="src-card">
                <p class="src-card__eyebrow">恩恵</p>
                <h4>${present(profile?.starterBoonSeed?.visibleBoon?.label || "開始恩恵")}</h4>
                <div class="src-text-list">
                  <p>${present(profile?.starterBoonSeed?.visibleBoon?.summary || "")}</p>
                  <p>${present(profile?.starterBoonSeed?.dormantGrace?.label || "")} ${present(profile?.starterBoonSeed?.dormantGrace?.summary || "")}</p>
                </div>
              </section>
              ${
                profile?.sourceMode === "reincarnated"
                  ? `
                    <section class="src-card src-card--span-3">
                      <p class="src-card__eyebrow">転生元</p>
                      <h4>${present(profile.sourceTitle || profile.sourceName || "別世界の面影")}</h4>
                      <div class="src-text-list">
                        <p>${present(profile.sourceSummary || profile.sourceModeSummary || "")}</p>
                        <p>${present(profile.appearanceNotes || "")}</p>
                        <p>${present(profile.reinterpretationNotes || "")}</p>
                      </div>
                    </section>
                  `
                  : ""
              }
              <section class="src-card src-card--span-3">
                <p class="src-card__eyebrow">仕上げ</p>
                <h4>導入・恩恵・初期装備を整える</h4>
                <p class="src-muted">ここで整えた内容は、開始時の上限を超えない範囲で反映されます。空欄は今の内容を保ちます。</p>
                <div class="src-tag-list">${renderTags(safetyTags, "note")}</div>
                <div class="src-genesis-grid">
                  <label class="src-field src-field--span-2">
                    <span>導入見出し</span>
                    <input class="src-text-input" data-genesis-text="openingHeadline" type="text" maxlength="40" value="${escapeHtml(genesisDraft.openingHeadline || "")}" placeholder="例: 灰の辺境から来た旅人" />
                  </label>
                  <label class="src-field src-field--span-2">
                    <span>導入文</span>
                    <textarea class="src-text-input src-text-area" data-genesis-text="openingLinesText" rows="5" maxlength="640" placeholder="1行ずつ区切ってください">${escapeHtml(genesisDraft.openingLinesText || "")}</textarea>
                  </label>
                  <label class="src-field">
                    <span>旅装名</span>
                    <input class="src-text-input" data-genesis-text="loadoutName" type="text" maxlength="32" value="${escapeHtml(genesisDraft.loadoutName || equipment.loadoutName || "")}" placeholder="例: 灰狩りの旅装" />
                  </label>
                  <label class="src-field src-field--span-2">
                    <span>装備メモ</span>
                    <textarea class="src-text-input src-text-area" data-genesis-text="flavorNotesText" rows="3" maxlength="480" placeholder="開始装備の雰囲気や由来を1行ずつ">${escapeHtml(genesisDraft.flavorNotesText || "")}</textarea>
                  </label>
                  <label class="src-field">
                    <span>見える恩恵</span>
                    <input class="src-text-input" data-genesis-text="visibleBoonLabel" type="text" maxlength="32" value="${escapeHtml(genesisDraft.visibleBoonLabel || "")}" placeholder="例: 白火の導き" />
                  </label>
                  <label class="src-field">
                    <span>見える恩恵の説明</span>
                    <textarea class="src-text-input src-text-area" data-genesis-text="visibleBoonSummary" rows="3" maxlength="180" placeholder="開始時に見える恩恵の説明">${escapeHtml(genesisDraft.visibleBoonSummary || "")}</textarea>
                  </label>
                  <label class="src-field">
                    <span>眠る恩寵</span>
                    <input class="src-text-input" data-genesis-text="dormantGraceLabel" type="text" maxlength="32" value="${escapeHtml(genesisDraft.dormantGraceLabel || "")}" placeholder="例: 灰鏡の祝福" />
                  </label>
                  <label class="src-field">
                    <span>眠る恩寵の説明</span>
                    <textarea class="src-text-input src-text-area" data-genesis-text="dormantGraceSummary" rows="3" maxlength="180" placeholder="まだ眠っている恩寵の説明">${escapeHtml(genesisDraft.dormantGraceSummary || "")}</textarea>
                  </label>
                </div>
                <div class="src-genesis-slot-grid">
                  ${starterSlots
                    .map(
                      (slot) => `
                        <article class="src-slot-edit-card">
                          <p class="src-card__eyebrow">${present(slot.slotLabel || "装備")}</p>
                          <label class="src-field">
                            <span>装備名</span>
                            <input class="src-text-input" data-genesis-slot-id="${escapeHtml(slot.slotId || "")}" data-genesis-slot-field="name" type="text" maxlength="40" value="${escapeHtml(slot.name || "")}" />
                          </label>
                          <label class="src-field">
                            <span>補助名</span>
                            <input class="src-text-input" data-genesis-slot-id="${escapeHtml(slot.slotId || "")}" data-genesis-slot-field="subtitle" type="text" maxlength="32" value="${escapeHtml(slot.subtitle || "")}" />
                          </label>
                          <label class="src-field">
                            <span>説明</span>
                            <textarea class="src-text-input src-text-area src-text-area--compact" data-genesis-slot-id="${escapeHtml(slot.slotId || "")}" data-genesis-slot-field="flavorText" rows="3" maxlength="220">${escapeHtml(slot.flavorText || "")}</textarea>
                          </label>
                          <label class="src-field">
                            <span>補正・特徴</span>
                            <textarea class="src-text-input src-text-area src-text-area--compact" data-genesis-slot-id="${escapeHtml(slot.slotId || "")}" data-genesis-slot-field="statsText" rows="3" maxlength="180" placeholder="1行ずつ区切ってください">${escapeHtml(slot.statsText || "")}</textarea>
                          </label>
                        </article>
                      `
                    )
                    .join("")}
                </div>
              </section>
            </div>
            <div class="src-start-panel__actions">
              <button class="src-inline-button" data-start-reset-genesis="true" ${STATE.pending ? "disabled" : ""}>今の内容に戻す</button>
              <button class="src-inline-button" data-start-edit="true" ${STATE.pending ? "disabled" : ""}>キャラクリに戻る</button>
              <button class="src-inline-button" data-start-finalize="true" ${STATE.pending ? "disabled" : ""}>仕上げを反映する</button>
              <button class="src-choice-chip" data-start-begin="true" ${STATE.pending ? "disabled" : ""}>この導入から始める</button>
            </div>
          </div>
        </section>
      `;
    }

    return "";
  }

  function relationshipRows(display) {
    return (display?.namedCast || [])
      .filter((item) => item.conflictText || item.conflictsWithLabel)
      .slice(0, 4)
      .map((item) => ({
        label: `${item.displayName} - ${item.conflictsWithLabel || "別の関係者"}`,
        detail: item.conflictText || item.traceText || "対立の詳細はまだありません。"
      }));
  }

  function nextSessionNotice(display) {
    const playCycle = display?.playCycle || {};
    const turn = Number(playCycle.turnInSession || 0);
    const maxTurns = Number(playCycle.maxTurns || 6);
    if (turn >= maxTurns) {
      return "次のセッションへ進めます。";
    }
    return `次のセッションへ進めるのは ${maxTurns} 手目の後です。いまは ${turn} / ${maxTurns} 手目です。`;
  }

  function metricRows(record, order = [], labels = {}) {
    const source = record || {};
    const seen = new Set();
    const rows = [];
    for (const key of order) {
      if (source[key] === undefined || source[key] === null) {
        continue;
      }
      seen.add(key);
      rows.push({ label: labels[key] || presentLabel(key), value: source[key] });
    }
    for (const [key, value] of Object.entries(source)) {
      if (seen.has(key) || value === undefined || value === null) {
        continue;
      }
      rows.push({ label: labels[key] || presentLabel(key), value });
    }
    return rows;
  }

  function assetKindLabel(kind) {
    const raw = String(kind || "").trim();
    if (!raw) {
      return "画像候補";
    }
    return ASSET_KIND_LABELS[raw] || presentLabel(raw.replaceAll("_", " "));
  }

  function uniqueStrings(values) {
    return [...new Set((values || []).map((value) => String(value || "").trim()).filter(Boolean))];
  }

  function codexPlaceRows(display) {
    const worldSpine = display?.worldSpine || {};
    const rows = [];
    const push = (label, detail) => {
      const cleanedLabel = String(label || "").trim();
      const cleanedDetail = String(detail || "").trim();
      if (!cleanedLabel) {
        return;
      }
      if (rows.some((row) => row.label === cleanedLabel)) {
        return;
      }
      rows.push({ label: cleanedLabel, detail: cleanedDetail });
    };

    push(display?.scenePacket?.locationLabel, "いま場面の中心になっている場所。");
    push(display?.activeNode?.title, display?.activeNode?.questTitle || "いま追っている局面。");
    push(display?.institutionAlert?.label, display?.institutionAlertGuide?.summary || "いま揺らいでいる取り決め。");
    push(worldSpine.worldName, `${worldSpine.eraLabel || "時代"} / ${worldSpine.calendarName || "暦"} ${worldSpine.year || ""}年`);

    (worldSpine.topNotes || []).forEach((note) => {
      const raw = String(note || "").trim();
      if (!raw) {
        return;
      }
      const matched = raw.match(/^(.+?)[：:]\s*(.+)$/);
      if (matched) {
        push(matched[1], matched[2]);
      } else {
        push(raw, "この局面で前面に出ている語。");
      }
    });

    return rows;
  }

  function knowledgeCategories(display) {
    const namedCast = display?.namedCast || [];
    const relics = display?.equipmentHub?.relics || [];
    const spells = display?.equipmentHub?.attunedSpells || [];
    const places = codexPlaceRows(display);
    const eventCount = uniqueStrings([
      display?.currentEvent?.label,
      display?.activeNode?.title,
      display?.institutionAlert?.label
    ]).length;
    return [
      {
        label: "人物",
        known: namedCast.length,
        total: Math.max(namedCast.length + 3, 8),
        note: namedCast[0]?.displayName ? `${namedCast[0].displayName} まで記録済み` : "まだ人物知識はありません。"
      },
      {
        label: "場所",
        known: places.length,
        total: Math.max(places.length + 2, 6),
        note: places[0]?.label ? `${places[0].label} が開いています` : "まだ場所知識はありません。"
      },
      {
        label: "遺物",
        known: relics.length,
        total: Math.max(relics.length + 2, 4),
        note: relics[0]?.name ? `${relics[0].name} を確認済み` : "まだ遺物は見つかっていません。"
      },
      {
        label: "魔法",
        known: spells.length,
        total: Math.max(spells.length + 2, 6),
        note: spells[0]?.name ? `${spells[0].name} を記録済み` : "まだ記憶魔法はありません。"
      },
      {
        label: "局面",
        known: eventCount,
        total: Math.max(eventCount + 2, 5),
        note: display?.currentEvent?.label || "まだ局面知識はありません。"
      }
    ];
  }

  function groupPeopleByAffiliation(people) {
    const groups = new Map();
    for (const item of people || []) {
      const key = String(item?.affiliationLabel || "未所属").trim() || "未所属";
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push(item);
    }
    return [...groups.entries()]
      .map(([label, members]) => ({ label, members }))
      .sort((left, right) => {
        if (right.members.length !== left.members.length) {
          return right.members.length - left.members.length;
        }
        return left.label.localeCompare(right.label, "ja");
      });
  }

  function relationTypeBetween(focusCast, item) {
    if (!focusCast || !item || focusCast.npcId === item.npcId) {
      return null;
    }
    const outbound = focusCast.conflictsWithNpcId === item.npcId;
    const inbound = item.conflictsWithNpcId === focusCast.npcId;
    const trust = Number(item.trust || 0);
    const stress = Number(item.stress || 0);
    if (focusCast.conflictsWithNpcId === item.npcId || item.conflictsWithNpcId === focusCast.npcId) {
      return {
        tone: "conflict",
        label: "対立",
        symbol: "⚔",
        color: "#c76d5b",
        direction: outbound && inbound ? "both" : outbound ? "out" : inbound ? "in" : "none",
        width: 2.6 + Math.min(Math.max(stress - 50, 0), 15) * 0.08
      };
    }
    if (trust >= 62 && stress <= 52) {
      return {
        tone: "ally",
        label: "信頼",
        symbol: "♡",
        color: "#7da98d",
        direction: "both",
        width: 2.4 + Math.min(Math.max(trust - 60, 0), 15) * 0.06
      };
    }
    if (trust >= 56 && stress <= 56) {
      return {
        tone: "ally",
        label: "協力余地",
        symbol: "✦",
        color: "#7da98d",
        direction: "both",
        width: 2.3 + Math.min(Math.max(trust - 55, 0), 12) * 0.05
      };
    }
    if (stress >= 60) {
      return {
        tone: "tense",
        label: "緊張",
        symbol: "⚠",
        color: "#c9935f",
        direction: "none",
        width: 2.1 + Math.min(Math.max(stress - 58, 0), 14) * 0.05
      };
    }
    return {
      tone: "watch",
      label: "警戒",
      symbol: "◇",
      color: "#7f8fa8",
      direction: "none",
      width: 2
    };
  }

  function relationNodeMarks(node) {
    const marks = [];
    if (node.isFocus) {
      marks.push({ label: "焦点", tone: "focus" });
    }
    if (Number(node.stress || 0) >= 60) {
      marks.push({ label: "緊張", tone: "tense" });
    }
    if (Number(node.trust || 0) >= 60) {
      marks.push({ label: "信", tone: "ally" });
    }
    if (String(node.secretState || "") === "hidden") {
      marks.push({ label: "秘", tone: "secret" });
    }
    return marks.slice(0, 2);
  }

  function relationGraphModel(display, focusCast) {
    const namedCast = (display?.namedCast || []).slice(0, 7);
    const focus = focusCast || namedCast[0];
    if (!focus) {
      return null;
    }
    const width = 640;
    const height = 360;
    const centerX = 320;
    const centerY = 170;
    const radius = 120;
    const orbit = namedCast.filter((item) => item.npcId !== focus.npcId);
    const nodes = [
      {
        ...focus,
        x: centerX,
        y: centerY,
        relation: null,
        isFocus: true
      }
    ];

    orbit.forEach((item, index) => {
      const angle = (-Math.PI / 2) + (2 * Math.PI * index) / Math.max(orbit.length, 1);
      nodes.push({
        ...item,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        relation: relationTypeBetween(focus, item),
        isFocus: false
      });
    });

    const edges = nodes
      .filter((item) => !item.isFocus && item.relation)
      .map((item) => {
        const startX = centerX;
        const startY = centerY;
        const endX = item.x;
        const endY = item.y;
        return {
          ...item.relation,
          startX,
          startY,
          endX,
          endY,
          midX: (startX + endX) / 2,
          midY: (startY + endY) / 2,
          trust: Number(item.trust || 0),
          stress: Number(item.stress || 0)
        };
      });

    return { width, height, nodes, edges };
  }

  function renderRelationGraph(display, focusCast) {
    const graph = relationGraphModel(display, focusCast);
    if (!graph) {
      return "<p class='src-empty'>まだ人物関係は見えていません。</p>";
    }
    return `
      <div class="src-relation-graph">
        <svg class="src-relation-graph__svg" viewBox="0 0 ${graph.width} ${graph.height}" aria-hidden="true">
          ${graph.edges
            .map(
              (edge) => `
                <line
                  x1="${edge.startX}"
                  y1="${edge.startY}"
                  x2="${edge.endX}"
                  y2="${edge.endY}"
                  stroke="${edge.color}"
                  stroke-width="${edge.width || 2.2}"
                  stroke-dasharray="${edge.tone === "watch" ? "6 5" : edge.tone === "tense" ? "3 4" : "none"}"
                  opacity="0.92"
                  marker-end="${edge.direction === "out" || edge.direction === "both" ? "url(#src-arrow-end)" : ""}"
                  marker-start="${edge.direction === "in" || edge.direction === "both" ? "url(#src-arrow-start)" : ""}"
                />
                <g transform="translate(${edge.midX}, ${edge.midY})">
                  <rect x="-34" y="-11" width="68" height="22" rx="11" fill="rgba(18, 14, 11, 0.88)" stroke="${edge.color}" stroke-width="1" />
                  <text class="src-relation-graph__edge-label" text-anchor="middle" dominant-baseline="central" fill="${edge.color}">${escapeHtml(edge.label)}</text>
                </g>
              `
            )
            .join("")}
          <defs>
            <marker id="src-arrow-end" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(223, 187, 130, 0.78)" />
            </marker>
            <marker id="src-arrow-start" viewBox="0 0 10 10" refX="1.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 10 0 L 0 5 L 10 10 z" fill="rgba(223, 187, 130, 0.78)" />
            </marker>
          </defs>
        </svg>
        <div class="src-relation-graph__nodes">
          ${graph.nodes
            .map(
              (node) => {
                const marks = relationNodeMarks(node);
                return `
                <button
                  type="button"
                  class="src-relation-node src-relation-node--interactive ${node.isFocus ? "is-focus" : ""}"
                  style="left:${Math.round(node.x)}px; top:${Math.round(node.y)}px;"
                  data-codex-focus-npc="${escapeHtml(node.npcId || "")}"
                >
                  <div class="src-relation-node__head">
                    <span class="src-relation-node__symbol">${escapeHtml(node.relation?.symbol || "●")}</span>
                    <div class="src-relation-node__marks">
                      ${marks.map((mark) => `<span class="src-relation-node__mark is-${mark.tone}">${escapeHtml(mark.label)}</span>`).join("")}
                    </div>
                  </div>
                        <strong>${present(node.displayName || "???")}</strong>
                        <p>${present(npcMetaLine(node))}</p>
                      </button>
              `;
              }
            )
            .join("")}
        </div>
        <div class="src-relation-legend">
          <span><i class="src-relation-legend__line is-conflict"></i>対立</span>
          <span><i class="src-relation-legend__line is-ally"></i>協力余地 / 信頼</span>
          <span><i class="src-relation-legend__line is-watch"></i>警戒</span>
          <span><i class="src-relation-legend__line is-tense"></i>緊張</span>
          <span><i class="src-relation-legend__mark is-secret"></i>秘 = 隠し事</span>
        </div>
      </div>
    `;
  }

  function assetUrl(filename) {
    if (!filename) {
      return null;
    }
    return chrome.runtime.getURL(`assets/icons/${filename}`);
  }

  function renderIconTile({ filename, fallback, alt, small = false, featured = false }) {
    const classes = [
      "src-icon-tile",
      small ? "src-icon-tile--small" : "",
      featured ? "src-icon-tile--featured" : ""
    ]
      .filter(Boolean)
      .join(" ");
    const src = assetUrl(filename);
    if (!src) {
      return `<div class="${classes}">${escapeHtml(fallback || "?")}</div>`;
    }
    return `
      <div class="${classes}" data-fallback="${escapeHtml(fallback || "?")}">
        <img src="${src}" alt="" loading="lazy" />
      </div>
    `;
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

  async function persistShellSnapshot() {
    await chrome.storage.local.set({
      shellSnapshotCache: {
        display: STATE.display,
        playSource: STATE.playSource,
        saveRef: STATE.saveRef,
        settings: STATE.settings,
        status: STATE.status,
        updatedAt: new Date().toISOString()
      }
    });
  }

  function describeSource(payload) {
    if (payload?.request?.character_profile) {
      return "主人公を組み上げて場面を開きました。";
    }
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
    if (
      STATE.codexFocusNpcId &&
      !(STATE.display?.namedCast || []).some((item) => item.npcId === STATE.codexFocusNpcId)
    ) {
      STATE.codexFocusNpcId = null;
    }
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
    if (STATE.start?.step === "opening" && !STATE.start?.genesisDraft && STATE.display) {
      STATE.start = {
        ...(STATE.start || {}),
        genesisDraft: buildGenesisDraft(STATE.display),
        appliedGenesis: Boolean(payload.appliedGenesis || STATE.display?.characterProfile?.genesisApplied)
      };
    }
    setStatus(successText || describeSource(payload), "ok");
    persistShellSnapshot().catch(() => null);
  }

  async function loadSnapshot(options = {}) {
    if (
      !options.characterProfile &&
      !options.skipCharacterCreation &&
      shouldOpenCharacterCreation()
    ) {
      STATE.start = { ...(STATE.start || {}), step: "create", draft: STATE.start?.draft || defaultCharacterDraft() };
      setStatus("まず主人公を組みます。", "idle");
      render();
      return;
    }
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
      if (!query.world_json && options.characterProfile) {
        Object.assign(query, characterProfileQuery(options.characterProfile));
      }
      const payload = await apiRequest("/api/front/snapshot", { query });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "front snapshot の取得に失敗しました。");
      }
      applyDisplayPayload(payload.data, describeSource(payload.data));
      if (options.characterProfile) {
        STATE.start = {
          ...(STATE.start || {}),
          step: "opening",
          draft: { ...options.characterProfile },
          genesisDraft: buildGenesisDraft(payload.data?.display || STATE.display),
          selectedOpeningVariant: null,
          appliedGenesis: Boolean(payload.data?.appliedGenesis)
        };
      }
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      STATE.pending = false;
      render();
    }
  }

  async function createCharacterAndLoad() {
    const draft = { ...(STATE.start?.draft || defaultCharacterDraft()) };
    await loadSnapshot({ characterProfile: draft });
  }

  async function finalizeCharacterGenesis() {
    if (!STATE.playSource.world_json) {
      setStatus("仕上げを反映するには開始済みの world_json が必要です。", "error");
      return;
    }
    const genesisDraft = STATE.start?.genesisDraft || buildGenesisDraft(STATE.display);
    const proposal = buildGenesisProposal(genesisDraft);
    STATE.pending = true;
    render();
    setStatus("導入と初期装備を仕上げています。", "loading");
    try {
      const payload = await apiRequest("/api/front/finalize-character", {
        method: "POST",
        body: {
          world_json: STATE.playSource.world_json,
          proposal
        }
      });
      if (!payload.ok) {
        throw new Error(payload.data?.error || "キャラクター仕上げの反映に失敗しました。");
      }
      applyDisplayPayload(payload.data, "導入と初期装備を仕上げました。");
      STATE.start = {
        ...(STATE.start || {}),
        step: "opening",
        genesisDraft: buildGenesisDraft(payload.data?.display || STATE.display),
        appliedGenesis: true
      };
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

  function renderTags(values, tone = "neutral") {
    const rows = (values || []).map((value) => `<span class="src-tag src-tag--${tone}">${present(value)}</span>`);
    return rows.length ? rows.join("") : `<span class="src-empty">まだ項目がありません。</span>`;
  }

  function drawerContent(display) {
    const actor = display?.actorRail || {};
    const equipment = display?.equipmentHub || {};
    const inventory = display?.inventoryHub || {};
    const assetPromptPack = display?.assetPromptPack || {};
    const skillRows = metricRows(
      actor.skills,
      ["combat", "diplomacy", "ritual", "stealth", "stewardship", "authority"],
      SKILL_LABELS
    );
    const tendencyRows = metricRows(actor.tendencies, ["mercy", "prudence", "ambition", "zeal"], TENDENCY_LABELS);
    const assetEntries = assetPromptPack.entries || [];
    const iconEntries = assetEntries.filter((entry) => String(entry.kind || "").endsWith("_icon"));
    const artEntries = assetEntries.filter((entry) => !String(entry.kind || "").endsWith("_icon"));
    const carryTags = [
      ...(display?.nextSessionHook?.carriedPressures || []),
      ...(display?.nextSessionHook?.scarsRemaining || []),
      ...(display?.nextSessionHook?.protectedAssets || [])
    ].filter(Boolean);
    const assetStateRows = Object.entries(
      assetEntries.reduce((counts, entry) => {
        const key = String(entry.assetState || "queued");
        counts[key] = (counts[key] || 0) + 1;
        return counts;
      }, {})
    ).map(([state, count]) => `${presentLabel(state)} ${count}`);
    const codexCategory = STATE.codexCategory || "people";
    switch (STATE.drawer) {
      case "character":
        const featured = equipment.featuredItem || {};
        const characterProfile = display?.characterProfile || {};
        return `
          <div class="src-drawer-grid src-drawer-grid--character">
            <section class="src-card">
              <p class="src-card__eyebrow">来歴</p>
              <h4>${present(actor.label || "旅人")}</h4>
              <p class="src-item-flavor">${present(characterProfile.summaryText || actor.existenceTitle || "来歴の記録を読み込み中です。")}</p>
              <div class="src-tag-list">
                ${renderTags(
                  [
                    characterProfile.raceLabel,
                    characterProfile.styleLabel,
                    characterProfile.temperamentLabel,
                    characterProfile.originLabel,
                    characterProfile.loadoutLabel,
                    characterProfile.sourceMode === "reincarnated" ? characterProfile.sourceModeLabel : null
                  ].filter(Boolean),
                  "note"
                )}
              </div>
              <div class="src-text-list">
                ${((characterProfile.openingLines || []).slice(0, 4)).map((line) => `<p>${present(line)}</p>`).join("")}
                ${characterProfile.appearanceNotes ? `<p>${present(characterProfile.appearanceNotes)}</p>` : ""}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">恩恵 / 恩寵</p>
              <h4>${present(characterProfile?.starterBoonSeed?.visibleBoon?.label || "開始恩恵")}</h4>
              <div class="src-text-list">
                <p>${present(characterProfile?.starterBoonSeed?.visibleBoon?.summary || "開始時の恩恵はまだありません。")}</p>
                <p>${present(characterProfile?.starterBoonSeed?.dormantGrace?.label || "")}</p>
                <p>${present(characterProfile?.starterBoonSeed?.dormantGrace?.summary || "")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">装備</p>
              <h4>${present(equipment.loadoutName || "旅装")}</h4>
              <div class="src-equip-load">
                <span>装備負荷</span>
                <strong>${present(equipment.equipLoad?.current)}/${present(equipment.equipLoad?.max)}</strong>
                <em>${present(equipment.equipLoad?.state || "標準")}</em>
              </div>
              <div class="src-equip-grid">
                ${(equipment.slots || [])
                  .map(
                    (item) => `
                      <article class="src-equip-slot ${featured.itemId === item.itemId ? "is-featured" : ""}">
                        ${renderIconTile({
                          filename: item.iconFilename || (item.iconKey ? `${item.iconKey}.png` : null),
                          fallback: (item.slotLabel || "?").slice(0, 1),
                          alt: item.name
                        })}
                        <div class="src-equip-slot__body">
                          <p class="src-equip-slot__label">${present(item.slotLabel)}</p>
                          <strong>${present(item.name)}</strong>
                          <p>${present(item.subtitle)}</p>
                          <div class="src-item-meta">
                            <span>${present(item.rarityLabel || item.rarity || "")}</span>
                            <span>${present(item.assetState || "queued")}</span>
                          </div>
                        </div>
                      </article>
                    `
                  )
                  .join("")}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">注目装備</p>
              <div class="src-featured-head">
                ${renderIconTile({
                  filename: featured.iconFilename || (featured.iconKey ? `${featured.iconKey}.png` : null),
                  fallback: "装",
                  alt: featured.name,
                  featured: true
                })}
                <div>
                  <h4>${present(featured.name || "装備詳細")}</h4>
                  <p class="src-item-subtitle">${present(featured.subtitle || "")}</p>
                </div>
              </div>
              <div class="src-item-meta">
                <span>${present(featured.rarityLabel || featured.rarity || "")}</span>
                <span>${present(featured.assetState || "queued")}</span>
              </div>
              <div class="src-tag-list">${renderTags(featured.stats || [], "slot")}</div>
              <p class="src-item-flavor">${present(featured.flavorText || "装備の記録はまだありません。")}</p>
              <div class="src-kv">
                <div><span>体力</span><strong>${present(actor.hp?.current)}/${present(actor.hp?.max)}</strong></div>
                <div><span>霊力</span><strong>${present(actor.mp?.current)}/${present(actor.mp?.max)}</strong></div>
                <div><span>Vessel</span><strong>${present(actor.vessel)}</strong></div>
                <div><span>存在級位</span><strong>${present(actor.existenceTitle)}</strong></div>
              </div>
              <div class="src-text-list">
                ${(equipment.flavorNotes || []).map((line) => `<p>${present(line)}</p>`).join("")}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">立ち絵</p>
              <h4>人物画の方針</h4>
              <div class="src-text-list">
                <p>${present(display?.assetPromptPack?.portraitGuide?.styleSummary || "主人公の立ち絵と顔アイコンは、ゲーム全体と同じ画風へ揃えます。")}</p>
                <p>${present(characterProfile.sourceMode === "reincarnated" ? (characterProfile.sourceSummary || "元の姿の面影を保ちながら、この世界の意匠へ置き換えます。") : "この世界の旅人として、装備と出自に沿った姿で描きます。")}</p>
                <p>${present(characterProfile.reinterpretationNotes || characterProfile.appearanceNotes || "")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">遺物</p>
              <h4>遺物スロット</h4>
              <div class="src-mini-card-list">
                ${(equipment.relics || [])
                  .map(
                    (item) => `
                      <article class="src-mini-card">
                        ${renderIconTile({
                          filename: item.iconFilename || (item.iconKey ? `${item.iconKey}.png` : null),
                          fallback: "R",
                          alt: item.name,
                          small: true
                        })}
                        <div>
                          <strong>${present(item.name)}</strong>
                          <div class="src-item-meta">
                            <span>${present(item.rarityLabel || item.rarity || "")}</span>
                            <span>${present(item.assetState || "queued")}</span>
                          </div>
                          <p>${present(item.flavorText)}</p>
                        </div>
                      </article>
                    `
                  )
                  .join("") || "<p class='src-empty'>まだ遺物がありません。</p>"}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">魔法</p>
              <h4>記憶魔法</h4>
              <div class="src-mini-card-list">
                ${(equipment.attunedSpells || [])
                  .map(
                    (spell) => `
                      <article class="src-mini-card">
                        ${renderIconTile({
                          filename: spell.iconFilename || (spell.iconKey ? `${spell.iconKey}.png` : null),
                          fallback: "M",
                          alt: spell.name,
                          small: true
                        })}
                        <div>
                          <strong>${present(spell.name)}</strong>
                          <div class="src-item-meta">
                            <span>${present(spell.attribute)}</span>
                            <span>${present(spell.assetState || "queued")}</span>
                          </div>
                          <p>${present(spell.attribute)} / ${present(spell.rank)} / MP ${present(spell.mpCost)}</p>
                          <p>${present(spell.description)}</p>
                        </div>
                      </article>
                    `
                  )
                  .join("") || "<p class='src-empty'>まだ記憶魔法がありません。</p>"}
              </div>
            </section>
          </div>
        `;
      case "inventory":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">所持品</p>
              <h4>所持品</h4>
              <div class="src-kv">
                <div><span>携行数</span><strong>${present(inventory.capacity?.used)}/${present(inventory.capacity?.max)}</strong></div>
                <div><span>即使用</span><strong>${present((inventory.quickUse || []).length)}</strong></div>
              </div>
              <div class="src-inventory-groups">
                ${(inventory.groups || [])
                  .map(
                    (group) => `
                      <section class="src-inventory-group">
                        <h5>${present(group.label)}</h5>
                        ${(group.items || [])
                          .map(
                            (item) => `
                              <article class="src-mini-card">
                                ${renderIconTile({
                                  filename: item.iconFilename || (item.iconKey ? `${item.iconKey}.png` : null),
                                  fallback: (item.category || "?").slice(0, 1).toUpperCase(),
                                  alt: item.name,
                                  small: true
                                })}
                                <div>
                                  <strong>${present(item.name)} ×${present(item.quantity)}</strong>
                                  <div class="src-item-meta">
                                    <span>${present(item.category)}</span>
                                    <span>${present(item.assetState || "queued")}</span>
                                  </div>
                                  <p>${present(item.description)}</p>
                                </div>
                              </article>
                            `
                          )
                          .join("")}
                      </section>
                    `
                  )
                  .join("") || "<p class='src-empty'>まだ所持品がありません。</p>"}
              </div>
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
              <p class="src-card__eyebrow">技能</p>
              <h4>技能ベクトル</h4>
              <div class="src-skill-list">
                ${skillRows
                  .map((row) => `<div><span>${present(row.label)}</span><strong>${present(row.value)}</strong></div>`)
                  .join("")}
              </div>
              <div class="src-text-list">
                <p>${present(display?.activeNodeGuide?.action || "この局面で向いている技能を整理します。")}</p>
                <p>${present(display?.storyGuide?.objective || "いまの目的に合わせて技能を選びます。")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">気質</p>
              <h4>判断の傾き</h4>
              <div class="src-skill-list">
                ${tendencyRows
                  .map((row) => `<div><span>${present(row.label)}</span><strong>${present(row.value)}</strong></div>`)
                  .join("") || "<p class='src-empty'>まだ気質は読めていません。</p>"}
              </div>
              <div class="src-text-list">
                <p>${present(display?.storyGuide?.trace || "最近の選び方はまだまとまっていません。")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">状態</p>
              <h4>いま効いているもの</h4>
              <div class="src-text-list">
                <div>
                  <strong>状態</strong>
                  <div class="src-tag-list">${renderTags(labeledList(actor.statuses || [], (item) => presentLabel(item.label)), "warning")}</div>
                </div>
                <div>
                  <strong>加護</strong>
                  <div class="src-tag-list">${renderTags(labeledList(actor.blessings || [], (item) => presentLabel(item.label)), "accent")}</div>
                </div>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">即応</p>
              <h4>よく使う行動と記憶魔法</h4>
              <div class="src-tag-list">${renderTags(labeledList(actor.quickSlots || [], (item) => presentLabel(item.label)), "slot")}</div>
              <div class="src-mini-card-list">
                ${(equipment.attunedSpells || [])
                  .slice(0, 4)
                  .map(
                    (spell) => `
                      <article class="src-mini-card">
                        ${renderIconTile({
                          filename: spell.iconFilename || (spell.iconKey ? `${spell.iconKey}.png` : null),
                          fallback: "M",
                          alt: spell.name,
                          small: true
                        })}
                        <div>
                          <strong>${present(spell.name)}</strong>
                          <div class="src-item-meta">
                            <span>${present(spell.attribute)}</span>
                            <span>MP ${present(spell.mpCost)}</span>
                          </div>
                          <p>${present(spell.description)}</p>
                        </div>
                      </article>
                    `
                  )
                  .join("") || "<p class='src-empty'>まだ記憶魔法はありません。</p>"}
              </div>
            </section>
          </div>
        `;
      case "quest":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">局面</p>
              <h4>${present(display?.activeNode?.title || "この局面")}</h4>
              <p>${present(display?.activeNodeGuide?.summary || display?.currentEvent?.summaryText || "まだ局面情報がありません。")}</p>
              <div class="src-tag-list">${renderTags(labeledList(display?.activeNode?.recommendedVectors || [], (value) => presentLabel(value)), "slot")}</div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">打ち手</p>
              <h4>打ち手の候補</h4>
              <div class="src-branch-list">
                ${(display?.currentEvent?.branchPreview || [])
                  .slice(0, 3)
                  .map((branch) => `<article><strong>${present(branch.label)}</strong><p>${present(branch.summaryText)}</p></article>`)
                  .join("") || "<p class='src-empty'>まだ打ち手の候補がありません。</p>"}
              </div>
            </section>
          </div>
        `;
      case "codex":
        const relationRows = relationshipRows(display);
        const focusBeat = display?.npcBeats?.[0] || {};
        const focusCast =
          (display?.namedCast || []).find((item) => item.npcId === STATE.codexFocusNpcId) ||
          (display?.namedCast || []).find((item) => item.npcId === focusBeat.npcId) ||
          (display?.namedCast || [])[0] ||
          {};
        const focusNpc = summarizeNpc(focusCast);
        const categoryRows = knowledgeCategories(display);
        const knownPeople = display?.namedCast || [];
        const peopleGroups = groupPeopleByAffiliation(knownPeople);
        const hiddenPeopleCount = Math.max(0, Math.min(4, (categoryRows.find((row) => row.label === "人物")?.total || 0) - knownPeople.length));
        const placeRows = codexPlaceRows(display);
        const codexTabs = [
          ["people", "人物"],
          ["places", "場所"],
          ["relics", "遺物"],
          ["spells", "魔法"],
          ["events", "局面"]
        ];
        const codexBody =
          codexCategory === "places"
            ? `
                <section class="src-card">
                  <p class="src-card__eyebrow">場所知識</p>
                  <h4>いま見えている固有名</h4>
                  <div class="src-mini-card-list">
                    ${placeRows
                      .slice(0, 8)
                      .map(
                        (row) => `
                          <article class="src-mini-card">
                            ${renderIconTile({
                              filename: null,
                              fallback: (row.label || "?").slice(0, 1),
                              alt: row.label,
                              small: true
                            })}
                            <div>
                              <strong>${present(row.label)}</strong>
                              <p>${present(row.detail)}</p>
                            </div>
                          </article>
                        `
                      )
                      .join("") || "<p class='src-empty'>まだ場所知識はありません。</p>"}
                  </div>
                </section>
              `
            : codexCategory === "relics"
              ? `
                  <section class="src-card">
                    <p class="src-card__eyebrow">遺物知識</p>
                    <h4>見つかった遺物</h4>
                    <div class="src-mini-card-list">
                      ${(equipment.relics || [])
                        .map(
                          (item) => `
                            <article class="src-mini-card">
                              ${renderIconTile({
                                filename: item.iconFilename || (item.iconKey ? `${item.iconKey}.png` : null),
                                fallback: "遺",
                                alt: item.name,
                                small: true
                              })}
                              <div>
                                <strong>${present(item.name)}</strong>
                                <div class="src-item-meta">
                                  <span>${present(item.rarityLabel || item.rarity || "")}</span>
                                  <span>${present(item.assetState || "queued")}</span>
                                </div>
                                <p>${present(item.flavorText)}</p>
                              </div>
                            </article>
                          `
                        )
                        .join("") || "<p class='src-empty'>まだ遺物は見つかっていません。</p>"}
                    </div>
                  </section>
                `
              : codexCategory === "spells"
                ? `
                    <section class="src-card">
                      <p class="src-card__eyebrow">魔法知識</p>
                      <h4>記録済みの魔法</h4>
                      <div class="src-mini-card-list">
                        ${(equipment.attunedSpells || [])
                          .map(
                            (spell) => `
                              <article class="src-mini-card">
                                ${renderIconTile({
                                  filename: spell.iconFilename || (spell.iconKey ? `${spell.iconKey}.png` : null),
                                  fallback: "魔",
                                  alt: spell.name,
                                  small: true
                                })}
                                <div>
                                  <strong>${present(spell.name)}</strong>
                                  <div class="src-item-meta">
                                    <span>${present(spell.attribute)}</span>
                                    <span>MP ${present(spell.mpCost)}</span>
                                  </div>
                                  <p>${present(spell.description)}</p>
                                </div>
                              </article>
                            `
                          )
                          .join("") || "<p class='src-empty'>まだ記憶魔法はありません。</p>"}
                      </div>
                    </section>
                  `
                : codexCategory === "events"
                  ? `
                      <section class="src-card">
                        <p class="src-card__eyebrow">局面知識</p>
                        <h4>${present(display?.currentEvent?.label || "局面")}</h4>
                        <div class="src-text-list">
                          <p>${present(display?.currentEvent?.summaryText || display?.currentEvent?.summary || "まだ局面情報がありません。")}</p>
                          <p>${present(display?.currentEvent?.importanceText || display?.currentEvent?.whyImportant || "")}</p>
                          <p>${present(display?.currentEvent?.objective || display?.storyGuide?.objective || "")}</p>
                        </div>
                        <div class="src-branch-list">
                          ${(display?.currentEvent?.branchPreview || [])
                            .slice(0, 4)
                            .map((branch) => `<article><strong>${present(branch.label)}</strong><p>${present(branch.summaryText)}</p></article>`)
                            .join("") || "<p class='src-empty'>まだ局面の分岐は見えていません。</p>"}
                        </div>
                      </section>
                    `
                  : `
                      <section class="src-card">
                        <p class="src-card__eyebrow">人物知識</p>
                        <h4>所属ごとの関係者</h4>
                        <div class="src-affiliation-groups">
                          ${peopleGroups
                            .map(
                              (group) => `
                                <section class="src-affiliation-group">
                                  <div class="src-affiliation-group__header">
                                    <strong>${present(group.label)}</strong>
                                    <span>${present(group.members.length)}名</span>
                                  </div>
                                  <div class="src-knowledge-list">
                                    ${group.members
                                      .map(
                                        (item) => `
                                          <button type="button" class="src-codex-row src-codex-row--interactive ${focusCast.npcId === item.npcId ? "is-active" : ""}" data-codex-focus-npc="${escapeHtml(item.npcId || "")}">
                                            <strong>${present(item.displayName)}</strong>
                                            <p>${present(npcMetaLine(item))}</p>
                                            <p>${present(item.summaryText || item.agenda || item.traceText || "まだ動きが見えていません。")}</p>
                                          </button>
                                        `
                                      )
                                      .join("")}
                                  </div>
                                </section>
                              `
                            )
                            .join("")}
                          ${
                            hiddenPeopleCount
                              ? `
                                <section class="src-affiliation-group src-affiliation-group--unknown">
                                  <div class="src-affiliation-group__header">
                                    <strong>未解放</strong>
                                    <span>${present(hiddenPeopleCount)}枠</span>
                                  </div>
                                  <div class="src-knowledge-list">
                                    ${Array.from({ length: hiddenPeopleCount })
                                      .map(
                                        () => `
                                          <article class="src-codex-row src-codex-row--unknown">
                                            <strong>???</strong>
                                            <p>まだ名前が分かっていません。</p>
                                            <p>この局面で見つかる可能性があります。</p>
                                          </article>
                                        `
                                      )
                                      .join("")}
                                  </div>
                                </section>
                              `
                              : ""
                          }
                        </div>
                      </section>
                      <section class="src-card">
                        <p class="src-card__eyebrow">注目人物</p>
                        <h4>${present(focusCast.displayName || "関係者")}</h4>
                        <div class="src-text-list">
                          <p>${present(npcMetaLine(focusCast))}</p>
                          <p>${present(focusNpc.summary || "まだ動きが見えていません。")}</p>
                          <p>${present(focusNpc.attitude || "まだ反応は定まっていません。")}</p>
                          <p>${present(focusNpc.conflict || "目立つ対立はまだ記録されていません。")}</p>
                        </div>
                      </section>
                      <section class="src-card src-card--span-2">
                        <p class="src-card__eyebrow">関係</p>
                        <h4>相関図</h4>
                        ${renderRelationGraph(display, focusCast)}
                        <div class="src-branch-list">
                          ${relationRows
                            .map((row) => `<article><strong>${present(row.label)}</strong><p>${present(row.detail)}</p></article>`)
                            .join("") || "<p class='src-empty'>まだ強い対立は見えていません。</p>"}
                        </div>
                      </section>
                    `;
        return `
          <div class="src-drawer-grid src-drawer-grid--codex">
            <section class="src-card src-card--span-2">
              <p class="src-card__eyebrow">知識</p>
              <h4>見えてきたもの</h4>
              <div class="src-knowledge-grid">
                ${categoryRows
                  .map(
                    (row) => `
                      <article class="src-knowledge-card">
                        <strong>${present(row.label)}</strong>
                        <div class="src-knowledge-meta">
                          <span>${present(row.known)} / ${present(row.total)}</span>
                          <span>記録済み</span>
                        </div>
                        <p>${present(row.note)}</p>
                      </article>
                    `
                  )
                  .join("")}
              </div>
            </section>
            <section class="src-card src-card--span-2">
              <p class="src-card__eyebrow">分類</p>
              <div class="src-filter-row">
                ${codexTabs
                  .map(
                    ([key, label]) => `
                      <button type="button" class="src-filter-chip ${codexCategory === key ? "is-active" : ""}" data-codex-category="${key}">
                        ${escapeHtml(label)}
                      </button>
                    `
                  )
                  .join("")}
              </div>
            </section>
            ${codexBody}
          </div>
        `;
      case "journal":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">記録</p>
              <h4>セッションの持ち越し</h4>
              <div class="src-tag-list">${renderTags(labeledList(display?.nextSessionHook?.carriedPressures || [], (value) => presentLabel(value)), "warning")}</div>
              <div class="src-tag-list">${renderTags(labeledList(display?.nextSessionHook?.npcCarryOvers || [], (value) => presentLabel(value)), "accent")}</div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">見通し</p>
              <h4>小結末</h4>
              <p>${present(display?.sessionEnding?.summary || display?.endingForecast?.summary || "まだ小結末は確定していません。")}</p>
            </section>
          </div>
        `;
      case "world":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">世界</p>
              <h4>世界の気配</h4>
              <div class="src-text-list">
                <p>${present(display?.worldPulsePanel?.summary || "世界の動きはまだ読めていません。")}</p>
                <p>${present(display?.worldPulsePanel?.focus || "")}</p>
                <p>${present(display?.worldPulsePanel?.read || "")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">このセッション</p>
              <h4>いま見ておくこと</h4>
              <div class="src-text-list">
                <p>${present(display?.storyGuide?.now || "このセッションの状況を読み込み中です。")}</p>
                <p>${present(display?.storyGuide?.stakes || "何が危ういかを整理しています。")}</p>
                <p>${present(display?.storyGuide?.objective || "次の目的を読み込み中です。")}</p>
                <p>${present(display?.storyGuide?.forecast || "先の見通しはまだまとまっていません。")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">取り決め</p>
              <h4>危うい取り決め</h4>
              <div class="src-kv">
                <div><span>主神</span><strong>${present(display?.worldSpine?.mainGodLabel)}</strong></div>
                <div><span>連鎖</span><strong>${present(display?.worldSpine?.activeChainLabel)}</strong></div>
                <div><span>同期</span><strong>${present(display?.worldSpine?.syncState)}</strong></div>
                <div><span>優勢分岐</span><strong>${present(display?.worldSpine?.dominantBranch)}</strong></div>
              </div>
              <div class="src-text-list">
                <p>${present(display?.institutionAlertGuide?.summary || display?.institutionAlert?.label || "いまは大きな制度圧は見えていません。")}</p>
                <p>${present(display?.institutionAlertGuide?.consequence || "")}</p>
              </div>
              <div class="src-tag-list">${renderTags(labeledList(display?.worldSpine?.topNotes || [], (value) => presentLabel(value)), "note")}</div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">残り火</p>
              <h4>持ち越しと見通し</h4>
              <div class="src-text-list">
                <p>${present(display?.archiveReview?.latestArchiveSummary || display?.storyGuide?.trace || "まだ大きな持ち越しはありません。")}</p>
                <p>${present(display?.archiveReview?.resurfacingRisk || "")}</p>
              </div>
              <div class="src-tag-list">
                ${renderTags(
                  carryTags.length
                    ? carryTags.slice(0, 6)
                    : labeledList(display?.worldSpine?.topNotes || [], (value) => presentLabel(value)),
                  "warning"
                )}
              </div>
            </section>
          </div>
        `;
      case "dice":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">進行</p>
              <h4>このセッションの進み具合</h4>
              <div class="src-kv">
                <div><span>セッション</span><strong>${present(display?.playCycle?.sessionNumber || 1)}</strong></div>
                <div><span>手番</span><strong>${present(display?.playCycle?.turnInSession || 1)} / ${present(display?.playCycle?.maxTurns || 6)}</strong></div>
                <div><span>局面</span><strong>${present(display?.playCycle?.phaseLabel || "進行中")}</strong></div>
              </div>
              <p>${present(display?.actionGuide?.choiceMode || "通常行動で進行します。")}</p>
              <p>${present(display?.actionGuide?.sessionFlow || "途中で区切るときは保存できます。")}</p>
              <p>${present(nextSessionNotice(display))}</p>
            </section>
          </div>
        `;
      case "assets":
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">画像</p>
              <h4>画像候補</h4>
              <p>${present(assetPromptPack.visualDirection || "この局面で使う画像候補を表示します。")}</p>
              <div class="src-kv">
                <div><span>件数</span><strong>${present(assetPromptPack.entryCount || 0)}</strong></div>
                <div><span>セット</span><strong>${present(assetPromptPack.batchTitle || "画像セット")}</strong></div>
              </div>
              <div class="src-tag-list">${renderTags(assetStateRows, "note")}</div>
              <div class="src-text-list">
                <p>${present(assetPromptPack.exportCommand || "画像書き出しのコマンドはまだありません。")}</p>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">人物画</p>
              <h4>共通の画風ルール</h4>
              <div class="src-text-list">
                <p>${present(assetPromptPack.portraitGuide?.styleSummary || "主要人物は同じ画風とタッチでそろえます。")}</p>
                <p>${present(assetPromptPack.portraitGuide?.negativePrompt || "禁止事項はまだありません。")}</p>
              </div>
              <div class="src-tag-list">
                ${renderTags(assetPromptPack.portraitGuide?.consistencyRules || [], "note")}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">参照画像</p>
              <h4>再解釈のルール</h4>
              <div class="src-text-list">
                ${((assetPromptPack.portraitGuide?.referenceHandling || [])).map((line) => `<p>${present(line)}</p>`).join("") || "<p class='src-empty'>まだ参照画像のルールはありません。</p>"}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">実画像</p>
              <h4>アイコン</h4>
              <div class="src-mini-card-list">
                ${iconEntries
                  .slice(0, 8)
                  .map(
                    (entry) => `
                      <article class="src-mini-card">
                        ${renderIconTile({
                          filename: entry.suggestedFilename || null,
                          fallback: "A",
                          alt: entry.label,
                          small: true
                        })}
                        <div>
                          <strong>${present(entry.label)}</strong>
                          <div class="src-item-meta">
                            <span>${present(assetKindLabel(entry.kind))}</span>
                            <span>${present(entry.assetState || "queued")}</span>
                          </div>
                          <p>${present(entry.suggestedFilename)}</p>
                        </div>
                      </article>
                    `
                  )
                  .join("") || "<p class='src-empty'>まだ画像候補はありません。</p>"}
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">板絵</p>
              <h4>これから作る図版</h4>
              <div class="src-mini-card-list">
                ${artEntries
                  .slice(0, 6)
                  .map(
                    (entry) => `
                      <article class="src-mini-card">
                        ${renderIconTile({
                          filename: null,
                          fallback: "絵",
                          alt: entry.label,
                          small: true
                        })}
                        <div>
                          <strong>${present(entry.label)}</strong>
                          <div class="src-item-meta">
                            <span>${present(assetKindLabel(entry.kind))}</span>
                            <span>${present(entry.assetState || "queued")}</span>
                          </div>
                          <p>${present(entry.suggestedFilename || "図版ファイル未設定")}</p>
                        </div>
                      </article>
                    `
                  )
                  .join("") || "<p class='src-empty'>まだ図版候補はありません。</p>"}
              </div>
            </section>
          </div>
        `;
      case "settings":
      default:
        return `
          <div class="src-drawer-grid">
            <section class="src-card">
              <p class="src-card__eyebrow">設定</p>
              <h4>現在の接続先</h4>
              <div class="src-kv">
                <div><span>API</span><strong>${present(STATE.settings.apiBaseUrl)}</strong></div>
                <div><span>seed</span><strong>${present(STATE.settings.seed)}</strong></div>
                <div><span>seasons</span><strong>${present(STATE.settings.seasons)}</strong></div>
                <div><span>archetype</span><strong>${present(STATE.settings.archetype)}</strong></div>
              </div>
            </section>
            <section class="src-card">
              <p class="src-card__eyebrow">補助</p>
              <h4>補助パネル</h4>
              <p>詳細設定は拡張の設定パネルから変更できます。</p>
              <button class="src-inline-button" data-open-sidepanel="true">設定パネルを開く</button>
            </section>
          </div>
        `;
    }
  }

  function render() {
    const display = STATE.display;
    const situationRows = summarizeSituation(display);
    const focusBeat = display?.npcBeats?.[0] || {};
    const focusCast = (display?.namedCast || []).find((item) => item.npcId === focusBeat.npcId) || {};
    const npcSummary = summarizeNpc(focusCast);
    const actorProfile = display?.characterProfile || {};
    const actorProfileTags = [actorProfile.raceLabel, actorProfile.styleLabel, actorProfile.originLabel, actorProfile.loadoutLabel].filter(Boolean);
    const focusConflictMarkup = npcSummary.conflict
      ? `<p class="src-muted">${present(npcSummary.conflict)}</p>`
      : "";
    const hotbarItems = [
      ["character", "装備"],
      ["inventory", "所持品"],
      ["skills", "技能"],
      ["quest", "局面"],
      ["codex", "図鑑"],
      ["journal", "記録"],
      ["world", "世界"],
      ["dice", "進行"],
      ["assets", "画像"],
      ["settings", "設定"]
    ];
    const hubOverlayMarkup = STATE.drawer
      ? `
          <section class="src-hub-overlay" aria-label="${escapeHtml(STATE.drawer)} overlay">
            <div class="src-hub-overlay__header">
              <div>
                <p class="src-eyebrow">詳細</p>
                <h3>${present(hotbarItems.find(([key]) => key === STATE.drawer)?.[1] || "詳細")}</h3>
              </div>
              <button class="src-inline-button" data-close-hub="true">閉じる</button>
            </div>
            <div class="src-hub-tabs">
              ${hotbarItems
                .map(
                  ([key, label]) => `
                    <button class="src-hotbar__button ${STATE.drawer === key ? "is-active" : ""}" data-drawer="${key}">
                      <span>${escapeHtml(label)}</span>
                    </button>
                  `
                )
                .join("")}
            </div>
            <div class="src-hub-overlay__body">
              ${drawerContent(display)}
            </div>
          </section>
        `
      : "";
    const startOverlayMarkup = renderStartOverlay(display);

    mount.innerHTML = `
      <div class="src-shell-root ${STATE.visible ? "is-open" : "is-collapsed"}">
        <button class="src-launcher" data-launcher="true">${STATE.visible ? "閉じる" : "Star Ring Codex"}</button>
        <section class="src-shell" aria-hidden="${STATE.visible ? "false" : "true"}">
          <header class="src-world-spine">
            <div class="src-brand">
              <p class="src-eyebrow">ゲームシェル</p>
              <h2>Star Ring Codex</h2>
            </div>
            <div class="src-world-kv">
              <span>${present(display?.worldSpine?.worldName || "未読込")}</span>
              <span>${present(display?.worldSpine?.eraLabel || "時代待ち")}</span>
              <span>${present(display?.worldSpine?.calendarName || "暦待ち")} ${present(display?.worldSpine?.year || "")}年</span>
              <span>主神 ${present(display?.worldSpine?.mainGodLabel || "-")}</span>
              <span>連鎖 ${present(display?.worldSpine?.activeChainLabel || "-")}</span>
              <span class="src-sync src-sync--${escapeHtml(STATE.status.tone)}">${present(STATE.status.text)}</span>
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
                <p class="src-eyebrow">主人公</p>
                <h3>${present(display?.actorRail?.label || "旅人")}</h3>
                <p class="src-subtitle">${present(display?.actorRail?.existenceTitle || "存在級位未設定")}</p>
                ${actorProfileTags.length ? `<div class="src-tag-list">${renderTags(actorProfileTags, "note")}</div>` : ""}
                <div class="src-meter-grid">
                  <div><span>HP</span><strong>${present(display?.actorRail?.hp?.current)}/${present(display?.actorRail?.hp?.max)}</strong></div>
                  <div><span>MP</span><strong>${present(display?.actorRail?.mp?.current)}/${present(display?.actorRail?.mp?.max)}</strong></div>
                  <div><span>Vessel</span><strong>${present(display?.actorRail?.vessel)}</strong></div>
                </div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">状態</p>
                <div class="src-tag-list">${renderTags(labeledList(display?.actorRail?.statuses || [], (item) => presentLabel(item.label)), "warning")}</div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">加護</p>
                <div class="src-tag-list">${renderTags(labeledList(display?.actorRail?.blessings || [], (item) => presentLabel(item.label)), "accent")}</div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">よく使う行動</p>
                <div class="src-tag-list">${renderTags(labeledList(display?.actorRail?.quickSlots || [], (item) => presentLabel(item.label)), "slot")}</div>
              </div>
            </aside>

            <section class="src-narrative-core">
              <div class="src-panel src-panel--hero">
                <p class="src-eyebrow">状況</p>
                <h3>${present(display?.scenePacket?.focusLabel || "現在の場面")}</h3>
                <p class="src-headline">${present(display?.currentEvent?.label || display?.scenePacket?.playerFacing?.headline || "場面データを読んでいます。")}</p>
                <p class="src-location">${present(display?.scenePacket?.locationLabel || "")}</p>
                <div class="src-scene-lines">
                  ${situationRows
                    .map(
                      (row) => `
                        <div class="src-scene-line">
                          <strong>${present(row.label)}</strong>
                          <p>${present(row.value)}</p>
                        </div>
                      `
                    )
                    .join("")}
                </div>
              </div>

              <div class="src-panel">
                <p class="src-eyebrow">選択肢</p>
                <div class="src-choice-list">
                  ${(display?.scenePacket?.playerFacing?.choiceChips || [])
                    .map(
                      (choice) => `
                        <button class="src-choice-chip" data-choice-id="${escapeHtml(choice.choiceId)}" ${STATE.pending ? "disabled" : ""}>
                          ${present(choice.label)}
                        </button>
                      `
                    )
                    .join("") || "<p class='src-empty'>選択肢はまだありません。</p>"}
                </div>
                <div class="src-tag-list">
                  ${renderTags(labeledList(display?.currentEvent?.recommendedChoiceLabels || [], (value) => presentLabel(value)), "slot")}
                </div>
              </div>
            </section>

            <aside class="src-context-rail">
              <div class="src-panel">
                <p class="src-eyebrow">注目人物</p>
                <h3>${present(focusCast.displayName || focusBeat.displayName || "関係者")}</h3>
                <p class="src-subtitle">${present(npcMetaLine(focusCast))}</p>
                <p>${present(npcSummary.summary)}</p>
                <p class="src-muted">${present(npcSummary.attitude || "まだ反応は定まっていません。")}</p>
                ${focusConflictMarkup}
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">この局面</p>
                <h3>${present(display?.activeNode?.title || "局面")}</h3>
                <p>${present(display?.activeNode?.questTitle || display?.currentEvent?.summaryText || "現在の問題を読み込んでいます。")}</p>
                <div class="src-tag-list">${renderTags(labeledList(display?.activeNode?.recommendedVectors || [], (value) => presentLabel(value)), "slot")}</div>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">危うい取り決め</p>
                <h3>${present(display?.institutionAlert?.label || "該当なし")}</h3>
                <p>${present(display?.institutionAlertGuide?.summary || "制度圧はまだ大きくありません。")}</p>
              </div>
              <div class="src-panel">
                <p class="src-eyebrow">世界の気配</p>
                <p>${present(display?.worldPulseGuide?.summaryText || "世界の動きを読み込んでいます。")}</p>
                <div class="src-tag-list">${renderTags(labeledList(display?.worldSpine?.topNotes || [], (value) => presentLabel(value)), "note")}</div>
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
          ${hubOverlayMarkup}
          ${startOverlayMarkup}
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
        const nextDrawer = button.getAttribute("data-drawer");
        STATE.drawer = STATE.drawer === nextDrawer ? null : nextDrawer;
        render();
      });
    });
    mount.querySelector("[data-close-hub='true']")?.addEventListener("click", () => {
      STATE.drawer = null;
      render();
    });
    mount.querySelector("[data-refresh='true']")?.addEventListener("click", () => loadSnapshot());
    mount.querySelector("[data-save='true']")?.addEventListener("click", () => saveSession());
    mount.querySelector("[data-load-save='true']")?.addEventListener("click", () => loadSavedSession());
    mount.querySelector("[data-next-session='true']")?.addEventListener("click", () => nextSession());
    mount.querySelector("[data-open-sidepanel='true']")?.addEventListener("click", async () => {
      try {
        await chrome.runtime.sendMessage({ type: "sidepanel.open-active" });
      } catch {
        setStatus("設定パネルの起動に失敗しました。", "error");
      }
    });
    mount.querySelectorAll("[data-codex-category]").forEach((button) => {
      button.addEventListener("click", () => {
        STATE.codexCategory = button.getAttribute("data-codex-category") || "people";
        render();
      });
    });
    mount.querySelectorAll("[data-codex-focus-npc]").forEach((button) => {
      button.addEventListener("click", () => {
        STATE.codexCategory = "people";
        STATE.codexFocusNpcId = button.getAttribute("data-codex-focus-npc") || null;
        render();
      });
    });
    mount.querySelectorAll("[data-character-text]").forEach((field) => {
      field.addEventListener("input", (event) => {
        const key = field.getAttribute("data-character-text");
        if (!key) {
          return;
        }
        const nextValue = event.currentTarget?.value || "";
        STATE.start = {
          ...(STATE.start || {}),
          draft: {
            ...(STATE.start?.draft || defaultCharacterDraft()),
            [key]: String(nextValue)
          }
        };
      });
    });
    mount.querySelectorAll("[data-character-choice]").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.getAttribute("data-character-choice");
        const value = button.getAttribute("data-character-value");
        if (!key || !value) {
          return;
        }
        STATE.start = {
          ...(STATE.start || {}),
          draft: {
            ...(STATE.start?.draft || defaultCharacterDraft()),
            [key]: value
          }
        };
        render();
      });
    });
    mount.querySelectorAll("[data-genesis-text]").forEach((field) => {
      field.addEventListener("input", (event) => {
        const key = field.getAttribute("data-genesis-text");
        if (!key) {
          return;
        }
        const nextValue = event.currentTarget?.value || "";
        STATE.start = {
          ...(STATE.start || {}),
          genesisDraft: {
            ...(STATE.start?.genesisDraft || buildGenesisDraft(STATE.display)),
            [key]: String(nextValue)
          }
        };
      });
    });
    mount.querySelectorAll("[data-genesis-slot-id][data-genesis-slot-field]").forEach((field) => {
      field.addEventListener("input", (event) => {
        const slotId = field.getAttribute("data-genesis-slot-id");
        const slotField = field.getAttribute("data-genesis-slot-field");
        if (!slotId || !slotField) {
          return;
        }
        const currentDraft = STATE.start?.genesisDraft || buildGenesisDraft(STATE.display);
        const slots = (currentDraft.slots || []).map((slot) =>
          slot.slotId === slotId
            ? {
                ...slot,
                [slotField]: String(event.currentTarget?.value || "")
              }
            : slot
        );
        STATE.start = {
          ...(STATE.start || {}),
          genesisDraft: {
            ...currentDraft,
            slots
          }
        };
      });
    });
    mount.querySelector("[data-start-auto='true']")?.addEventListener("click", async () => {
      STATE.start = { ...(STATE.start || {}), draft: defaultCharacterDraft(), genesisDraft: null, selectedOpeningVariant: null, appliedGenesis: false };
      await createCharacterAndLoad();
    });
    mount.querySelector("[data-start-create='true']")?.addEventListener("click", async () => {
      STATE.start = { ...(STATE.start || {}), genesisDraft: null, selectedOpeningVariant: null, appliedGenesis: false };
      await createCharacterAndLoad();
    });
    mount.querySelector("[data-start-reset-genesis='true']")?.addEventListener("click", () => {
      STATE.start = {
        ...(STATE.start || {}),
        genesisDraft: buildGenesisDraft(STATE.display),
        selectedOpeningVariant: null,
        appliedGenesis: Boolean(STATE.display?.characterProfile?.genesisApplied)
      };
      render();
    });
    mount.querySelector("[data-start-edit='true']")?.addEventListener("click", () => {
      STATE.start = { ...(STATE.start || {}), step: "create" };
      render();
    });
    mount.querySelector("[data-start-finalize='true']")?.addEventListener("click", async () => {
      await finalizeCharacterGenesis();
    });
    mount.querySelector("[data-start-begin='true']")?.addEventListener("click", () => {
      STATE.start = { ...(STATE.start || {}), step: null };
      render();
    });
    mount.querySelectorAll("[data-opening-variant-index]").forEach((button) => {
      button.addEventListener("click", () => {
        const index = Number(button.getAttribute("data-opening-variant-index"));
        const variants = STATE.display?.characterProfile?.openingVariants || [];
        const variant = variants[index];
        if (!variant) {
          return;
        }
        applyOpeningVariantToDraft({ ...variant, index });
      });
    });
    mount.querySelector("[data-opening-copy='true']")?.addEventListener("click", async () => {
      const variant = (STATE.display?.characterProfile?.openingVariants || [])[STATE.start?.selectedOpeningVariant || 0] || null;
      const promptText = buildOpeningPromptPreviewText(STATE.display, variant);
      try {
        const copied = await copyTextToClipboard(promptText);
        if (!copied) {
          throw new Error("コピーに失敗しました。");
        }
        setStatus("導入候補をコピーしました。", "ok");
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
    mount.querySelector("[data-opening-to-composer='true']")?.addEventListener("click", async () => {
      const variant = (STATE.display?.characterProfile?.openingVariants || [])[STATE.start?.selectedOpeningVariant || 0] || null;
      const promptText = buildOpeningPromptPreviewText(STATE.display, variant);
      try {
        await sendOpeningPromptToComposer(promptText);
        setStatus("導入候補を ChatGPT の入力欄へ入れました。必要なら少し整えて送れます。", "ok");
      } catch (error) {
        setStatus(error.message, "error");
      }
    });

    mount.querySelectorAll(".src-icon-tile img").forEach((image) => {
      const applyFallback = () => {
        const tile = image.parentElement;
        if (!(tile instanceof HTMLElement)) {
          return;
        }
        const fallback = tile.dataset.fallback || "?";
        tile.classList.add("is-fallback");
        tile.textContent = fallback;
      };
      image.addEventListener(
        "error",
        applyFallback,
        { once: true }
      );
      if (image.complete && image.naturalWidth === 0) {
        applyFallback();
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
    persistShellSnapshot().catch(() => null);
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
