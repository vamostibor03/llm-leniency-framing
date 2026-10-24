"""Experiment configuration: regimes (Lee's E0-E3b), extension flags, models.

All extension flags default to Lee's baseline, so ``Condition(regime="E2")`` *is* Lee's E2.

Config files are YAML (or JSON) with three sections::

    experiment: {name, supergames, periods, history_window, seed, concurrency}
    models:     {agent_a, agent_b, authority, classifier, temperature, ...}
    conditions: [ {name, regime, framing, chat, reasoning, reveal_reporter,
                   post_conviction: {...}}, ... ]

See ``configs/lee_baseline.yaml`` and ``configs/extensions.yaml``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Regimes
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Regime:
    """Enforcement regime. Defaults follow Lee (SSRN 7426061)."""

    name: str
    authority: bool = True  # is there an authority (audits, rulings, fines)?
    reporting: bool = True  # can firms file secret / public reports?
    fine: float = 200.0  # F
    leniency: bool = False  # sole reporter fined 0, both reporters F/2
    reward_multiple: float = 0.0  # R = reward_multiple * F, paid to a sole reporter on conviction
    audit_prob: float = 0.10  # alpha: random audit probability per period

    @property
    def reward(self) -> float:
        return self.reward_multiple * self.fine


REGIMES: Dict[str, Regime] = {
    # E0 laissez-faire: no authority, no reporting option (our reading of Lee; see README).
    "E0": Regime("E0", authority=False, reporting=False, fine=0.0, audit_prob=0.0),
    # E1 fines only: reporting is possible but gives no exemption.
    "E1": Regime("E1"),
    # E2 leniency: sole reporter 0, non-reporter F, both F/2.
    "E2": Regime("E2", leniency=True),
    # E3a / E3b leniency + reward R = 1F / 2F to the sole (first) reporter.
    "E3a": Regime("E3a", leniency=True, reward_multiple=1.0),
    "E3b": Regime("E3b", leniency=True, reward_multiple=2.0),
}


# --------------------------------------------------------------------------- #
# Post-conviction policy (extension 2: "realistic leniency")
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PostConviction:
    """What happens after a conviction. All False/neutral = Lee (bounty can be farmed every period).

    once_per_episode: amnesty and reward are granted at most once per cartel *episode*. An
        episode ends at the first period whose conversation the ground-truth classifier labels
        as "no agreement"; until then a further conviction gets no amnesty and no reward.
    repeat_offender_ineligible: a firm convicted before in this supergame (including one that
        received amnesty) is no longer eligible for amnesty or reward (Chen & Rey 2013).
    recidivism_multiplier: fine multiplier k for a firm's second and later convictions.
    monitoring_notice: after the first conviction both firms are told the market is under
        monitoring (and about k, if k != 1).
    monitored_audit_prob: if set, the audit probability after the first conviction.
    """

    once_per_episode: bool = False
    repeat_offender_ineligible: bool = False
    recidivism_multiplier: float = 1.0
    monitoring_notice: bool = False
    monitored_audit_prob: Optional[float] = None

    @property
    def active(self) -> bool:
        return (
            self.once_per_episode
            or self.repeat_offender_ineligible
            or self.recidivism_multiplier != 1.0
            or self.monitoring_notice
            or self.monitored_audit_prob is not None
        )

    @classmethod
    def dissolve_on_conviction(cls, k: float = 2.0, monitored_audit_prob: Optional[float] = None):
        """The 'realistic leniency' bundle: no repeat bounty, repeat offenders lose leniency,
        monitoring notice and a k-fold fine for a second conviction."""
        return cls(True, True, k, True, monitored_audit_prob)


# --------------------------------------------------------------------------- #
# Condition = regime x extension flags
# --------------------------------------------------------------------------- #

FRAMINGS = ("legal", "neutral")
CHAT_MODES = ("mandatory", "optional", "none")
REASONING_MODES = ("one_sentence", "free")
REVEAL_MODES = ("implicit", "explicit", "hidden")


@dataclass(frozen=True)
class Condition:
    """One experimental cell. Defaults reproduce Lee's protocol for ``regime``.

    framing: "legal" (Lee) or "neutral" (Form R / review / adjustment / bonus; identical payoffs).
    chat: "mandatory" (Lee: 2 rounds x 1 message each), "optional" (may send an empty message),
        "none" (tacit: no communication; the authority then has nothing to convict on).
    reasoning: "one_sentence" (Lee) or "free" (unconstrained reasoning field).
    reveal_reporter: what the history shows about enforcement.
        "implicit" (Lee): own price, competitor price, own profit, own fine, own reward;
            who reported is only inferable from fines/rewards.
        "explicit": additionally whether an investigation happened, what triggered it
            (whose report / audit) and the ruling.
        "hidden": only own net payoff per period (no fine/reward breakdown).
    """

    regime: str = "E2"
    name: Optional[str] = None
    framing: str = "legal"
    chat: str = "mandatory"
    chat_rounds: int = 2
    reasoning: str = "one_sentence"
    reveal_reporter: str = "implicit"
    post_conviction: PostConviction = field(default_factory=PostConviction)
    false_report_penalty: float = 0.0  # extension hook; Lee: 0

    def __post_init__(self):
        if self.regime not in REGIMES:
            raise ValueError(f"unknown regime {self.regime!r}; choose from {list(REGIMES)}")
        for value, allowed, what in (
            (self.framing, FRAMINGS, "framing"),
            (self.chat, CHAT_MODES, "chat"),
            (self.reasoning, REASONING_MODES, "reasoning"),
            (self.reveal_reporter, REVEAL_MODES, "reveal_reporter"),
        ):
            if value not in allowed:
                raise ValueError(f"{what} must be one of {allowed}, got {value!r}")
        if self.name is None:
            object.__setattr__(self, "name", self.default_name())

    @property
    def regime_spec(self) -> Regime:
        return REGIMES[self.regime]

    @property
    def is_lee_baseline(self) -> bool:
        return (
            self.framing == "legal"
            and self.chat == "mandatory"
            and self.chat_rounds == 2
            and self.reasoning == "one_sentence"
            and self.reveal_reporter == "implicit"
            and not self.post_conviction.active
            and self.false_report_penalty == 0
        )

    def default_name(self) -> str:
        parts = [self.regime]
        if self.framing != "legal":
            parts.append(self.framing)
        if self.chat != "mandatory":
            parts.append(f"chat-{self.chat}")
        if self.chat_rounds != 2:
            parts.append(f"rounds{self.chat_rounds}")
        if self.reasoning != "one_sentence":
            parts.append(f"reason-{self.reasoning}")
        if self.reveal_reporter != "implicit":
            parts.append(f"reveal-{self.reveal_reporter}")
        if self.post_conviction.active:
            parts.append("dissolve")
        return "_".join(parts)

    def flags(self) -> Dict[str, Any]:
        """Flat dict of the condition, logged on every period row."""
        d = asdict(self)
        pc = d.pop("post_conviction")
        d.update({f"pc_{k}": v for k, v in pc.items()})
        d["lee_baseline"] = self.is_lee_baseline
        return d


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


@dataclass
class ModelSpec:
    """One backend. ``model`` is an OpenRouter-style id, or ``mock:<policy>``."""

    model: str
    temperature: float = 1.0
    max_tokens: int = 400
    json_mode: bool = True  # request response_format=json_object (dropped if rejected)
    extra_body: Dict[str, Any] = field(default_factory=dict)  # e.g. {"reasoning": {"enabled": false}}


@dataclass
class Models:
    agent_a: ModelSpec
    agent_b: ModelSpec
    authority: ModelSpec
    classifier: Optional[ModelSpec]  # None disables the ground-truth classifier

    def by_role(self) -> Dict[str, Optional[ModelSpec]]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "authority": self.authority,
            "classifier": self.classifier,
        }


@dataclass
class ExperimentConfig:
    name: str = "lee_replication"
    supergames: int = 30
    periods: int = 20  # Lee: 20, not told to agents
    history_window: int = 40  # Lee: last 40 periods
    seed: int = 0
    concurrency: int = 8  # supergames in flight
    max_inflight_calls: int = 32  # model calls in flight
    max_parse_retries: int = 3
    models: Models = None  # type: ignore[assignment]
    conditions: List[Condition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["conditions"] = [c.flags() for c in self.conditions]
        return d


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def _model_spec(raw: Any, defaults: Dict[str, Any]) -> Optional[ModelSpec]:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = {"model": raw}
    merged = {**defaults, **raw}
    allowed = {f.name for f in fields(ModelSpec)}
    return ModelSpec(**{k: v for k, v in merged.items() if k in allowed})


def parse_models(raw: Dict[str, Any]) -> Models:
    """``models:`` section. Scalars at the top level are defaults for every role; the judge
    roles (authority, classifier) default to temperature 0."""
    raw = dict(raw or {})
    shared = {k: raw.pop(k) for k in list(raw) if k in {f.name for f in fields(ModelSpec)} and k != "model"}
    default_model = raw.pop("default", None) or raw.pop("model", None) or "openai/gpt-4.1-mini"
    agent_a = _model_spec(raw.get("agent_a", default_model), shared)
    agent_b = _model_spec(raw.get("agent_b", raw.get("agent_a", default_model)), shared)
    judge_defaults = {**shared, "temperature": 0.0}
    authority = _model_spec(raw.get("authority", default_model), judge_defaults)
    classifier_raw = raw.get("classifier", raw.get("authority", default_model))
    classifier = _model_spec(classifier_raw, judge_defaults) if classifier_raw else None
    return Models(agent_a, agent_b, authority, classifier)


def parse_condition(raw: Any) -> Condition:
    if isinstance(raw, str):
        return Condition(regime=raw)
    raw = dict(raw)
    pc = raw.pop("post_conviction", None)
    dissolve = raw.pop("dissolve_on_conviction", False)
    if dissolve:
        opts = dissolve if isinstance(dissolve, dict) else {}
        pc_obj = PostConviction.dissolve_on_conviction(**opts)
    elif pc:
        pc_obj = PostConviction(**pc)
    else:
        pc_obj = PostConviction()
    return Condition(post_conviction=pc_obj, **raw)


def load_config(path: str | Path) -> ExperimentConfig:
    text = Path(path).read_text()
    if str(path).endswith((".yaml", ".yml")):
        import yaml  # optional dependency, only for YAML configs

        raw = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    exp = dict(raw.get("experiment", {}))
    cfg = ExperimentConfig(**exp)
    cfg.models = parse_models(raw.get("models", {}))
    cfg.conditions = [parse_condition(c) for c in raw.get("conditions", list(REGIMES))]
    names = [c.name for c in cfg.conditions]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate condition names: {names}")
    return cfg


def with_mock_models(cfg: ExperimentConfig, policy_a: str, policy_b: Optional[str] = None) -> ExperimentConfig:
    """Replace every backend with the scripted MockLLM (no network, no key)."""
    policy_b = policy_b or policy_a
    m = cfg.models
    cfg.models = Models(
        agent_a=replace(m.agent_a, model=f"mock:{policy_a}"),
        agent_b=replace(m.agent_b, model=f"mock:{policy_b}"),
        authority=replace(m.authority, model="mock:authority"),
        classifier=replace(m.classifier, model="mock:classifier") if m.classifier else None,
    )
    return cfg
