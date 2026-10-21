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

## 2026-10-20 — Phase 2 gauntlet v1: steering with the generic profile LOSES to plain Stockfish

- `experiments/gauntlet_v1` (1,088 games, 4h13m, 0 time losses/illegal moves). Score vs the 8-engine field,
  512 games per seed, identical openings: **LostFish-steer 74.0% vs Stockfish 78.4% (−4.4 pts, ~±4.7 at 95%)**;
  fastchess Elo 152.7±24.2 vs 199.8±25.3 (≈ −47 Elo). Head-to-head 28/64 (43.8%). Per opponent LostFish
  was behind or equal everywhere: d8 −5.5, d10 −7.0, d12 −9.4, d14 −2.3, elo3000 −3.1, elo2600 0.0.
- **Gate failed.** With a generic opponent model (proxy depth 12 for everyone, weak clusters from pooled bots),
  deliberately choosing moves up to 30 cp below Stockfish's best costs more than the predicted-reply exploitation
  gains. Steering chose a non-top move on ~26% of moves with >1 candidate (telemetry).
- Field bug: `SF-n150k` and `SF-n300k` produced identical games/pentanomials ([0,0,55,9,0]); the shared
  `nodes=600000` under `[each]` overrode their per-engine limits, so both were full-strength Stockfish.
  The depth-limited and Elo-limited opponents were correct. Fixed in the variant configs (nodes per engine).
- Decision: do not deploy steering on Lichess yet (bot stays passthrough). Pending decomposition, queued:
  oracle runs (exact-depth opponent model) and variants tolerance=15 cp and λ=0 (pure exploit search).
- Lichess passthrough after 35 rated blitz games: 6 wins, 29 draws, 0 losses.

## 2026-10-20 — Oracle runs: steering loses even with the exact opponent model

