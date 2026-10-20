# LostFish

An adversarial chess engine. LostFish does not try to play the best move; it tries to steer games into positions its *specific opponent* misjudges, while a strong engine certifies that every move it plays stays within a safety margin of the best one.

LostFish is a UCI engine, so it runs anywhere Stockfish does: Lichess (via `lichess-bot`), `fastchess`/`cutechess-cli`, or a GUI.

- `docs/PLAN.md` — thesis, architecture, phased plan with gates, metrics
- `CLAUDE.md` — conventions and non-negotiables for development sessions
- `docs/DECISIONS.md` — append-only log of changes and their measured effect

## Status

- **Phase 0 (passthrough engine)** — done. Valid UCI engine; 200-game match vs Stockfish 19 at equal nodes: 50.0%, 0 time losses. Deployed on Lichess as `Lostfish-bot`.
- **Phase 1 (opponent mining)** — pipeline done; 40 bots fetched, profiles built. Depth fingerprint is capped by the 20k-node annotation (see `docs/DECISIONS.md`).
- **Phase 2 (steering v1)** — implemented (`docs/STEERING.md`); gauntlet vs an 8-engine field running. Thesis unmeasured until it finishes.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
scripts/setup_engines.sh
pytest -q
python -m lostfish.uci
```
