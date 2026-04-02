(function installStarRingCodexShared() {
  const TERM_LABELS = {
    balanced: "標準",
    common: "一般",
    uncommon: "上質",
    rare: "希少",
    sacred: "聖別",
    crafted: "仕立て品",
    mundane: "実用品",
    royal: "特別保管",
    queued: "準備中",
    rendering: "生成中",
    revealed: "表示中",
    canonical: "確定済み",
    medium: "標準",
    heavy: "重い",
    synced: "同期済み",
    patching: "更新中",
    degraded: "要確認",
    readonly: "閲覧専用",
    active: "進行中",
    critical: "切迫",
    none: "なし",
    hub: "拠点",
    dungeon: "坑路",
    kingdom: "王国",
    shrine_synod: "宗務会",
    miners_compact: "坑道組合",
    mire_circle: "湿地圏",
    demon_domain: "魔域",
    authority: "権限",
    combat: "戦闘",
    diplomacy: "交渉",
    ritual: "儀式",
    stealth: "隠密",
    stewardship: "統治"
  };

  const SKILL_LABELS = {
    combat: "戦闘",
    diplomacy: "交渉",
    ritual: "儀式",
    stealth: "隠密",
    stewardship: "統治",
    authority: "権限"
  };

  const TENDENCY_LABELS = {
    mercy: "慈悲",
    prudence: "慎重",
    ambition: "野心",
    zeal: "熱意"
  };

  const ASSET_KIND_LABELS = {
    equipment_icon: "装備アイコン",
    equipment_plate: "装備図",
    relic_icon: "遺物アイコン",
    relic_plate: "遺物図",
    portrait_icon: "顔アイコン",
    portrait_plate: "立ち絵",
    spell_icon: "魔法アイコン",
    spell_plate: "魔法図",
    consumable_icon: "消耗品アイコン",
    tool_icon: "道具アイコン",
    quest_item_icon: "重要品アイコン"
  };

  const CHARACTER_CREATION = {
    races: [
      { id: "human", label: "人間", summary: "標準的で、どの局面にも入りやすい。" },
      { id: "elf", label: "エルフ", summary: "儀式と観察に強く、気配を拾いやすい。" },
      { id: "dwarf", label: "ドワーフ", summary: "鍛造と坑道に強く、守りも堅い。" },
      { id: "werebeast", label: "獣人", summary: "嗅覚と脚で場を読み、乱戦でも強い。" },
      { id: "birdfolk", label: "翼人", summary: "見晴らしと伝令に長け、変化を拾いやすい。" },
      { id: "fishfolk", label: "魚人", summary: "潮と航路に明るく、水辺の局面に強い。" },
      { id: "dragonewt", label: "竜人", summary: "威圧と胆力があり、前に出るほど映える。" },
      { id: "fey", label: "妖精族", summary: "夢と気配に敏く、儀式向き。" },
      { id: "demonian", label: "魔人", summary: "契約と代価に敏く、危うい局面で強い。" },
      { id: "fallen", label: "堕天族", summary: "傷を抱えつつ、危機で意地を見せる。" },
      { id: "plantfolk", label: "樹人", summary: "根気と再生力があり、支え役に向く。" },
      { id: "gemfolk", label: "石人", summary: "理を積み、長い局面で崩れにくい。" }
    ],
    styles: [
      { id: "vanguard", label: "前衛", summary: "危うい場面で前に立って押し返す。" },
      { id: "envoy", label: "交渉役", summary: "利害を見て話をまとめ、場をつなぐ。" },
      { id: "seeker", label: "探究者", summary: "見えない理由や古い理を探りにいく。" },
      { id: "shadow", label: "斥候", summary: "足跡や気配を追い、決め手を拾う。" },
      { id: "warden", label: "守り手", summary: "崩れかけた手順と補給を立て直す。" }
    ],
    temperaments: [
      { id: "mercy", label: "情に厚い", summary: "切り捨てるより、助ける道を探す。" },
      { id: "prudence", label: "慎重", summary: "ひと呼吸置いてから動き、崩れる順番を見る。" },
      { id: "ambition", label: "野心家", summary: "勝ち筋を逃さず、立場を上げる機会を掴む。" },
      { id: "zeal", label: "熱意が強い", summary: "正しいと思ったことへ勢いよく踏み込む。" },
      { id: "stoic", label: "寡黙", summary: "言葉より行動で示し、揺れても顔に出しにくい。" },
      { id: "curious", label: "好奇心が強い", summary: "未知と違和感を見つけると手を伸ばしてしまう。" },
      { id: "rebellious", label: "反骨が強い", summary: "押しつけられた理屈に従わず、納得まで噛みつく。" },
      { id: "devout", label: "敬虔", summary: "祈りと誓いを裏切らず、役目に筋を通そうとする。" }
    ],
    origins: [
      { id: "ford", label: "渡し場育ち", summary: "人と荷が交わる境目で揉め事の収め方を見てきた。" },
      { id: "shrine", label: "祠育ち", summary: "祈りと手順の近くで、形に残らない気配を学んだ。" },
      { id: "mine", label: "坑道育ち", summary: "崩落と補給の重さを知り、踏ん張りが利く。" },
      { id: "road", label: "街道育ち", summary: "検札と荷の流れを見て、人の動きに明るい。" },
      { id: "marsh", label: "湿地育ち", summary: "見えにくい道を覚えていて、痕跡と抜け道に強い。" },
      { id: "court", label: "宮廷育ち", summary: "視線と儀礼の強い場所で育ち、立場の差に敏い。" },
      { id: "harbor", label: "港育ち", summary: "荷と噂が集まる波止場で育ち、流れと相場に明るい。" },
      { id: "caravan", label: "隊商育ち", summary: "長い道と売買の駆け引きを知り、移動中でも立て直しが利く。" },
      { id: "cloister", label: "修道院育ち", summary: "静かな祈りと禁則の中で育ち、沈黙の重さを知っている。" },
      { id: "frontier", label: "辺境育ち", summary: "壁の外に近い土地で育ち、少人数の守りに慣れている。" }
    ],
    loadouts: [
      { id: "oathblade", label: "誓約の旅装", summary: "直剣と手灯で、列と約束を守る。" },
      { id: "trailbow", label: "斥候の旅装", summary: "弓と索具で、先を見て安全な道を拾う。" },
      { id: "ritescribe", label: "儀式の旅装", summary: "杖と書板で、祈りと手順を扱う。" },
      { id: "wardenhammer", label: "守り手の旅装", summary: "戦槌と護灯で、崩れた列と補給を立て直す。" },
      { id: "shadowknife", label: "影歩きの旅装", summary: "短剣と鍵具で、隠れた手順や抜け道を拾う。" },
      { id: "tailored", label: "設定から組む", summary: "人物設定と転生元の面影から初期装備一式を組み直す。" }
    ],
    sourceModes: [
      { id: "native", label: "この世界の旅人", summary: "この世界で生きてきた人物として始める。" },
      { id: "reincarnated", label: "別世界からの転生者", summary: "元の姿の面影を持ったまま、この世界へ入り直す。" }
    ]
  };

  function defaultCharacterDraft() {
    return {
      name: "",
      race: "human",
      style: "vanguard",
      temperament: "prudence",
      origin: "ford",
      loadout: "oathblade",
      sourceMode: "native",
      sourceTitle: "",
      sourceName: "",
      appearanceNotes: "",
      reinterpretationNotes: ""
    };
  }

  function creationOptions(key) {
    return CHARACTER_CREATION[key] || [];
  }

  function creationOptionLabel(key, id) {
    return creationOptions(key).find((item) => item.id === id) || null;
  }

  function characterProfileQuery(draft) {
    const payload = {
      character_race: draft.race || "human",
      character_style: draft.style || "vanguard",
      character_temperament: draft.temperament || "prudence",
      character_origin: draft.origin || "ford",
      character_loadout: draft.loadout || "oathblade",
      character_source_mode: draft.sourceMode || "native"
    };
    if (String(draft.name || "").trim()) {
      payload.character_name = String(draft.name).trim();
    }
    if (String(draft.sourceTitle || "").trim()) {
      payload.character_source_title = String(draft.sourceTitle).trim();
    }
    if (String(draft.sourceName || "").trim()) {
      payload.character_source_name = String(draft.sourceName).trim();
    }
    if (String(draft.appearanceNotes || "").trim()) {
      payload.character_appearance_notes = String(draft.appearanceNotes).trim();
    }
    if (String(draft.reinterpretationNotes || "").trim()) {
      payload.character_reinterpretation_notes = String(draft.reinterpretationNotes).trim();
    }
    return payload;
  }

  window.__starRingCodexShared = {
    TERM_LABELS,
    SKILL_LABELS,
    TENDENCY_LABELS,
    ASSET_KIND_LABELS,
    CHARACTER_CREATION,
    defaultCharacterDraft,
    creationOptions,
    creationOptionLabel,
    characterProfileQuery
  };
})();
