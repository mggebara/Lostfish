# Decisions log

Append-only. One entry per change that affects play strength, architecture, or scope. Format: date, change, measurement, decision.

## 2026-10-19 — Seed

- Language: Python orchestration over Stockfish/Lc0 subprocesses. Rust only after profiling. See PLAN.md §3.
- Engine is a UCI engine; local matches via fastchess; Lichess via lichess-bot. No custom runner.
- First victims: the Lichess bot field (bullet/blitz). Stockfish/Lc0 full strength is Phase 5.
- Core metric: score vs. a fixed local field at equal node budget, LostFish minus plain Stockfish.