- `experiments/oracle_d{8,10,12,14}`: LostFish-steer given `profiles/sf-d{d}.json` (proxy = Stockfish at the
  opponent's exact depth) vs SF-d{d}, Stockfish 19 as matched seed, 64 games per seed per opponent:

  | opponent | LostFish-oracle | Stockfish | diff |
  | --- | --- | --- | --- |
  | SF-d8  | 92.2% | 97.7% | −5.5 |
  | SF-d10 | 84.4% | 90.6% | −6.2 |
  | SF-d12 | 69.5% | 77.3% | −7.8 |
  | SF-d14 | 64.8% | 65.6% | −0.8 |
  | **all** | **77.7%** | **82.8%** | **−5.1 (±6.7)** |

  Head-to-head LostFish vs Stockfish 111/256 (43.4%). 0 time losses / illegal moves.
- **The Phase 2 thesis fails at this budget as implemented**: a perfect depth model does not rescue steering v1.
  Against d8–d12 Stockfish already scores 90–98%, so deviating from its best move can only lose points
  (ceiling effect); against d14, where there is room, the effect is ≈ 0. Suspects, in order: (1) the 30 cp
  tolerance is far too loose for 600k-node evals; (2) winner's curse — picking the max of K noisy 150k-node
  "eval after predicted reply" estimates selects noise; (3) the proxy's reply may not match the opponent's
  actual reply (hash carry-over makes a fixed-depth engine effectively deeper). (3) is measurable offline from
  telemetry + PGNs; (1)/(2) via the queued tolerance=15 and λ=0 variants.
- Decision: steering stays off on Lichess. No new complexity until the decomposition explains the loss.
- Lichess passthrough: 55 rated blitz games, 10 wins, 45 draws, 0 losses, 0 time losses by us.

## 2026-10-20 — Why steering loses: offline decomposition (scripts/proxy_accuracy.py)

Joined telemetry with the oracle PGNs (≈7k LostFish moves per run, 0 chosen-move mismatches):
- **The "oracle" proxy is not an oracle.** Stockfish at the opponent's exact depth (fresh 16 MB hash) predicts
  the opponent's actual reply only 50.7% (d8) / 55.2% (d10) / 59.6% (d12) / 58.7% (d14) top-1, 70–78% top-2.
  The generic d12 proxy does the same (55.3%). Hash carry-over makes a fixed-depth engine effectively deeper and
  less predictable than a cold search at that depth.
- **Predicted gains are fantasy, realised gains are small but real.** When steering deviated (≈20% of moves,
  giving up a median 4 cp / mean 6 cp certified), the proxy predicted +361 cp (d8) … +42 cp (d14) edges;
  realised change in our next certified eval was +14.6 (d8) / +10.3 / +7.7 / +6.2 cp vs +6.1 / +4.2 / +2.5 /
  +1.9 cp for non-deviated moves. Net: deviations gain ≈ +4–8 cp more than passthrough moves at the eval level.
  Classic winner's curse on 150k-node evals of proxy-predicted blunders, but the sign is right.
- **So the −5 pts must come from somewhere steering-independent.** Prime suspect: the certifier searches with
  MultiPV=5 at 600k nodes, and its rank-1 move is weaker than a single-PV 600k search — on *every* move,
  including the ~45% single-candidate passthrough moves. Queued `experiments/gauntlet_v1_tol0`
  (tolerance 0: no steering, same MultiPV=5 search) to measure that cost directly. If tol0 ≈ −5 pts, steering
  is neutral-to-positive and the protocol must compensate MultiPV (e.g. K=3, or certify nodes × MultiPV cost
  factor); if tol0 ≈ 0, the deviations themselves are the loss.

## 2026-10-20 — Variant results at shutdown; steering deployed on Lichess

- `gauntlet_v1_tol15` (complete, 1,088 games): LostFish-steer 77.0% vs Stockfish 80.6% → **−3.6 (±4.7)**.
  Halving the tolerance recovered less than a point of the −4.4 seen at 30 cp, consistent with a loss that is
  mostly *not* proportional to how far steering deviates (i.e. the MultiPV certifier cost).
- `gauntlet_v1_lambda0` interrupted at 209 games (machine shutdown): −1.6 (±10.8), uninformative. Re-run.
- `gauntlet_v1_tol0` (the decisive MultiPV-cost measurement) not started. **Run first next session:**
  `nohup scripts/run_queue.sh experiments/gauntlet_v1_tol0 experiments/gauntlet_v1_lambda0 > logs/queue.log 2>&1 &`
- Lichess: steering switched ON at 07:15 (rendered config `Steering: true`, blitz only). Steering era so far:
  12 rated games, 5 wins, 7 draws, 0 losses (passthrough era: 55 games, 10W 45D 0L). Too few to compare, but
  no time losses and no errors with 3 engines per move under load. Restart with `scripts/run_lichess_bot.sh`.
- Open items: fix the fingerprint depth cap (re-annotate ~50 games/bot at 200k nodes), make `uci.py` emit an
  `info depth/nodes/score/pv` line before `bestmove` (PGNs currently show n=0 for LostFish), build a bot-like
  local field (Maia via Lc0, weak open-source engines), and Phase 3 training on the 549k annotated positions.

## 2026-10-20 — Tolerance-0 run: the MultiPV certifier alone costs ~2 points; 1-ply steering costs ~2 more

- `experiments/gauntlet_v1_tol0` (1,088 games, per-engine node limits fixed): LostFish with tolerance 0
  (MultiPV=5 certify search, never deviates) 78.3% vs Stockfish 80.4% → **−2.1 (±4.7)**, ≈ −29 Elo.
  Summary of the decomposition at 600k nodes vs the same field: tol0 −2.1, tol15 −3.6, tol30 (generic) −4.4,
  oracle depth −5.1. So the equal-nodes protocol charges MultiPV about 2 points, and the 1-ply exploit search
  is itself worth about −2 on top. **Decision:** 1-ply steering is retired as the main idea; every steering
  experiment from now on carries a `LostFish-tol0` seed as the within-run control.
- Next idea (Matthew agreed): **victim-play line search** — continue each exploit line with our best move and
  the opponent model's predicted reply for `steer.line_depth` replies, Stockfish only at the leaf; deviate
  only when the line score beats Stockfish's move by `steer.min_gain_cp`. Implemented (default depth 1 keeps
  old behaviour); variants `configs/variants/line2.yaml`, `line3.yaml`.
- Opponent models that are actually right: `Lc0PolicyProxy` reads a Leela/Maia net's root policy at 1 node
  (~1 ms). Exact for a 1-node Maia opponent; profiles `maia-1100/1500/1900`, `maia1/5/9` (Lichess), `lc0-t1`.
