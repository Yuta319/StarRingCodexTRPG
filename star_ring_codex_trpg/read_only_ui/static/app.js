const statusBanner = document.getElementById("status-banner");
const actorRail = document.getElementById("actor-rail");
const worldSpine = document.getElementById("world-spine");
const worldPulse = document.getElementById("world-pulse");
const campaignWorld = document.getElementById("campaign-world");
const storyGuide = document.getElementById("story-guide");
const scenePacket = document.getElementById("scene-packet");
const activeNode = document.getElementById("active-node");
const institutionAlert = document.getElementById("institution-alert");
const npcBeats = document.getElementById("npc-beats");
const sceneTitle = document.getElementById("scene-title");
const seedInput = document.getElementById("seed-input");
const seasonsInput = document.getElementById("seasons-input");
const archetypeInput = document.getElementById("archetype-input");
const worldJsonInput = document.getElementById("world-json-input");
const saveSessionButton = document.getElementById("save-session-button");
const loadSessionButton = document.getElementById("load-session-button");
const nextSessionButton = document.getElementById("next-session-button");
const freeActionForm = document.getElementById("free-action-form");
const freeActionInput = document.getElementById("free-action-input");
const freeActionButton = document.getElementById("free-action-button");

let currentPlaySource = { seed: 1729, world_json: null };
let currentSaveRef = { saveId: null, savePath: null };
let isPending = false;
let currentDisplay = null;
let currentBundle = null;
let archiveFilterKind = "all";
let archiveRoleFilter = "all";

function renderKeyValueBlock(target, items) {
  target.innerHTML = "";
  items.forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "kv-row";
    const left = document.createElement("span");
    left.className = "kv-row__key";
    left.textContent = key;
    const right = document.createElement("span");
    right.className = "kv-row__value";
    right.textContent = Array.isArray(value) ? value.join(" / ") : String(value ?? "-");
    row.append(left, right);
    target.append(row);
  });
}

function renderTagList(values, className = "tag") {
  const wrapper = document.createElement("div");
  wrapper.className = "tag-list";
  values.forEach((value) => {
    const tag = document.createElement("span");
    tag.className = className;
    tag.textContent = value;
    wrapper.append(tag);
  });
  return wrapper;
}

function renderTextList(values, emptyText = "該当なし") {
  const wrapper = document.createElement("div");
  wrapper.className = "text-list";
  const rows = values && values.length ? values : [emptyText];
  rows.forEach((value) => {
    const p = document.createElement("p");
    p.textContent = value;
    wrapper.append(p);
  });
  return wrapper;
}

function createCard(title, body) {
  const card = document.createElement("section");
  card.className = "sub-card";
  const heading = document.createElement("h3");
  heading.textContent = title;
  card.append(heading, body);
  return card;
}

function createSection(title, entries) {
  const content = document.createElement("div");
  renderKeyValueBlock(content, entries);
  return createCard(title, content);
}

function humanizeNodeStatus(value) {
  return {
    active: "進行中",
    resolved: "収束済み",
  }[value] || "状況確認中";
}

function humanizeInstitutionStatus(value) {
  return {
    none: "該当なし",
    active: "有効",
    strained: "揺らいでいる",
    broken: "崩れている",
  }[value] || "状況確認中";
}

function humanizeVector(value) {
  return {
    diplomacy: "対話",
    stewardship: "管理",
    authority: "権限",
    stealth: "潜行",
    ritual: "儀式",
  }[value] || "別の手立て";
}

function humanizeSyncState(value) {
  return {
    synced: "同期済み",
  }[value] || "確認中";
}

function humanizeRuptureState(value) {
  return {
    stable: "まだ保っている",
    micro_leak: "小さなほころびがある",
    local_break: "局所的に崩れている",
    clear_break: "決壊寸前だ",
  }[value] || "揺らいでいる";
}

function humanizeEndingTone(value) {
  return {
    steady: "比較的安定",
    mixed: "傷を残して継続",
    grim: "厳しい結末",
  }[value] || "記録中";
}

function archivePrefix(entry) {
  const title = String(entry?.title ?? "").trim();
  const sessionNumber = entry?.sessionNumber ?? "?";
  return title ? `第${sessionNumber}節「${title}」` : `第${sessionNumber}節`;
}

