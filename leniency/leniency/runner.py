"""Run conditions x supergames concurrently, write one JSONL row per period.

Layout of ``<out>/``::

    config.json                 the resolved ExperimentConfig
    periods.jsonl               one row per period (all conditions)
    cache.jsonl                 response cache (re-running replays finished calls for free)
    usage.json                  calls / tokens / $ by role, phase and model
    errors.jsonl                supergames that aborted (parse failures); never imputed

Rows are written per *finished supergame*, so ``periods.jsonl`` never holds half a supergame.
Re-running the same command skips finished (condition, supergame) pairs, and the cache makes the
interrupted supergames replay their completed calls without new API spend.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import ExperimentConfig
from .game import ParseFailure, Supergame
from .llm import FatalBackendError, Router


def _done_pairs(path: Path, periods: int) -> Set[Tuple[str, int]]:
    counts: Dict[Tuple[str, int], int] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = (r["condition"], r["supergame"])
            counts[k] = counts.get(k, 0) + 1
    return {k for k, n in counts.items() if n >= periods}


async def run_experiment(cfg: ExperimentConfig, out_dir: Path, quiet: bool = False) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(cfg.to_dict(), indent=2, default=str))
    periods_path = out_dir / "periods.jsonl"
    done = _done_pairs(periods_path, cfg.periods)
    router = Router(out_dir / "cache.jsonl", max_inflight=cfg.max_inflight_calls, seed=cfg.seed)
    jobs = [(c, s) for c in cfg.conditions for s in range(cfg.supergames) if (c.name, s) not in done]
    sem = asyncio.Semaphore(cfg.concurrency)
    write_lock = asyncio.Lock()
    t0 = time.time()
    stats = {"finished": 0, "failed": 0, "skipped": len(done)}

    async def one(cond, s):
        async with sem:
            sg = Supergame(cfg, cond, s, router)
            try:
                rows = await sg.run()
            except ParseFailure as e:
                stats["failed"] += 1
                async with write_lock:
                    with open(out_dir / "errors.jsonl", "a") as f:
                        f.write(json.dumps({"condition": cond.name, "supergame": s, "error": str(e)}) + "\n")
                return
            async with write_lock:
                with open(periods_path, "a") as f:
                    for r in rows:
                        f.write(json.dumps(r, default=str) + "\n")
            stats["finished"] += 1
            if not quiet:
                pa = sum(r["price_a"] + r["price_b"] for r in rows) / (2 * len(rows))
                rep = sum(r["report_type"] != "none" for r in rows)
                conv = sum(r["authority_ruling"] == "guilty" for r in rows)
                print(
                    f"  [{stats['finished'] + stats['failed']}/{len(jobs)}] {cond.name:<28} sg{s:<3} "
                    f"avg price {pa:5.2f}  reports {rep:2d}  convictions {conv:2d}  "
                    f"calls so far {router.usage.total().calls}  {time.time() - t0:.0f}s",
                    flush=True,
                )

    try:
        await asyncio.gather(*(one(c, s) for c, s in jobs))
    except FatalBackendError as e:
        sys.exit(f"fatal backend error: {e}")
    finally:
        usage = router.usage.to_dict()
        usage["supergames_run"] = stats["finished"]
        usage["supergames_failed"] = stats["failed"]
        usage["supergames_skipped_already_done"] = stats["skipped"]
        usage["wall_seconds"] = round(time.time() - t0, 1)
        (out_dir / "usage.json").write_text(json.dumps(usage, indent=2))
    return usage