- Ceiling effect: vs Maia-1900 even at 400 nodes, all seeds at 20k nodes win ~100%; win rate cannot show
  steering there (use `scripts/game_length.py`). Lc0 T1-256x10 at 200 nodes is a genuine near-peer for
  Stockfish@20k (calibration 1W 3D) and differently shaped → `experiments/lc0_line_t1_n200` is the key test:
  seeds LostFish-tol0 / line1 / line2 / Stockfish at 20k nodes, same openings.
- Lichess ops lesson: three restarts in one day put the event stream into a 429 loop for 2.5 h (7.5k retries,
  0 games). Rule: restart at most once, then leave it; if rate-limited, stop for 10 min before starting again.

## 2026-10-20 — Line search vs Lc0 near-peer at 20k nodes: steering helps a little, the certifier costs a lot

- `experiments/lc0_line_t1_n200` (640 games, 0 problems): seeds at 20k nodes vs lc0 T1-256x10 @200 nodes,
  64 games each: **Stockfish 78.1%, LostFish-line2 59.4%, LostFish-line1 57.8%, LostFish-tol0 (control) 52.3%**
  (±9.5 each). Seed-vs-seed: Stockfish beats every LostFish variant ~70%.
- Two readings. (1) **Relative to the same certifier, steering is positive**: line1 +5.5, line2 +7.1 over the
  tol0 control (not significant at n=64, but the first positive sign for the mechanism, and 2-ply ≥ 1-ply).
  (2) **The MultiPV certifier is ruinous at low budgets**: the control scores 26 points below plain Stockfish
  at equal nodes (MultiPV=3 at 20k nodes ≈ 7k nodes per line). At 600k the same cost was 2 points.
- Compute actually used per move (telemetry): tol0 24k nodes, line1 30k, line2 55k vs Stockfish's 20k. So
  LostFish is also behind at equal *total* compute. Caveat: with no clock the soft budget was 200 ms and
  26% of line2 moves hit the deadline (candidates skipped); fixed (`NO_CLOCK_FLOOR_MS`), rerun queued as
  `lc0_line_t1_n200_v2`. Telemetry now records `line_depth` and `config` per move.
- Conclusion so far: the architecture "MultiPV certify, then steer" is dominated by plain search at equal
  compute; steering's marginal value is small-positive at best. The next structural change must remove the
  MultiPV tax (single-PV certify for the best move/eval; cheap candidate proposals verified inside the
  exploit lines) before any steering gain can show up in match results.

## 2026-10-20 (late) — Line-search rerun and Maia runs: steering is a small plus, the MultiPV certifier dominates

- `lc0_line_t1_n200_v2` (deadline fixed, 640 games, 0 problems), vs lc0 T1@200, 64 games each:
  Stockfish 78.1%, line2 60.9%, line1 57.0%, tol0 control 56.2%. Pooled with v1 (128 games each):
  control 54.3%, line1 57.4% (+3.1), line2 60.2% (+5.9), Stockfish 78.1% (+23.8 over the control).
  2-ply ≥ 1-ply ≥ control in both runs; the margins are inside ±7 but consistent in sign.
- `maia_line_1900_n400`: ceiling as predicted (all seeds 97.7–100%). Mean plies to win vs Maia:
  Stockfish 96.6, line1 96.9, line2 102.0, control 106.8 → steering wins ~5–10 plies faster than its own
  certifier, but not faster than plain Stockfish. `maia_oracle_{1900,1500}_n1`: 100% for both seeds (no
  information beyond "no harm"); head-to-head Stockfish beats LostFish@20k ~74%.
- Decision: the measured marginal value of the exploit search is small-positive (+3 to +6 points vs its own
  certifier at 20k; ~+0 at 600k) and the MultiPV certifier tax (−24 at 20k, −2 at 600k) swamps it. Next
  structural change, as announced: **certifier v2 without MultiPV** — single-PV search at full nodes for the
  best move/eval (identical to plain Stockfish), a shallow MultiPV for candidate proposals, and a per-candidate
  verification search before certification. The control then equals Stockfish by construction.