function currentArchiveEntries() {
  return currentDisplay?.archiveInspector?.entries ?? currentBundle?.world_state?.campaign_state?.sessionArchive ?? [];
}

function currentArchiveInspector() {
  return currentDisplay?.archiveInspector ?? null;
}

function createArchiveSection(title, body) {
  const section = document.createElement("section");
  section.className = "archive-entry__section";
  const heading = document.createElement("h4");
  heading.textContent = title;
  section.append(heading, body);
  return section;
}

function matchesArchiveFilter(entry) {
  const tags = entry.filterTags || ["all"];
  if (archiveFilterKind !== "all" && !tags.includes(archiveFilterKind)) {
    return false;
  }
  if (archiveRoleFilter !== "all" && entry.keyRoleSlotId !== archiveRoleFilter) {
    return false;
  }
  return true;
}

function buildArchiveFilters(inspector, onChange) {
  const wrapper = document.createElement("div");
  wrapper.className = "archive-filters";

  const kinds = [
    ["all", "すべて"],
    ["hook", "いま効いているもの"],
    ["vice", "悪徳"],
    ["taboo", "禁忌"],
    ["hidden", "隠れた傷"],
    ["resurfacing", "再燃"],
  ];
  const kindRow = document.createElement("div");
  kindRow.className = "archive-filters__row";
  kinds.forEach(([value, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "archive-filter-chip";
    if (archiveFilterKind === value) {
      button.classList.add("archive-filter-chip--active");
    }
    button.textContent = label;
    button.addEventListener("click", () => {
      archiveFilterKind = value;
      onChange();
    });
    kindRow.append(button);
  });
  wrapper.append(kindRow);

  const roleSelect = document.createElement("select");
  roleSelect.className = "archive-filter-select";
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = "すべての座";
  roleSelect.append(allOption);
  (inspector.roleFilters || []).forEach((role) => {
    const option = document.createElement("option");
    option.value = role.roleSlotId;
    option.textContent = role.roleLabel;
    if (archiveRoleFilter === role.roleSlotId) {
      option.selected = true;
    }
    roleSelect.append(option);
  });
  roleSelect.addEventListener("change", () => {
    archiveRoleFilter = roleSelect.value;
    onChange();
  });
  wrapper.append(roleSelect);
  return wrapper;
}

function buildArchiveEntryDetail(entry, hook) {
  const wrapper = document.createElement("div");
  wrapper.className = "archive-entry__body";

  const overview = document.createElement("div");
  renderKeyValueBlock(overview, [
    ["節の始まり", entry.openingSummary || "-"],
    ["節", archivePrefix(entry)],
    ["結末", humanizeEndingTone(entry.tone)],
    ["主役の座", `${entry.keyRoleLabel || "-"} / ${entry.keyOccupantLabel || "-"}`],
    ["守れたもの", entry.protected || "-"],
    ["失ったもの", entry.lost || "-"],
    ["持ち越し", entry.carriedForward || "-"],
  ]);
  wrapper.append(createArchiveSection("記録の要点", overview));

  const residueLines = [
    entry.viceSummary,
    entry.tabooSummary,
    entry.hiddenCrimeSummary,
    entry.ritualPollutionSummary,
  ].filter(Boolean);
  wrapper.append(createArchiveSection("残った因果", renderTextList(residueLines, "この節で強く残った因果は整理中。")));

  const echoLines = [entry.archivedCauseEcho, entry.resurfacingRisk].filter(Boolean);
  wrapper.append(createArchiveSection("残響と再燃", renderTextList(echoLines, "まだ大きな再燃は見えていない。")));

  const hookLines = entry.hookConnections || [];
  wrapper.append(createArchiveSection("いまの hook への効き方", renderTextList(hookLines, "いまはこの節の因果が前面には出ていない。")));

  const priorityBlock = document.createElement("div");
  renderKeyValueBlock(priorityBlock, [
    ["優先順位", entry.priorityRank ? `上位 ${entry.priorityRank}` : "圏外"],
    ["新しさ", entry.priorityDebug?.recency ?? "-"],
    ["重さ", entry.priorityDebug?.severity ?? "-"],
    ["見えやすさ", entry.priorityDebug?.visibility ?? "-"],
    ["今との近さ", entry.priorityDebug?.relevance ?? "-"],
    ["合計", entry.priorityDebug?.total ?? "-"],
  ]);
  wrapper.append(createArchiveSection("優先の理由", priorityBlock));

  return wrapper;
}

function renderArchiveHistory(display) {
  const inspector = currentArchiveInspector();
  const archiveEntries = currentArchiveEntries();
  if (!archiveEntries.length) {
    return;
  }
  if (!inspector) {
    archiveRoleFilter = "all";
  } else if (archiveRoleFilter !== "all" && !(inspector.roleFilters || []).some((role) => role.roleSlotId === archiveRoleFilter)) {
    archiveRoleFilter = "all";
  }

  const wrapper = document.createElement("div");
  wrapper.className = "archive-list";

  const renderEntries = () => {
    wrapper.innerHTML = "";
    archiveEntries.filter(matchesArchiveFilter).forEach((entry, index) => {
      const details = document.createElement("details");
      details.className = "archive-entry";
      if (index === 0) {
        details.open = true;
      }

      const summary = document.createElement("summary");
      summary.className = "archive-entry__summary";

      const heading = document.createElement("div");
      heading.className = "archive-entry__headline";
      const prioritySuffix = entry.priorityRank ? ` / 優先 ${entry.priorityRank}` : "";
      heading.textContent = `${archivePrefix(entry)} / ${humanizeEndingTone(entry.tone)}${prioritySuffix}`;

      const meta = document.createElement("div");
      meta.className = "archive-entry__meta";
      meta.textContent = `${entry.keyRoleLabel || "関係者"} / 守れたもの: ${entry.protected || "-"} / 失ったもの: ${entry.lost || "-"} / 持ち越し: ${entry.carriedForward || "-"}`;

      summary.append(heading, meta);
      details.append(summary, buildArchiveEntryDetail(entry, display.nextSessionHook));
      wrapper.append(details);
    });

    if (!wrapper.children.length) {
      wrapper.append(renderTextList(["条件に合う記録はまだない。"]));
    }
  };

  if (inspector) {
    campaignWorld.append(createCard("節の記録の絞り込み", buildArchiveFilters(inspector, () => {
      renderCampaignWorld(currentDisplay);
    })));
    if (inspector.archiveCompression?.compressedCount > 0) {
      campaignWorld.append(createSection("圧縮した古い記録", [
        ["件数", inspector.archiveCompression.compressedCount],
        ["範囲", inspector.archiveCompression.latestSummary || "古い記録を圧縮して保持している。"],
      ]));
    }
  }

  renderEntries();
  campaignWorld.append(createCard("節の記録", wrapper));
}

function describeRequestSource(request) {
  if (request.world_json) {
    return "保存した世界の続きから読み込みました。";
  }
  return `seed ${request.seed} から世界を開きました。`;
}

function renderActor(actor, playCycle, namedCast) {
  actorRail.innerHTML = `
    <div class="actor-card">
      <p class="actor-card__eyebrow">主人公</p>
      <h2>${actor.label}</h2>
      <p class="actor-card__subtitle">${actor.existenceTitle}</p>
      <div class="actor-meters">
        <div><span>体力</span><strong>${actor.hp.current}/${actor.hp.max}</strong></div>
        <div><span>霊力</span><strong>${actor.mp.current}/${actor.mp.max}</strong></div>
        <div><span>器量</span><strong>${actor.vessel}</strong></div>
      </div>
    </div>
    <div class="actor-strip">
      <div class="actor-strip__block">
        <p>状態</p>
      </div>
      <div class="actor-strip__block">
        <p>加護</p>
      </div>
      <div class="actor-strip__block">
        <p>行動</p>
      </div>
      <div class="actor-strip__block">
        <p>進行</p>
      </div>
      <div class="actor-strip__block actor-strip__block--wide">
        <p>関係者</p>
      </div>
    </div>
  `;

  const blocks = actorRail.querySelectorAll(".actor-strip__block");
  blocks[0].append(renderTagList(actor.statuses.map((item) => item.label)));
  blocks[1].append(renderTagList(actor.blessings.map((item) => item.label), "tag tag--accent"));
  blocks[2].append(renderTagList(actor.quickSlots.map((item) => item.label), "tag tag--slot"));
  blocks[3].append(renderTagList([
    `第${playCycle.sessionNumber}節`,
    `${playCycle.turnInSession}/${playCycle.maxTurns}手目`,
    playCycle.phaseLabel,
    `残り${playCycle.remainingTurns}手`,
  ], "tag tag--note"));
  blocks[4].append(renderTagList(
    namedCast.map((item) => `${item.displayName} / ${item.trustText} / ${item.stressText}`),
    "tag tag--accent",
  ));
}

function renderStoryGuide(display) {
  storyGuide.innerHTML = "";
  if (display.sessionOpeningGuide) {
    storyGuide.append(
      createCard(
        display.sessionOpeningGuide.headline,
        renderTextList(display.sessionOpeningGuide.lines, "この節の持ち越しを確認している。"),
      ),
    );
  }
  storyGuide.append(createSection("いま起きていること", [
    ["状況", display.storyGuide.now],
    ["今回の目的", display.storyGuide.objective],
  ]));
  storyGuide.append(createSection("なぜ重要か", [
    ["重要な理由", display.storyGuide.stakes],
    ["勧めたい動き", display.storyGuide.recommendedChoiceLabels],
    ["選択の傾向", display.storyGuide.trace],
    ["結末の見立て", display.storyGuide.forecast],
  ]));
  storyGuide.append(createSection("この世界の状態", [
    ["概況", display.storyGuide.worldState],
  ]));
  if (display.actionGuide) {
    storyGuide.append(createSection("進め方の目安", [
      ["通常の選択", display.actionGuide.choiceMode],
      ["自由行動", display.actionGuide.freeActionMode],
      ["保存と継続", display.actionGuide.sessionFlow],
    ]));
  }
}

function renderScene(packet, currentEvent) {
  sceneTitle.textContent = packet.focusLabel;
  scenePacket.innerHTML = `
    <p class="scene-headline">${packet.playerFacing.headline}</p>
    <p class="scene-location">${packet.locationLabel}</p>
  `;

  const lines = document.createElement("div");
  lines.className = "scene-lines";
  packet.playerFacing.lines.forEach((line) => {
    const p = document.createElement("p");
    p.textContent = line;
    lines.append(p);
  });
  scenePacket.append(lines);

  scenePacket.append(createSection("場面の層", [
    ["場所", packet.dramaticLayers.place],
    ["焦点", packet.dramaticLayers.focus],
    ["ずれ", packet.dramaticLayers.discrepancy],
    ["反応", packet.dramaticLayers.reaction],
    ["余波", packet.dramaticLayers.aftermath],
  ]));

  const choices = document.createElement("div");
  choices.className = "choice-chips";
  packet.playerFacing.choiceChips.forEach((choice) => {
    const chip = document.createElement("button");
    chip.className = "choice-chip";
    if ((currentEvent.recommendedChoices || []).includes(choice.choiceId)) {
      chip.classList.add("choice-chip--recommended");
    }
    chip.type = "button";
    chip.disabled = isPending;
    chip.dataset.choiceId = choice.choiceId;
    chip.textContent = choice.label;
    chip.addEventListener("click", () => playChoice(choice.choiceId));
    choices.append(chip);
  });
  scenePacket.append(createCard("選べる行動", choices));
}

function renderNpcBeats(beats, namedCast) {
  const castById = Object.fromEntries(namedCast.map((item) => [item.npcId, item]));
  npcBeats.innerHTML = "";
  beats.forEach((beat) => {
    const detail = castById[beat.npcId] || {};
    const card = document.createElement("article");
    card.className = "npc-card";
    card.innerHTML = `
      <p class="npc-card__eyebrow">${humanizeRuptureState(beat.ruptureState)}</p>
      <h3>${beat.displayName}</h3>
      <p>${beat.roleBeat}</p>
      <p>${beat.relationBeat}</p>
      <p>${beat.emotionBeat}</p>
      <p><strong>対立:</strong> ${detail.conflictText || "-"}</p>
      <p><strong>弱み:</strong> ${detail.weaknessText || "-"}</p>
      <p><strong>秘密:</strong> ${detail.secretText || "-"}</p>
      <p><strong>反応:</strong> ${detail.traceText || "-"}</p>
    `;
    npcBeats.append(card);
  });
}

function renderBranchPreview(branches) {
  const container = document.createElement("div");
  container.className = "branch-preview";
  branches.forEach((branch) => {
    const block = document.createElement("div");
    block.className = "branch-preview__item";
    const title = document.createElement("p");
    title.innerHTML = `<strong>${branch.label}</strong>`;
    const summary = document.createElement("p");
    summary.textContent = branch.summaryText;
    const result = document.createElement("p");
    result.textContent = branch.resultText;
    const risk = document.createElement("p");
    risk.textContent = branch.riskText;
    block.append(title, summary, result, risk);
    if (branch.preferredChoiceLabels && branch.preferredChoiceLabels.length) {
      block.append(renderTagList(branch.preferredChoiceLabels, "tag tag--note"));
    }
    container.append(block);
  });
  return container;
}

function renderCampaignWorld(display) {
  campaignWorld.innerHTML = "";
  campaignWorld.append(createSection("現在の事件", [
    ["事件", display.currentEvent.label],
    ["局面", display.currentEvent.statusLabel],
    ["状況", display.currentEvent.summaryText],
    ["重要な点", display.currentEvent.importanceText],
    ["直前の結果", display.currentEvent.lastOutcomeText],
  ]));
  campaignWorld.append(createCard("分岐候補", renderBranchPreview(display.currentEvent.branchPreview || [])));
  campaignWorld.append(createSection("拠点", [
    ["拠点名", display.hub.label],
    ["地域", display.hub.regionLabel],
    ["状態", display.hub.statusLabel],
    ["説明", display.hub.supportText],
    ["安定", display.hub.stability],
    ["補給", display.hub.supply],
    ["緊張", display.hub.heat],
  ]));
  campaignWorld.append(createSection("坑路", [
    ["名称", display.dungeon.label],
    ["地域", display.dungeon.regionLabel],
    ["状態", display.dungeon.statusLabel],
    ["説明", display.dungeon.supportText],
    ["深度", `${display.dungeon.depth}/${display.dungeon.maxDepth}`],
    ["封印", display.dungeon.sealIntegrity],
    ["危険", display.dungeon.threat],
  ]));
  campaignWorld.append(createSection("選択の痕跡", [
    ["いま多い動き", display.playerTrace.dominantChoiceText],
    ["残った余韻", display.playerTrace.afterglowText],
  ]));
  campaignWorld.append(createSection("悪徳と禁忌の圧", [
    ["悪徳の圧", display.viceTaboo?.vicePressure ?? "-"],
    ["禁忌の圧", display.viceTaboo?.tabooPressure ?? "-"],
    ["場の腐り", display.viceTaboo?.moralCorrosion ?? "-"],
    ["悪名", display.viceTaboo?.publicInfamy ?? "-"],
    ["隠れた罪", display.viceTaboo?.hiddenCrimes ?? "-"],
    ["儀礼の汚れ", display.viceTaboo?.ritualPollution ?? "-"],
  ]));
  campaignWorld.append(createCard("悪徳が生まれやすい要因", renderTextList(display.viceTaboo?.viceSources || [], "いまは大きな悪徳圧は目立たない。")));
  campaignWorld.append(createCard("禁忌が生まれやすい要因", renderTextList(display.viceTaboo?.tabooSources || [], "いまは大きな禁忌圧は目立たない。")));
  campaignWorld.append(createCard("最近の選択", renderTextList(display.playerTrace.recentChoices, "まだ目立つ痕跡はない。")));
  if (display.lastFreeAction) {
    campaignWorld.append(createSection("直近の自由行動", [
      ["概要", display.lastFreeAction.summary],
      ["結果", display.lastFreeAction.adjudication?.outcome ?? "-"],
      ["余波", display.lastFreeAction.logs?.afterglow ?? "-"],
    ]));
  }
  campaignWorld.append(createCard("悪徳の痕", renderTextList(display.viceTaboo?.viceTrace || [], "まだ大きな悪徳の痕は残っていない。")));
  campaignWorld.append(createCard("禁忌の痕", renderTextList(display.viceTaboo?.tabooTrace || [], "まだ大きな禁忌の痕は残っていない。")));
  campaignWorld.append(createCard("見えてきた秘密", renderTextList(display.playerTrace.discoveredSecrets, "まだ大きな秘密は見えていない。")));
  campaignWorld.append(createCard("見えてきた弱み", renderTextList(display.playerTrace.knownWeaknesses, "まだ決定的な弱みは見えていない。")));
  campaignWorld.append(createCard("世界に残った痕跡", renderTextList(display.playerTrace.worldMarks, "まだ大きな傷は残っていない。")));
  campaignWorld.append(createSection("小結末", [
    ["予兆", `${display.endingForecast.title} / ${display.endingForecast.summary}`],
    ["直近の小結末", display.sessionEnding ? `${display.sessionEnding.title}。${display.sessionEnding.summary}` : "まだ小結末は出ていない。"],
    ["残ったもの", display.sessionEnding ? display.sessionEnding.whatRemained : "まだ小結末は出ていない。"],
    ["守れたもの", display.sessionEnding ? display.sessionEnding.protected : "まだ小結末は出ていない。"],
    ["失ったもの", display.sessionEnding ? display.sessionEnding.lost : "まだ小結末は出ていない。"],
    ["持ち越し", display.sessionEnding ? display.sessionEnding.carriedForward : "まだ小結末は出ていない。"],
    ["余韻", display.sessionEnding ? `${display.sessionEnding.legacyEffect} ${display.sessionEnding.keyNpcAftertaste}` : "まだ小結末は出ていない。"],
  ]));
  if (display.archiveReview) {
    campaignWorld.append(createSection("読み返し", [
      ["直近の記録", display.archiveReview.latestArchiveSummary],
      ["いま再燃している火種", display.archiveReview.resurfacingSpark ?? display.archiveReview.resurfacingRisk],
      ["まだ隠れている傷", display.archiveReview.hiddenWound ?? display.archiveReview.previousSessionScar],
    ]));
  }
  renderArchiveHistory(display);
  if (display.nextSessionHook) {
    campaignWorld.append(createCard("次の節への持ち越し", renderTextList(display.nextSessionHook.nextMainEventCandidates, "まだ次の主事件候補は固まっていない。")));
    campaignWorld.append(createCard("残る圧力", renderTextList(display.nextSessionHook.carriedPressures, "まだ大きな圧は残っていない。")));
    campaignWorld.append(createCard("続く関係", renderTextList(display.nextSessionHook.npcCarryOvers, "まだ強いしこりは残っていない。")));
    campaignWorld.append(createCard("残った傷", renderTextList(display.nextSessionHook.scarsRemaining, "まだ大きな傷は残っていない。")));
    campaignWorld.append(createCard("守れたもの", renderTextList(display.nextSessionHook.protectedAssets, "まだ守れたものは整理されていない。")));
    campaignWorld.append(createCard("強く戻ってきている因果", renderTextList(display.nextSessionHook.archivedCauseEchoes, "まだ古い因果は強く浮いていない。")));
    campaignWorld.append(createCard("再浮上の火種", renderTextList(display.nextSessionHook.resurfacingRisks, "まだ大きな再浮上の火種は見えていない。")));
    campaignWorld.append(createCard("残っている悪徳", renderTextList(display.nextSessionHook.unresolvedVice, "まだ大きな悪徳のしこりは残っていない。")));
    campaignWorld.append(createCard("残っている禁忌", renderTextList(display.nextSessionHook.unresolvedTaboo, "まだ大きな禁忌のしこりは残っていない。")));
  }
}

function renderDisplay(display) {
  if (!display) {
    return;
  }
  currentDisplay = display;
  syncActionButtons();
  renderActor(display.actorRail, display.playCycle, display.namedCast);

  renderKeyValueBlock(worldSpine, [
    ["世界", display.worldSpine.worldName],
    ["暦", `${display.worldSpine.calendarName} ${display.worldSpine.year}年`],
    ["時代", display.worldSpine.eraLabel],
    ["主神", display.worldSpine.mainGodLabel],
    ["連鎖", display.worldSpine.activeChainLabel],
    ["優勢な分岐", display.worldSpine.dominantBranch],
    ["同期", humanizeSyncState(display.worldSpine.syncState)],
  ]);
  worldSpine.append(createCard("注記", renderTagList(display.worldSpine.topNotes, "tag tag--note")));

  renderKeyValueBlock(worldPulse, [
    ["状態", display.worldPulseGuide.statusLabel],
    ["世界のゆらぎ", display.worldPulse.cycleDistortion],
    ["昇神のうねり", display.worldPulse.apotheosisFlux],
    ["継承争い", display.worldPulse.successionPressure],
    ["神々の対立", display.worldPulse.divineWarPressure],
    ["概況", display.worldPulseGuide.summaryText],
  ]);
  if (display.worldPulsePanel) {
    worldPulse.append(createSection("世界の気配の見方", [
      ["いま強い圧", display.worldPulsePanel.focus],
      ["読み方", display.worldPulsePanel.read],
    ]));
  }

  renderCampaignWorld(display);
  renderStoryGuide(display);
  renderScene(display.scenePacket, display.currentEvent);
  renderNpcBeats(display.npcBeats, display.namedCast);

  renderKeyValueBlock(activeNode, [
    ["事件名", display.activeNode.title],
    ["連鎖", display.activeNode.chainLabel],
    ["取り決め", display.activeNode.institutionLabel || "該当なし"],
    ["目的", display.activeNode.questTitle],
    ["事態の重さ", display.activeNode.severity],
    ["急ぎ", display.activeNode.urgency],
    ["進み", display.activeNode.stage],
    ["状態", humanizeNodeStatus(display.activeNode.status)],
  ]);
  if (display.activeNodeGuide) {
    activeNode.append(createSection("次の一手の見方", [
      ["局面", display.activeNodeGuide.summary],
      ["向いている動き", display.activeNodeGuide.action],
      ["いまの進み", display.activeNodeGuide.timing],
    ]));
  }
  activeNode.append(createCard("向いている動き", renderTagList((display.activeNode.recommendedVectors || []).map(humanizeVector), "tag tag--slot")));
  activeNode.append(createCard("残りそうな余波", renderTagList(display.activeNode.projectedLegacies || [], "tag tag--accent")));

  renderKeyValueBlock(institutionAlert, [
    ["取り決め", display.institutionAlert.label || "該当なし"],
    ["状態", humanizeInstitutionStatus(display.institutionAlert.status)],
    ["危うさ", display.institutionAlert.breachRisk],
  ]);
  if (display.institutionAlertGuide) {
    institutionAlert.append(createSection("約定が崩れると", [
      ["いまの見立て", display.institutionAlertGuide.summary],
      ["影響", display.institutionAlertGuide.consequence],
    ]));
  }
}

function setStatus(message, state) {
  statusBanner.textContent = message;
  statusBanner.dataset.state = state;
}

function setPlaySource(source) {
  currentPlaySource = {
    seed: source?.seed ?? null,
    world_json: source?.world_json ?? null,
  };
  if (currentPlaySource.world_json) {
    worldJsonInput.value = currentPlaySource.world_json;
  }
}

function setSaveRef(saveMeta) {
  currentSaveRef = {
    saveId: saveMeta?.saveId ?? null,
    savePath: saveMeta?.savePath ?? null,
  };
}

function syncActionButtons() {
  [saveSessionButton, loadSessionButton, nextSessionButton, freeActionButton].forEach((button) => {
    if (button) {
      button.disabled = isPending;
    }
  });
}

async function loadBundle(params) {
  const query = new URLSearchParams(params);
  isPending = true;
  syncActionButtons();
  setStatus("表示データを読み込んでいます...", "loading");
  const response = await fetch(`/api/bundle?${query.toString()}`);
  const payload = await response.json();
  if (!response.ok) {
    isPending = false;
    syncActionButtons();
    setStatus(payload.error || "表示データの読み込みに失敗しました。", "error");
    return;
  }
  setPlaySource(payload.playSource);
  setSaveRef(payload.display?.saveMeta);
  currentBundle = payload.bundle;
  isPending = false;
  syncActionButtons();
  setStatus(describeRequestSource(payload.request), "ok");
  renderDisplay(payload.display);
}

async function playChoice(choiceId) {
  if (isPending) {
    return;
  }
  isPending = true;
  syncActionButtons();
  renderDisplay(currentDisplay);
  setStatus("選択を反映しています...", "loading");
  const response = await fetch("/api/play", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      choiceId,
      seed: currentPlaySource.seed,
      world_json: currentPlaySource.world_json,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    isPending = false;
    syncActionButtons();
    renderDisplay(currentDisplay);
    setStatus(payload.error || "選択の反映に失敗しました。", "error");
    return;
  }
  setPlaySource(payload.playSource);
  currentBundle = payload.bundle;
  isPending = false;
  syncActionButtons();
  renderDisplay(payload.display);
  setStatus(payload.transition.message, payload.transition.outcome === "failure" ? "error" : "ok");
}

async function saveSession() {
  if (isPending || !currentPlaySource.world_json) {
    return;
  }
  isPending = true;
  syncActionButtons();
  setStatus("この節の記録を保存しています...", "loading");
  const response = await fetch("/api/save-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      world_json: currentPlaySource.world_json,
    }),
  });
  const payload = await response.json();
  isPending = false;
  syncActionButtons();
  if (!response.ok) {
    setStatus(payload.error || "節の記録を保存できませんでした。", "error");
    return;
  }
  setSaveRef(payload);
  setStatus(`節の記録を保存しました。保存ID: ${payload.saveId}。続けるならこのまま遊べます。`, "ok");
}

