"""Key-free tests: payoffs, settlement rules, prompts, parsing, full mock pipeline.

    python -m pytest -q tests/
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

from leniency import prompts as P
from leniency.analysis import analyze
from leniency.config import (
    REGIMES, Condition, ExperimentConfig, ModelSpec, Models, PostConviction, load_config, with_mock_models,
)
from leniency.game import EnforcementState, settle
from leniency.llm import extract_json, keyword_agreement
from leniency.payoffs import PAYOFF, markup_index, verify_matrix
from leniency.runner import run_experiment

ROOT = Path(__file__).resolve().parents[1]


# ----------------------------- payoffs ------------------------------------ #

def test_matrix_benchmarks():
    v = verify_matrix()
    assert v["formula_mismatches"] == []
    assert PAYOFF[3][3] == 100 and PAYOFF[9][9] == 180
    assert v["pure_nash_equilibria"] == [(3, 3)]
    assert v["joint_profit_max"] == (360, 9, 9)
    assert markup_index(3) == 0 and markup_index(9) == 1


# ----------------------------- settlement --------------------------------- #

def _settle(regime, reporters, guilty=True, investigated=True, cond=None, state=None):
    cond = cond or Condition(regime=regime)
    state = state or EnforcementState()
    return settle(REGIMES[regime], cond, state, tuple(reporters), investigated, guilty), state


@pytest.mark.parametrize("regime,reporters,fine,reward", [
    ("E0", "A", {"A": 0, "B": 0}, {"A": 0, "B": 0}),
    ("E1", "", {"A": 200, "B": 200}, {"A": 0, "B": 0}),
    ("E1", "A", {"A": 200, "B": 200}, {"A": 0, "B": 0}),     # no exemption in E1
    ("E2", "", {"A": 200, "B": 200}, {"A": 0, "B": 0}),      # audit conviction
    ("E2", "A", {"A": 0, "B": 200}, {"A": 0, "B": 0}),
    ("E2", "AB", {"A": 100, "B": 100}, {"A": 0, "B": 0}),
    ("E3a", "B", {"A": 200, "B": 0}, {"A": 0, "B": 200}),
    ("E3b", "A", {"A": 0, "B": 200}, {"A": 400, "B": 0}),
    ("E3b", "AB", {"A": 100, "B": 100}, {"A": 0, "B": 0}),   # reward only to a sole reporter
])
def test_lee_settlement(regime, reporters, fine, reward):
    s, _ = _settle(regime, reporters)
    assert s.fine == fine and s.reward == reward


def test_acquittal_and_no_investigation_cost_nothing():
    s, st = _settle("E3b", "A", guilty=False)
    assert s.fine == {"A": 0, "B": 0} and s.reward == {"A": 0, "B": 0} and st.convictions == {"A": 0, "B": 0}
    s, _ = _settle("E3b", "", investigated=False)
    assert s.fine == {"A": 0, "B": 0}


def test_lee_bounty_is_farmable_every_period():
    st = EnforcementState()
    for rep in "ABAB":
        s, st = _settle("E3b", rep, state=st)
        assert s.reward[rep] == 400 and s.fine[rep] == 0


def test_dissolve_on_conviction():
    cond = Condition(regime="E3b", post_conviction=PostConviction.dissolve_on_conviction(k=2.0))
    st = EnforcementState()
    s1, st = _settle("E3b", "A", cond=cond, state=st)
    assert s1.reward["A"] == 400 and s1.fine == {"A": 0, "B": 200}
    # same episode, B now reports: B is a repeat offender (convicted in period 1) -> no leniency,
    # recidivist fine 2F for both; no reward
    s2, st = _settle("E3b", "B", cond=cond, state=st)
    assert s2.reward == {"A": 0, "B": 0}
    assert s2.fine == {"A": 400, "B": 400}


def test_once_per_episode_resets_on_new_episode():
    cond = Condition(regime="E3b", post_conviction=PostConviction(once_per_episode=True))
    st = EnforcementState()
    s1, st = _settle("E3b", "A", cond=cond, state=st)
    s2, st = _settle("E3b", "B", cond=cond, state=st)
    assert s1.reward["A"] == 400 and s2.reward["B"] == 0 and s2.fine["B"] == 200
    st.leniency_granted_in_episode = False  # what the engine does when C_t == "none"
    s3, st = _settle("E3b", "B", cond=cond, state=st)
    assert s3.reward["B"] == 400


# ----------------------------- prompts ------------------------------------ #

LEGAL_WORDS = re.compile(
    r"report|agreement|illegal|price-fixing|authority|\bfine[sd]?\b|leniency|reward|guilty|convict|cartel|collu|\blaw\b",
    re.I,
)


def _agent_texts(cond):
    reg = cond.regime_spec
    conv = 'You: "x" | Competitor: "y"'
    texts = [
        P.system_prompt(reg, cond).replace(P.LEE_SYSTEM, ""),  # Lee's system text has no legal words
        P.price_prompt(reg, cond, 2, "(h)", conv),
        P.public_prompt(cond, 2, 9, 9, conv),
        P.monitoring_notice(cond, cond.post_conviction, 1, reg, 0.1),
        P.render_history([_row()], "A", cond, 40),
    ]
    return texts


def _row():
    return {"period": 1, "price_a": 9, "price_b": 9, "base_a": 180, "base_b": 180, "fine_a": 0, "fine_b": 200,
            "reward_a": 400, "reward_b": 0, "payoff_a": 580, "payoff_b": -20, "investigated": True,
            "reporters": "A", "report_type": "secret", "authority_ruling": "guilty"}


@pytest.mark.parametrize("regime", ["E1", "E2", "E3a", "E3b"])
@pytest.mark.parametrize("reveal", ["implicit", "explicit", "hidden"])
def test_neutral_framing_has_no_legal_words(regime, reveal):
    cond = Condition(regime=regime, framing="neutral", reveal_reporter=reveal,
                     post_conviction=PostConviction.dissolve_on_conviction())
    for t in _agent_texts(cond):
        assert not LEGAL_WORDS.search(t), t


def test_neutral_and_legal_rules_state_same_numbers():
    for regime in ["E1", "E2", "E3a", "E3b"]:
        # (?<![A-Z]) ignores the digits in "Form R1" / "Form R2"
        nums = lambda f: re.findall(
            r"(?<![A-Z])\d+%?", P.market_rules(REGIMES[regime], Condition(regime=regime, framing=f))
        )
        assert nums("legal") == nums("neutral")


def test_baseline_prompts_are_lee_verbatim():
    cond = Condition(regime="E2")
    assert P.system_prompt(cond.regime_spec, cond).startswith(P.LEE_SYSTEM)
    assert P.price_prompt(cond.regime_spec, cond, 3, "H", "C") == P.LEE_PRICE.format(period=3, history="H", conversation="C")
    assert P.chat_prompt(cond, 3, "H", "C") == P.LEE_CHAT.format(period=3, history="H", conversation="C")
    assert P.public_prompt(cond, 3, 9, 7, "C") == P.LEE_PUBLIC.format(period=3, my_price=9, opp_price=7, conversation="C")


def test_e0_has_no_report_option():
    cond = Condition(regime="E0")
    t = P.price_prompt(cond.regime_spec, cond, 1, "H", "C")
    assert "secret_report" not in t and "SECRET" not in t


def test_reveal_modes():
    r = _row()
    imp = P.render_history([r], "B", Condition(regime="E3b"), 40)
    exp = P.render_history([r], "B", Condition(regime="E3b", reveal_reporter="explicit"), 40)
    hid = P.render_history([r], "B", Condition(regime="E3b", reveal_reporter="hidden"), 40)
    assert "your fine 200" in imp and "your competitor filed" not in imp
    assert "your competitor filed a secret report" in exp and "ruling guilty" in exp
    assert "fine" not in hid and "your payoff -20" in hid


# ----------------------------- parsing ------------------------------------ #

def test_extract_json_variants():
    assert extract_json('{"price": 9}') == {"price": 9}
    assert extract_json('<think>hmm {"x":1}</think>\n```json\n{"price": 7, "secret_report": true}\n```') == {
        "price": 7, "secret_report": True}
    assert extract_json('Sure! {"message": "hi {there}"} bye') == {"message": "hi {there}"}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_keyword_classifier():
    k = keyword_agreement('Firm A: "Let\'s both keep prices at 9 and not report anything." | Firm B: "Deal."')
    assert k["agreement"] == "explicit" and k["agreed_price"] == 9 and k["silence_pact"]
    assert keyword_agreement('Firm A: "I will compete hard."')["agreement"] == "none"


# ----------------------------- pipeline ----------------------------------- #

def _mock_cfg(policy, conditions=None, supergames=2, periods=6):
    cfg = load_config(ROOT / "configs" / "smoke.yaml")
    cfg.supergames, cfg.periods = supergames, periods
    if conditions:
        cfg.conditions = [c for c in cfg.conditions if c.name in conditions]
    return with_mock_models(cfg, *policy.split(","))


def test_mock_pipeline_end_to_end(tmp_path):
    cfg = _mock_cfg("farm")
    usage = asyncio.run(run_experiment(cfg, tmp_path, quiet=True))
    assert usage["supergames_failed"] == 0
    rows = [json.loads(l) for l in (tmp_path / "periods.jsonl").read_text().splitlines()]
    assert len(rows) == len(cfg.conditions) * cfg.supergames * cfg.periods
    by = {}
    for r in rows:
        by.setdefault(r["condition"], []).append(r)
    # E0: no reports, no fines, payoff == base
    assert all(r["report_type"] == "none" and r["payoff_a"] == r["base_a"] for r in by["E0"])
    # E3b + farming: alternating sole secret reporters, each paid 400
    e3b = sorted(by["E3b"], key=lambda r: (r["supergame"], r["period"]))
    assert all(r["report_type"] == "secret" and len(r["reporters"]) == 1 for r in e3b)
    assert all(r[f"reward_{r['reporters'].lower()}"] == 400 for r in e3b)
    # dissolve: the bounty is paid at most once per episode (mock chat always agrees -> one episode)
    for sg in range(cfg.supergames):
        d = [r for r in by["E3b_dissolve"] if r["supergame"] == sg]
        assert sum(r["reward_a"] + r["reward_b"] for r in d) == 400
        assert any(r["monitored"] for r in d)
    # tacit: no chat, never guilty
    assert all(r["chat"] == [] and r["authority_ruling"] != "guilty" for r in by["E2_chat-none"])
    # common random numbers: same audit draws across conditions
    audits = {c: [r["audit"] for r in sorted(v, key=lambda r: (r["supergame"], r["period"]))] for c, v in by.items()}
    assert audits["E2"] == audits["E3b"]
    res = analyze(tmp_path)
    t4 = res["table4"].set_index("condition")
    assert t4.loc["E3b", "farming_index"] == pytest.approx(1.0)
    assert t4.loc["E3b", "sole_switch_rate"] == pytest.approx(1.0)
    assert t4.loc["E0", "delta"] == pytest.approx(1.0)  # mock always prices 9
    assert (tmp_path / "analysis" / "table4.md").exists()


def test_resume_uses_cache(tmp_path):
    cfg = _mock_cfg("collude", conditions=["E2"], supergames=1, periods=3)
    u1 = asyncio.run(run_experiment(cfg, tmp_path, quiet=True))
    (tmp_path / "periods.jsonl").unlink()  # pretend the run crashed before writing
    u2 = asyncio.run(run_experiment(cfg, tmp_path, quiet=True))
    assert u2["total"]["calls"] == u1["total"]["calls"] and u2["total"]["cached"] == u2["total"]["calls"]
    u3 = asyncio.run(run_experiment(cfg, tmp_path, quiet=True))  # already done -> nothing to do
    assert u3["supergames_skipped_already_done"] == 1 and u3["total"]["calls"] == 0


def test_deterred_policy_reacts_to_fines(tmp_path):
    cfg = _mock_cfg("deterred,snitch", conditions=["E2"], supergames=1, periods=4)
    asyncio.run(run_experiment(cfg, tmp_path, quiet=True))
    rows = [json.loads(l) for l in (tmp_path / "periods.jsonl").read_text().splitlines()]
    rows.sort(key=lambda r: r["period"])
    assert rows[0]["price_a"] == 9 and rows[0]["fine_a"] == 200  # B reports, A fined
    assert all(r["price_a"] == 3 for r in rows[1:])  # A reacts to its fine in history