- Lichess (steering, since 21:16): 1W 3D 1L; first rated loss (vs CruelKen 3036). Casual mid-band game vs
  RomanticBot2 (2312): win.

## 2026-10-21 — Certifier v2 at 20k vs Lc0 near-peer: clean control equals Stockfish; steering now costs

- `experiments/lc0_v2_t1_n200` (640 games, 0 problems), vs lc0 T1@200, 64 games each:
  **Stockfish 76.6%, v2 control 73.4%, v2 + 2-ply 68.0%, v2 + 1-ply 64.8%** (±9.5). Control vs Stockfish
  head-to-head 50.0%: the single-PV certifier reproduces plain Stockfish as designed (MultiPV tax gone).
- With a strong best move to deviate from, steering is **negative**: line1 −8.6, line2 −5.4 vs the control
  (not significant at n=64, but the sign flipped from the MultiPV runs). Reading: the "+3/+6 over its own
  certifier" seen with MultiPV was mostly the exploit search's extra evaluations repairing a noisy rank-1
  move, not opponent exploitation. Deviating from Stockfish's actual best within 30 cp, with min_gain 10,
  gives up more than the predicted opponent errors return, even with a same-net policy model.
- Open lever before giving up: a stricter deviation policy (small tolerance, large min_gain) — only the few
  lines with a big predicted edge. Measurable offline from this run's telemetry (realised vs predicted gain
  by predicted-edge bin). Final high-budget test running overnight: `experiments/field_v2_600k`.
- Offline analysis of that run (telemetry × PGN, 3,382 predictions): the Lc0 policy proxy predicts the real
  lc0@200 reply **69.7%** top-1 (vs 50–60% for the Stockfish depth proxy). Realised change in our next
  certified eval, non-deviated moves: +6.2 cp (baseline drift). Deviated moves by predicted edge: edge < 20 →
  +3.3 / −4.0 (line1/line2), 20–50 → +2.7 / +3.4, **≥ 50 → +21.7 / +7.4**. Only big-edge deviations beat the
  baseline; small-edge ones lose. Queued `experiments/lc0_v2g50_t1_n200` with `min_gain_cp: 50`
  (variants `v2_line1_g50`, `v2_line2_g50`) to run after the 600k field test.

## 2026-10-21 — Direction: Lc0 as the fixed victim (PLAN §6 Phase 5), agreed with Matthew

- Steering (certify-then-steer within a tolerance) has a non-positive marginal effect in every controlled
  run so far (see entries above); the strict min-gain-50 variant is the last steering test. Matthew agreed
  that focusing on Lc0 as a fixed victim is the best way forward.
- Design (this is the write-up CLAUDE.md rule 3 requires before any custom search):
  1. **Victim**: lc0 + T1-256x10 at a fixed node budget N_v (start 200; Stockfish@20k scores ~77% there),
     Threads=1, fixed hash. Deterministic enough to model exactly by running the same engine.
  2. **Exact victim model**: `Lc0PolicyProxy(nodes=N_v)` — the victim engine itself as the opponent model
     (top-1 = its bestmove; alternates from root visit counts). Costs one victim search per prediction.
  3. **Victim-play search (Stage A, no learning)**: at our nodes, K candidates (Stockfish MultiPV at a
     shallow budget, later a learned proposer); at victim nodes, exactly the victim's move; depth d of our
     moves; leaves scored by Stockfish at the leaf budget. Root choice = max over victim-play lines, still
     gated by the single-PV certifier (never outside the tolerance of Stockfish's minimax best) and a
     min-gain threshold. This generalises `steer.line_value` from a line to a K-ary tree over our moves.
  4. **Measurement**: LostFish-victimplay vs lc0@N_v against Stockfish@B vs lc0@N_v, same openings, matched
     total compute; report the exploitability curve over N_v ∈ {50, 200, 800}.
  5. **Stage B (learning, PLAN Phase 3/5)**: from Stage A games and the 549k annotated positions, train a
     proposer/value net (PyTorch on MPS) that predicts "victim blunders within n plies" and proposes
     trap-setting candidates, replacing Stockfish MultiPV as the candidate source.
- Lichess bot stays on steering=true for data; Lichess is not the measurement for this phase.