async function loadSavedSession() {
  if (isPending) {
    return;
  }
  isPending = true;
  syncActionButtons();
  setStatus("保存した続きから開いています...", "loading");
  const requestBody = currentSaveRef.saveId ? { saveId: currentSaveRef.saveId } : {};
  const response = await fetch("/api/load-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });
  const payload = await response.json();
  isPending = false;
  syncActionButtons();
  if (!response.ok) {
    setStatus(payload.error || "保存した続きを開けませんでした。", "error");
    return;
  }
  setPlaySource(payload.playSource);
  setSaveRef(payload.saveMeta);
  currentBundle = payload.bundle;
  renderDisplay(payload.display);
  setStatus("保存した続きから開きました。まずは「この節の入り口」を確認してください。", "ok");
}

async function nextSession() {
  if (isPending || !currentPlaySource.world_json) {
    return;
  }
  isPending = true;
  syncActionButtons();
  setStatus("次の節を開いています...", "loading");
  const response = await fetch("/api/next-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      world_json: currentPlaySource.world_json,
    }),
  });
  const payload = await response.json();
  isPending = false;
  syncActionButtons();
  if (!response.ok) {
    setStatus(payload.error || "次の節へ進めませんでした。", "error");
    return;
  }
  setPlaySource(payload.playSource);
  setSaveRef(payload.display?.saveMeta);
  currentBundle = payload.bundle;
  renderDisplay(payload.display);
  setStatus("次の節を開きました。持ち越しを確認してから一手目を選んでください。", "ok");
}

