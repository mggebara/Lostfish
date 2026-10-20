# LostFish

An adversarial chess engine. LostFish does not try to play the best move; it tries to steer games into positions its *specific opponent* misjudges, while a strong engine certifies that every move it plays stays within a safety margin of the best one.

LostFish is a UCI engine, so it runs anywhere Stockfish does: Lichess (via `lichess-bot`), `fastchess`/`cutechess-cli`, or a GUI.

- `docs/PLAN.md` — thesis, architecture, phased plan with gates, metrics
- `CLAUDE.md` — conventions and non-negotiables for development sessions
- `docs/DECISIONS.md` — append-only log of changes and their measured effect

## Status

Phase 0 (passthrough engine playing on Lichess) — not started.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
scripts/setup_engines.sh
pytest -q
python -m lostfish.uci
```
