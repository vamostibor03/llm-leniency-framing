"""One supergame of Lee's protocol (Bigoni et al. 2012 with LLM firms).

Per period t (Lee, SSRN 7426061):
  1. chat: ``chat_rounds`` rounds x 1 message per firm, the first speaker drawn at random each
     period; an empty message is retried up to 3 times (mandatory chat).
  2. price + secret report, simultaneously: JSON {"reasoning", "price", "secret_report"}.
  3. prices are revealed.
  4. if no secret report was filed, each firm simultaneously decides on a public report.
  5. investigation if any report was filed OR a random audit fires (prob. alpha); the
     authority LLM rules guilty / not_guilty on the conversation ONLY.
  6. settlement: u = pi - fine + reward (``settle``).

We also run a separate ground-truth classifier on every non-empty conversation (C_t: explicit /
implicit / none, plus agreed price and silence pact). It never affects payoffs, except that
``PostConviction.once_per_episode`` uses it to decide when a cartel episode has ended.

All randomness (first speaker, audits) comes from per-(supergame) streams seeded independently
of the condition, so condition k and condition j face the SAME audit draws in supergame s
(common random numbers, which reduces between-condition variance).
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

from . import prompts as P
from .config import Condition, ExperimentConfig, Models, Regime
from .llm import Router, as_bool, extract_json, keyword_agreement
from .payoffs import profit

FIRMS = ("A", "B")
FREE_REASONING_MAX_TOKENS = 2000  # agents only, reasoning: free


class ParseFailure(RuntimeError):
    """A model kept returning unusable output. The supergame aborts (never imputed)."""


# --------------------------------------------------------------------------- #
# Settlement (pure, unit-tested)
# --------------------------------------------------------------------------- #


@dataclass
class EnforcementState:
    """Per-supergame enforcement memory used by the post-conviction extension."""

    convictions: Dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0})
    first_conviction_period: Optional[int] = None
    episode: int = 0  # cartel-episode counter (advances when C_t == "none")
    leniency_granted_in_episode: bool = False


@dataclass
class Settlement:
    fine: Dict[str, float]
    reward: Dict[str, float]
    eligible: Dict[str, bool]
    note: str = ""


def settle(
    regime: Regime,
    cond: Condition,
    state: EnforcementState,
    reporters: Tuple[str, ...],
    investigated: bool,
    guilty: bool,
) -> Settlement:
    """Fines and rewards for one period. Mutates ``state`` (conviction counts, episode grant).

    Lee's baseline (``PostConviction()`` all off):
      E0: nothing.  E1: guilty -> each pays F, reporting irrelevant.
      E2: guilty -> sole reporter 0, non-reporter F; both reported F/2 each; none F each.
      E3a/E3b: as E2, plus reward R = 1F / 2F to a sole reporter.
    Extensions: recidivism fine multiplier, repeat offenders lose eligibility, at most one
    amnesty/reward per cartel episode, a penalty for reports the authority rejects.
    """
    pc = cond.post_conviction
    fine = {f: 0.0 for f in FIRMS}
    reward = {f: 0.0 for f in FIRMS}
    eligible = {f: True for f in FIRMS}
    if not regime.authority or not investigated:
        return Settlement(fine, reward, eligible)
    if not guilty:
        if cond.false_report_penalty:
            for f in reporters:
                fine[f] = cond.false_report_penalty
        return Settlement(fine, reward, eligible, "acquitted")

    F = regime.fine
    for f in FIRMS:
        if pc.repeat_offender_ineligible and state.convictions[f] > 0:
            eligible[f] = False
        if pc.once_per_episode and state.leniency_granted_in_episode:
            eligible[f] = False
    mult = {f: (pc.recidivism_multiplier if state.convictions[f] > 0 else 1.0) for f in FIRMS}

    note = "convicted"
    if regime.leniency and len(reporters) == 1:
        (rep,) = reporters
        other = "B" if rep == "A" else "A"
        fine[other] = F * mult[other]
        if eligible[rep]:
            fine[rep] = 0.0
            reward[rep] = regime.reward
            state.leniency_granted_in_episode = True
            note = f"leniency to {rep}"
        else:
            fine[rep] = F * mult[rep]
            note = f"{rep} ineligible for leniency"
    elif regime.leniency and len(reporters) == 2:
        for f in FIRMS:
            fine[f] = (F / 2 if eligible[f] else F) * mult[f]
        if any(eligible.values()):
            state.leniency_granted_in_episode = True
        note = "both reported"
    else:  # E1, or leniency regime with no reporter (audit)
        for f in FIRMS:
            fine[f] = F * mult[f]
    for f in FIRMS:
        state.convictions[f] += 1
    return Settlement(fine, reward, eligible, note)


# --------------------------------------------------------------------------- #
# Supergame
# --------------------------------------------------------------------------- #


class Supergame:
    def __init__(self, cfg: ExperimentConfig, cond: Condition, index: int, router: Router):
        self.cfg, self.cond, self.index, self.router = cfg, cond, index, router
        self.regime = cond.regime_spec
        self.models: Models = cfg.models
        # independent streams, shared across conditions (common random numbers)
        self.rng_speaker = random.Random(f"{cfg.seed}|speaker|{index}")
        self.rng_audit = random.Random(f"{cfg.seed}|audit|{index}")
        self.rows: List[Dict[str, Any]] = []
        self.state = EnforcementState()

    # -- helpers ------------------------------------------------------------
    def _spec(self, firm: str):
        spec = self.models.agent_a if firm == "A" else self.models.agent_b
        # unconstrained reasoning overflows the default cap and truncates the JSON reply
        if self.cond.reasoning == "free" and spec.max_tokens < FREE_REASONING_MAX_TOKENS:
            spec = replace(spec, max_tokens=FREE_REASONING_MAX_TOKENS)
        return spec

    def _key(self, period: int, phase: str, firm: str = "", attempt: int = 0) -> str:
        return f"{self.cfg.name}|{self.cond.name}|sg{self.index}|t{period}|{phase}|{firm}|try{attempt}"

    def _audit_prob(self) -> float:
        pc = self.cond.post_conviction
        if self.state.first_conviction_period is not None and pc.monitored_audit_prob is not None:
            return pc.monitored_audit_prob
        return self.regime.audit_prob

    def _system(self) -> str:
        notice = None
        pc = self.cond.post_conviction
        if pc.monitoring_notice and self.state.first_conviction_period is not None:
            notice = P.monitoring_notice(
                self.cond, pc, self.state.first_conviction_period, self.regime, self._audit_prob()
            )
        return P.system_prompt(self.regime, self.cond, notice)

    def _history(self, firm: str) -> str:
        return P.render_history(self.rows, firm, self.cond, self.cfg.history_window)

    async def _ask_json(self, role: str, spec, msgs, period: int, phase: str, firm: str,
                        validate, meta: Dict[str, Any]) -> Tuple[Dict[str, Any], str, int]:
        """Call + parse + validate with up to ``max_parse_retries`` re-samples."""
        last = ""
        for attempt in range(self.cfg.max_parse_retries + 1):
            text = await self.router.call(
                role, spec, msgs, self._key(period, phase, firm, attempt),
                {**meta, "phase": phase, "firm": firm, "period": period},
            )
            last = text
            try:
                obj = extract_json(text)
                ok = validate(obj)
                if ok is not None:
                    return ok, text, attempt
            except ValueError:
                pass
        raise ParseFailure(f"{self.cond.name} sg{self.index} t{period} {phase} {firm}: unusable reply {last[:200]!r}")

    # -- phases ---------------------------------------------------------------
    async def _chat(self, period: int, system: str) -> Tuple[List[Dict[str, str]], str]:
        if self.cond.chat == "none":
            return [], ""
        first = self.rng_speaker.choice(FIRMS)
        order = [first, "B" if first == "A" else "A"] * self.cond.chat_rounds
        turns: List[Dict[str, str]] = []
        for i, firm in enumerate(order):
            user = P.chat_prompt(self.cond, period, self._history(firm), P.render_conversation(turns, firm))
            msgs = P.messages(system, user)
            mandatory = self.cond.chat == "mandatory"

            def validate(obj, mandatory=mandatory):
                msg = obj.get("message")
                msg = "" if msg is None else str(msg).strip()
                if mandatory and (not msg or set(msg) <= set(". …")):
                    return None  # Lee: retry on empty / ellipsis / placeholder
                return {"message": msg}

            try:
                obj, _, _ = await self._ask_json(
                    f"agent_{firm.lower()}", self._spec(firm), msgs, period, f"chat{i}", firm, validate,
                    {"history_rows": self.rows},
                )
                text = obj["message"]
            except ParseFailure:
                if not mandatory:
                    raise
                text = ""  # Lee retries 3x; a firm that still says nothing is logged as silent
            turns.append({"speaker": firm, "text": text})
        return turns, first

    async def _price(self, period: int, system: str, firm: str, conv: str) -> Dict[str, Any]:
        user = P.price_prompt(self.regime, self.cond, period, self._history(firm), conv)
        key_name = "submit_r1" if self.cond.framing == "neutral" else "secret_report"
        reporting = self.regime.reporting

        def validate(obj):
            try:
                price = int(round(float(obj.get("price"))))
            except (TypeError, ValueError):
                return None
            if not 0 <= price <= 12:
                return None
            secret = as_bool(obj.get(key_name, obj.get("secret_report", False))) if reporting else False
            if secret is None:
                return None
            return {"price": price, "secret": bool(secret), "reasoning": str(obj.get("reasoning", ""))}

        obj, raw, attempts = await self._ask_json(
            f"agent_{firm.lower()}", self._spec(firm), P.messages(system, user), period, "price", firm,
            validate, {"history_rows": self.rows},
        )
        return {**obj, "raw": raw, "retries": attempts}

    async def _public(self, period: int, system: str, firm: str, my: int, opp: int, conv: str) -> Dict[str, Any]:
        user = P.public_prompt(self.cond, period, my, opp, conv)
        key_name = "submit_r2" if self.cond.framing == "neutral" else "public_report"

        def validate(obj):
            v = as_bool(obj.get(key_name, obj.get("public_report")))
            return None if v is None else {"public": v, "reasoning": str(obj.get("reasoning", ""))}

        obj, raw, attempts = await self._ask_json(
            f"agent_{firm.lower()}", self._spec(firm), P.messages(system, user), period, "public", firm,
            validate, {"history_rows": self.rows},
        )
        return {**obj, "raw": raw, "retries": attempts}

    async def _authority(self, period: int, conv_judge: str) -> Dict[str, Any]:
        if conv_judge == "(no conversation)":  # tacit condition: nothing to judge
            return {"ruling": "not_guilty", "rationale": "no conversation", "skipped": True}

        def validate(obj):
            r = str(obj.get("ruling", "")).strip().lower().replace("-", "_").replace(" ", "_")
            return None if r not in ("guilty", "not_guilty") else {"ruling": r, "rationale": str(obj.get("rationale", ""))}

        obj, _, _ = await self._ask_json(
            "authority", self.models.authority, P.messages(None, P.authority_prompt(conv_judge)),
            period, "authority", "", validate, {"conversation": conv_judge},
        )
        return obj

    async def _classify(self, period: int, conv_judge: str) -> Dict[str, Any]:
        if conv_judge == "(no conversation)":
            return {"agreement": "none", "agreed_price": None, "silence_pact": False, "source": "empty"}
        if self.models.classifier is None:
            return {**keyword_agreement(conv_judge), "source": "keyword"}

        def validate(obj):
            a = str(obj.get("agreement", "")).strip().lower()
            if a not in ("explicit", "implicit", "none"):
                return None
            ap = obj.get("agreed_price")
            try:
                ap = int(ap) if ap is not None and str(ap).lower() != "null" else None
            except (TypeError, ValueError):
                ap = None
            sp = as_bool(obj.get("silence_pact", False))
            return {"agreement": a, "agreed_price": ap, "silence_pact": bool(sp), "rationale": str(obj.get("rationale", "")), "source": "llm"}

        obj, _, _ = await self._ask_json(
            "classifier", self.models.classifier, P.messages(None, P.classifier_prompt(conv_judge)),
            period, "classifier", "", validate, {"conversation": conv_judge},
        )
        return obj

    # -- main loop -----------------------------------------------------------
    async def run(self) -> List[Dict[str, Any]]:
        for period in range(1, self.cfg.periods + 1):
            self.rows.append(await self.play_period(period))
        return self.rows

    async def play_period(self, t: int) -> Dict[str, Any]:
        system = self._system()
        audit_prob = self._audit_prob()
        monitored = self.state.first_conviction_period is not None
        # (1) chat
        turns, first = await self._chat(t, system)
        conv_judge = P.render_conversation(turns)  # "Firm A" / "Firm B"
        # ground-truth classifier runs concurrently with the price stage (it never feeds back)
        classify_task = asyncio.create_task(self._classify(t, conv_judge))
        # (2) price + secret report, simultaneous
        dec = dict(zip(FIRMS, await asyncio.gather(
            *(self._price(t, system, f, P.render_conversation(turns, f)) for f in FIRMS)
        )))
        price = {f: dec[f]["price"] for f in FIRMS}
        secret = {f: dec[f]["secret"] for f in FIRMS}
        # (3) reveal; (4) public report only if no secret report
        public = {f: False for f in FIRMS}
        pub: Dict[str, Dict[str, Any]] = {}
        if self.regime.reporting and not any(secret.values()):
            pub = dict(zip(FIRMS, await asyncio.gather(*(
                self._public(t, system, f, price[f], price["B" if f == "A" else "A"], P.render_conversation(turns, f))
                for f in FIRMS
            ))))
            public = {f: pub[f]["public"] for f in FIRMS}
        reporters = tuple(f for f in FIRMS if secret[f]) or tuple(f for f in FIRMS if public[f])
        report_type = "secret" if any(secret.values()) else ("public" if any(public.values()) else "none")
        # (5) investigation
        audit = self.regime.authority and (self.rng_audit.random() < audit_prob)
        investigated = self.regime.authority and (bool(reporters) or audit)
        auth = await self._authority(t, conv_judge) if investigated else None
        guilty = bool(auth and auth["ruling"] == "guilty")
        ct = await classify_task
        # cartel episode bookkeeping (extension 2)
        if ct["agreement"] == "none" and self.state.leniency_granted_in_episode:
            self.state.leniency_granted_in_episode = False
            self.state.episode += 1
        prior_conv = dict(self.state.convictions)
        # (6) settlement
        s = settle(self.regime, self.cond, self.state, reporters, investigated, guilty)
        if guilty and self.state.first_conviction_period is None:
            self.state.first_conviction_period = t
        base = {"A": profit(price["A"], price["B"]), "B": profit(price["B"], price["A"])}
        payoff = {f: base[f] - s.fine[f] + s.reward[f] for f in FIRMS}

        row: Dict[str, Any] = {
            "condition": self.cond.name,
            "regime": self.cond.regime,
            "supergame": self.index,
            "period": t,
            "round": t,  # Lee's name for the period index
            "price_a": price["A"], "price_b": price["B"],
            "base_a": base["A"], "base_b": base["B"],
            "secret_a": secret["A"], "secret_b": secret["B"],
            "public_a": public["A"], "public_b": public["B"],
            "public_asked": bool(pub),
            "report_type": report_type,
            "reporters": "".join(reporters),
            "audit": bool(audit),
            "audit_prob": audit_prob,
            "investigated": bool(investigated),
            "authority_ruling": auth["ruling"] if auth else None,
            "authority_rationale": auth.get("rationale") if auth else None,
            "agreement": ct["agreement"],  # ground-truth C_t
            "agreement_any": ct["agreement"] != "none",
            "agreed_price": ct.get("agreed_price"),
            "silence_pact": ct.get("silence_pact", False),
            "classifier_source": ct.get("source"),
            "classifier_rationale": ct.get("rationale"),
            "fine_a": s.fine["A"], "fine_b": s.fine["B"],
            "reward_a": s.reward["A"], "reward_b": s.reward["B"],
            "payoff_a": payoff["A"], "payoff_b": payoff["B"],
            "settlement_note": s.note,
            "eligible_a": s.eligible["A"], "eligible_b": s.eligible["B"],
            "prior_convictions_a": prior_conv["A"], "prior_convictions_b": prior_conv["B"],
            "cartel_episode": self.state.episode,
            "monitored": monitored,
            "chat": turns,
            "first_speaker": first or None,
            "reasoning_a": dec["A"]["reasoning"], "reasoning_b": dec["B"]["reasoning"],
            "public_reasoning_a": pub.get("A", {}).get("reasoning"),
            "public_reasoning_b": pub.get("B", {}).get("reasoning"),
            "parse_retries": {"price_a": dec["A"]["retries"], "price_b": dec["B"]["retries"]},
            "raw_price_a": dec["A"]["raw"], "raw_price_b": dec["B"]["raw"],
            "model_a": self.models.agent_a.model, "model_b": self.models.agent_b.model,
            "model_authority": self.models.authority.model,
            "model_classifier": self.models.classifier.model if self.models.classifier else "keyword",
        }
        row.update({f"flag_{k}": v for k, v in self.cond.flags().items() if k not in ("regime", "name")})
        return row