async function submitFreeAction() {
  const actionText = freeActionInput.value.trim();
  if (isPending || !actionText) {
    return;
  }
  isPending = true;
  syncActionButtons();
  setStatus("自由行動を裁定しています...", "loading");
  const response = await fetch("/api/free-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      actionText,
      seed: currentPlaySource.seed,
      world_json: currentPlaySource.world_json,
    }),
  });
  const payload = await response.json();
  isPending = false;
  syncActionButtons();
  if (!response.ok) {
    setStatus(payload.error || "自由行動の裁定に失敗しました。", "error");
    return;
  }
  freeActionInput.value = "";
  setPlaySource(payload.playSource);
  setSaveRef(payload.display?.saveMeta);
  currentBundle = payload.bundle;
  renderDisplay(payload.display);
  setStatus(payload.transition.message, payload.transition.outcome === "backlash" || payload.transition.outcome === "failure" || payload.transition.outcome === "exposed" ? "error" : "ok");
}

document.getElementById("seed-form").addEventListener("submit", (event) => {
  event.preventDefault();
  loadBundle({
    seed: seedInput.value,
    seasons: seasonsInput.value,
    archetype: archetypeInput.value,
  });
});

document.getElementById("world-json-form").addEventListener("submit", (event) => {
  event.preventDefault();
  loadBundle({
    world_json: worldJsonInput.value,
    seasons: seasonsInput.value,
    archetype: archetypeInput.value,
  });
});

saveSessionButton.addEventListener("click", () => {
  saveSession();
});

loadSessionButton.addEventListener("click", () => {
  loadSavedSession();
});

nextSessionButton.addEventListener("click", () => {
  nextSession();
});

freeActionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitFreeAction();
});

loadBundle({ seed: 1729, seasons: 10, archetype: "balanced" });
