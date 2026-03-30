from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TermEntry:
    internal_key: str
    ui_label: str
    natural_phrase: str
    register: str


_TERMS = {
    "distortion": TermEntry("distortion", "世界のゆらぎ", "世界の綻びが広がっている", "plain_japanese"),
    "cycleDistortion": TermEntry("cycleDistortion", "世界のゆらぎ", "世界の綻びが広がっている", "plain_japanese"),
    "apotheosis_flux": TermEntry("apotheosis_flux", "昇神のうねり", "昇神をめぐる気配が強まっている", "world_term"),
    "apotheosisFlux": TermEntry("apotheosisFlux", "昇神のうねり", "昇神をめぐる気配が強まっている", "world_term"),
    "succession_pressure": TermEntry("succession_pressure", "継承争い", "継承をめぐる争いが表に出ている", "plain_japanese"),
    "successionPressure": TermEntry("successionPressure", "継承争い", "継承をめぐる争いが表に出ている", "plain_japanese"),
    "divine_war_pressure": TermEntry("divine_war_pressure", "神々の対立", "神々の争いが表へにじんでいる", "world_term"),
    "divineWarPressure": TermEntry("divineWarPressure", "神々の対立", "神々の争いが表へにじんでいる", "world_term"),
    "breach_risk": TermEntry("breach_risk", "取り決めの危うさ", "このままでは取り決めが崩れかねない", "plain_japanese"),
    "breachRisk": TermEntry("breachRisk", "取り決めの危うさ", "このままでは取り決めが崩れかねない", "plain_japanese"),
    "sealIntegrity": TermEntry("sealIntegrity", "封印の状態", "封印の効きが弱まっている", "world_term"),
    "seal_integrity": TermEntry("seal_integrity", "封印の状態", "封印の効きが弱まっている", "world_term"),
    "threat": TermEntry("threat", "坑路の危険", "坑路の危険が増している", "plain_japanese"),
    "stability": TermEntry("stability", "拠点の安定", "拠点はまだ持ちこたえている", "plain_japanese"),
    "heat": TermEntry("heat", "場の荒れ具合", "場の空気が荒れている", "plain_japanese"),
    "supply": TermEntry("supply", "物資の余裕", "補給が乱れている", "plain_japanese"),
    "pressure": TermEntry("pressure", "事態の切迫度", "放っておくと手遅れになる", "plain_japanese"),
    "vicePressure": TermEntry("vicePressure", "悪事の広がり", "ごまかしや横流しが起こりやすい", "plain_japanese"),
    "tabooPressure": TermEntry("tabooPressure", "禁じ手の気配", "禁じ手の誘いが強まっている", "plain_japanese"),
    "moralCorrosion": TermEntry("moralCorrosion", "場の荒み", "見て見ぬふりが積み重なっている", "plain_japanese"),
    "publicInfamy": TermEntry("publicInfamy", "悪名", "悪い噂が広がっている", "plain_japanese"),
    "hiddenCrimes": TermEntry("hiddenCrimes", "隠れた罪", "表に出ていない罪が積もっている", "plain_japanese"),
    "ritualPollution": TermEntry("ritualPollution", "儀礼の汚れ", "祈りと封印に濁りが残っている", "world_term"),
    "publicLegitimacy": TermEntry("publicLegitimacy", "公の信", "制度への信が揺らいでいる", "plain_japanese"),
    "collectiveEfficacy": TermEntry("collectiveEfficacy", "人の連携", "まだ助け合いが働いている", "plain_japanese"),
    "observe": TermEntry("observe", "周囲を見る", "まず状況を見極める", "plain_japanese"),
    "inspect": TermEntry("inspect", "手がかりを調べる", "記録や痕跡を確かめる", "plain_japanese"),
    "speak": TermEntry("speak", "関係者に話す", "相手の本音を引き出す", "plain_japanese"),
    "intervene": TermEntry("intervene", "踏み込んで動く", "危険を承知で事態に手を入れる", "plain_japanese"),
    "custom_action": TermEntry("custom_action", "自由行動", "定型の外から独自の手を打つ", "plain_japanese"),
    "success": TermEntry("success", "うまく収まった", "ひとまず持ち直した", "plain_japanese"),
    "partial_success": TermEntry("partial_success", "痛みを残して進んだ", "前には進んだが借りが残った", "plain_japanese"),
    "failure": TermEntry("failure", "止めきれなかった", "悪化を止めきれなかった", "plain_japanese"),
    "concealed_success": TermEntry("concealed_success", "気づかれずに通した", "狙いは通ったが跡だけが残った", "plain_japanese"),
    "exposed": TermEntry("exposed", "表に出た", "隠していた行いが露見した", "plain_japanese"),
    "backlash": TermEntry("backlash", "強い反動を受けた", "禁じ手の反動がこちらへ返ってきた", "plain_japanese"),
    "holding": TermEntry("holding", "安定している", "まだ持ちこたえている", "plain_japanese"),
    "tense": TermEntry("tense", "緊張が高まっている", "いまにも荒れそうだ", "plain_japanese"),
    "fracturing": TermEntry("fracturing", "崩れかけている", "足場そのものが危ない", "plain_japanese"),
    "sealed": TermEntry("sealed", "まだ封じられている", "封印はまだ働いている", "world_term"),
    "unstable": TermEntry("unstable", "揺らいでいる", "いまにも崩れそうだ", "plain_japanese"),
    "breach_risk_status": TermEntry("breach_risk_status", "決壊寸前だ", "ひと押しで崩れそうだ", "plain_japanese"),
    "mapped": TermEntry("mapped", "道筋は見えている", "進むべき路は読めている", "plain_japanese"),
    "critical": TermEntry("critical", "かなり切迫している", "今すぐ手を打たないと危ない", "plain_japanese"),
    "escalating": TermEntry("escalating", "悪化しつつある", "放置するとさらに厄介になる", "plain_japanese"),
    "contained": TermEntry("contained", "いったん抑えられている", "今はまだ踏みとどまっている", "plain_japanese"),
    "active": TermEntry("active", "進行中", "まだ収まっていない", "plain_japanese"),
    "resolved": TermEntry("resolved", "いったん収まった", "いまは表立って燃えていない", "plain_japanese"),
    "synced": TermEntry("synced", "同期済み", "表示は最新の状態を読んでいる", "plain_japanese"),
    "none": TermEntry("none", "該当なし", "いまは特記すべきものがない", "plain_japanese"),
}


def get_term(internal_key: str) -> TermEntry | None:
    return _TERMS.get(internal_key)


def ui_label(internal_key: str, fallback: str | None = None) -> str:
    entry = get_term(internal_key)
    return entry.ui_label if entry else (fallback or internal_key)


def natural_phrase(internal_key: str, fallback: str | None = None) -> str:
    entry = get_term(internal_key)
    return entry.natural_phrase if entry else (fallback or internal_key)


def all_internal_keys() -> list[str]:
    return sorted(_TERMS)
