# Decisions log

Append-only. One entry per change that affects play strength, architecture, or scope. Format: date, change, measurement, decision.

## 2026-10-19 — Seed

- Language: Python orchestration over Stockfish/Lc0 subprocesses. Rust only after profiling. See PLAN.md §3.
- Engine is a UCI engine; local matches via fastchess; Lichess via lichess-bot. No custom runner.
- First victims: the Lichess bot field (bullet/blitz). Stockfish/Lc0 full strength is Phase 5.
- Core metric: score vs. a fixed local field at equal node budget, LostFish minus plain Stockfish.

## 2026-10-19 — Phase 1 mining v1: profiles exist, depth fingerprint is not yet a measurement

- Pipeline: 40 bots × 300 rated bullet/blitz games (12,012 games, ~24 games/s anonymous), annotated
  at 20k nodes/position (110–170 positions/s on 4 workers), fingerprint → k-means clusters → profiles.
- Gate ("fingerprinted depth predicts held-out moves at least as well as any fixed depth") passes
  nominally: mean held-out agreement 0.500 at fitted depth vs 0.499 at the best single depth (d13),
  14/16 bots ≥ d13. **Not meaningful**: 20k nodes completes only depth 13–14, so 13/16 bots are
  "depth-capped" (agreement still rising at the deepest measured depth). The fitted depth is mostly
  the node limit. maia1/maia5/sargon-1ply have flat curves: Stockfish-at-depth-d is a poor model for them.
- Decision: keep profiles (needed for play) but treat `effective_depth` as a lower bound. Next: re-annotate
  ~50 games/bot at ~200k nodes to resolve depths 15–20 (needs an output-dir option in `mining/annotate.py`),
  and fingerprint human-like bots against Maia instead. Gate not loosened; ≥100-bot requirement still open.
- Weak clusters: strong signal only for mid-rated bots (simpleeval ×2.0 z=13.6, turkjs ×1.75 z=12.0,
  jibbby ×1.8 z=11.4); clusters for 2600+ bots rest on a handful of blunders and are noise.

## 2026-10-19 — Phase 2 experiment design (running)

- `experiments/gauntlet_v1`: seeds LostFish-steer (Steering=true, `_generic`, proxy depth 12) and
  Stockfish 19, both 600k nodes, vs an 8-engine Stockfish field (d8/d10/d12/d14, 150k/300k nodes,
  UCI_Elo 2600/3000), 32 rounds × 2 games per pairing, same openings (8moves_v3, srand 20261019).
  Trivially weak opponents were dropped after a smoke run showed both seeds at ~100% there.
- `experiments/oracle_d{8,10,12,14}`: same, but LostFish is given the exact opponent model
  (`profiles/sf-d*.json`). Tests the thesis with a perfect proxy; if it fails here it fails at this budget.
- fastchess does not send `UCI_Opponent`, so local profiles are selected via the `Profile` option.

## 2026-10-19 — Phase 0 gate (local): passthrough baseline

- `experiments/phase0_passthrough`: LostFish (Steering=false) vs Stockfish 19, both 600k nodes, 8moves_v3
  openings, 100 rounds × 2. Result: 100.0/200 (50.00%), 8 wins, 8 losses, 184 draws; 0 time losses,
  0 illegal moves, 0 crashes. Every colour-reversed pair mirrored, so the wrapper is faithful.
- LostFish's own overhead per move: median 0.3 ms, max 9 ms (telemetry). fastchess `--compliance` 40/40.
- Lichess: Lostfish-bot deployed in passthrough mode, blitz only while the CPU is shared; first 4 rated
  games 1 win 3 draws, no time losses. Kept as the baseline configuration.
