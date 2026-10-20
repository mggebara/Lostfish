# CLAUDE.md — LostFish

LostFish is an adversarial chess engine: a UCI engine that uses Stockfish to certify a set of safe candidate moves, then picks the candidate most likely to lead a *specific opponent* into positions it misjudges. Read `docs/PLAN.md` before doing anything; it holds the architecture, phases, and gates.

## Non-negotiables

1. **LostFish is always a valid UCI engine.** Every commit must pass `tests/test_uci.py`. If a change breaks UCI, it does not merge.
2. **Never pick a move outside the certified set.** The certifier (Stockfish MultiPV within `tolerance_cp`) bounds the damage steering can do. Steering reorders candidates; it never adds one.
3. **No custom chess search, move generator, or evaluation.** Stockfish/Lc0 do the chess. LostFish does the steering. If you think you need custom search, write it up in `docs/DECISIONS.md` first.
4. **Measure, then change.** Any change to steering, tolerance, or time management gets a gauntlet (`scripts/run_gauntlet.sh`) against the baseline before merging. Record the result in `docs/DECISIONS.md`.
5. **Python first; Rust only after profiling.** Do not port anything to Rust/C unless `cProfile` shows LostFish's own code above 10% of per-move time.
6. **Secrets never enter the repo.** The Lichess token lives in the `LICHESS_BOT_TOKEN` environment variable or an untracked `.env`. `configs/lichess-bot.config.yml` is gitignored; only the `.example` is committed.

## Commands

```bash
# setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
scripts/setup_engines.sh            # downloads Stockfish, Syzygy 5-piece, fastchess into ./engines and ./tb

# quality
ruff check . && ruff format --check .
pytest -q                           # fast tests; mark slow ones @pytest.mark.slow
pytest -q -m slow                   # engine-in-the-loop tests

# play
python -m lostfish.uci                  # run as a UCI engine on stdin/stdout
scripts/run_gauntlet.sh experiments/<name>/config.toml   # fastchess match, writes PGN + summary

# lichess
cd third_party/lichess-bot && python lichess-bot.py -v   # after configuring config.yml
```

## Layout

- `lostfish/` — the engine package. `uci.py` (front end), `engines.py` (subprocess pool), `certify.py`, `opponent.py`, `steer.py`, `features.py`, `timeman.py`, `profiles.py`.
- `mining/` — offline data pipeline: fetch bot games, annotate, fingerprint, cluster, build profiles.
- `training/` — Phase 3+ model training (PyTorch). Not needed before Phase 3.
- `experiments/<name>/` — one directory per gauntlet: config, PGNs, `RESULT.md`.
- `profiles/` — `<bot>.json` opponent profiles. `_generic.json` is the fallback.
- `configs/lostfish.yaml` — all tunables: node budgets per time control, `K`, `tolerance_cp`, λ, engine paths and pinned versions.
- `tests/` — pytest. Keep engine-free tests fast; mark engine tests `slow`.
- `docs/DECISIONS.md` — append-only. Date, change, measurement, decision.

## Conventions

- Python 3.11+, type hints everywhere, `ruff` for lint and format, `pytest` for tests.
- Evals are always **centipawns from LostFish's point of view** once they leave `engines.py`. Convert at the boundary; never pass raw white-relative scores around.
- Stockfish instances: `Threads=1`, fixed `Hash`, node-limited searches (`go nodes N`), never time-limited inside LostFish. Time management converts the clock to nodes in `timeman.py`. This keeps everything reproducible.
- Engine processes are persistent and pooled. Never spawn a process per move.
- Opponent identity arrives via the UCI option `UCI_Opponent` (lichess-bot sets it). Unknown opponent → `_generic` profile. Never crash on a missing profile.
- Log one JSON line per move to `logs/moves.jsonl`: fen, candidates with scores, chosen move, budgets, elapsed ms. This is the telemetry Phase 4 depends on.
- Don't add dependencies casually. Current allowed set: `python-chess`, `pyyaml`, `numpy`, `pandas`/`pyarrow` (mining), `requests` (mining), `torch` (training only).

## Working style for Claude Code sessions

- One or two checkboxes from `docs/PLAN.md` per session. Say which ones at the start.
- Run `pytest -q` before reporting done. If a test needs an engine binary that is not present, skip with a clear reason, don't delete the test.
- When a gate in the plan fails, do not "fix" it by loosening the gate. Report the measurement and propose next steps.
- Prefer small, reviewable commits with the checkbox text as the subject.
