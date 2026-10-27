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

## 2026-10-21 — Steering thesis closed as negative at 20k–600k nodes; project pivots to the Lc0 victim

- `experiments/field_v2_600k`, stopped at 1,325/1,440 games for a machine shutdown (sample already ±4.7):
  vs the Stockfish field, 264 games per seed: **Stockfish 78.6%, v2 control 75.9%, v2 + 2-ply 74.1%,
  v2 + 1-ply 72.9%**. Head-to-head every seed vs every other: exactly 50.0% — the v2 control is
  Stockfish-equivalent by construction; its 2.7-point gap vs the field is within noise. Steering: −1.8 /
  −3.0 vs the control. Per opponent, steering lost most vs the depth-limited engines (d10, d12).
- Across all controlled runs (two budgets, Stockfish- and Lc0-shaped opponents, depth proxy, exact-depth
  oracle, Maia/Lc0 policy proxy at 70% accuracy, 1-ply and 2-ply victim-play lines, MultiPV and
  single-PV certifiers): steering's marginal effect is 0 to −9 points, never positive. **Conclusion:**
  certify-then-steer within a 30 cp tolerance does not beat plain Stockfish against engine opponents at
  these budgets. The exploitable slack is smaller than the cost of leaving Stockfish's best move.
- Not run (machine shutdown): `lc0_v2g50_t1_n200` (strict min_gain 50) and `lc0_victim_t1_n50` (first
  exploitability point with the exact victim model + victim-play tree). Resume queue, in order:
  `nohup scripts/run_queue.sh experiments/lc0_v2g50_t1_n200 experiments/lc0_victim_t1_n50 > logs/queue.log 2>&1 &`
- Lichess (steering on, 2026-10-20 21:16 → 2026-10-21 08:10): 68 games, 35W 30D 3L; rated top band 6W 29D 3L,
  casual 1500–2500 band 29W 1D 0L. Bot stopped cleanly between games for the shutdown.

## 2026-10-21 — Strict min-gain-50 steering (the last steering test): still negative vs Lc0@200 at 20k

- `experiments/lc0_v2g50_t1_n200`: 20k nodes, round robin of Stockfish, v2 control (tol0), v2 + 1-ply
  line with `min_gain_cp: 50`, v2 + 2-ply line with `min_gain_cp: 50`, and lc0 T1@200 (the opponent the
  Lc0 policy proxy models). 64 games per pairing, 640 total; 0 time losses, 0 illegal moves, 0 crashes.
- vs lc0@200 (±9.5 each, n=64): **Stockfish 78.9%, v2 control 72.7%, line2-g50 68.0%, line1-g50 64.8%**.
  Pooled, steering 66.4% vs controls 75.8% (n=128 each): −9.4, about two standard errors. Head-to-head:
  control vs Stockfish 50.0% (Stockfish-equivalent as designed); the g50 variants scored 54.7% / 54.7% vs
  Stockfish and 53.1% / 53.9% vs the control (n=64, ±12: noise). Note the 6-point gap between the two
  identical engines vs lc0 — that is the noise floor at n=64.
- Telemetry (14k moves per seed): deviations from Stockfish's best on 3.6% (line1) / 6.9% (line2) of
  moves; 88 / 197 ms per move vs 17 ms for the control, i.e. 5× / 11× the compute. The strictest gate we
  have (deviate only when the predicted victim-play edge is ≥ 50 cp, with a 70%-accurate policy proxy)
  still loses to the very opponent it models, and loses more with the deeper line.
- **Decision:** steering is closed as negative; no further certify-then-steer variants. All effort goes
  to the Lc0-victim line (Stage A running: `lc0_victim_t1_n50`, then `lc0_victim_t1_n200`).

## 2026-10-21 — Stage A, first exploitability point: victim lc0 T1@50, exact victim model + 2-ply victim-play tree

- `experiments/lc0_victim_t1_n50`: 20k nodes for us, victim lc0 T1-256x10 at 50 nodes. Seeds: Stockfish, v2 control,
  v2 + 2-ply line `min_gain_cp 50` (1-node policy proxy), and v2 + 2-ply tree (`tree_width 2`, `min_gain_cp 50`)
  with the **exact victim model** (`lc0-t1-n50`: the victim engine itself at its own 50 nodes). 32 games per
  pairing, 320 total; 0 time losses, 0 illegal moves, 0 crashes.
- vs lc0@50 (±13.4, n=32): **Stockfish 95.3%, control 95.3%, tree2-exact 92.2%, line2-g50 84.4%**. Plies to
  decision in won games vs lc0: tree2-exact 109, control 112, line2-g50 120, Stockfish 122. Head-to-head
  pairings all 40–59%, i.e. noise.
- Telemetry (7k moves per seed): tree2-exact deviated from Stockfish's best on 3.7% of moves (264); median
  certified cost 1 cp (max 39), median predicted victim-play edge 90 cp. Cost: **2.06 s per move** on average
  (control 22 ms, ~94×), 3.5 s on deviating moves, max 28.7 s; the exact victim model is ~96% of steering time
  (about 15 victim searches per move). line2-g50: 6.7% deviations, 198 ms per move.
- Reading: the ceiling (a 50-node victim loses ~95% to everything) hides small effects, but nothing points
  to a positive margin. The exact victim model with a 2-ply tree does not outscore the control, and its
  slightly faster wins (109 vs 112 plies) are within noise. At 50 nodes the victim blunders so often that
  Stockfish's minimax already harvests the errors; 94× more compute buys nothing measurable.
- Next: second point at victim @200 (`lc0_victim_t1_n200`, running since 20:31, 160 games), where the victim
  is a near-peer (Stockfish@20k ~77–79%) and the ceiling is gone. Stage B stays gated on a positive Stage A margin.

## 2026-10-21 — Stage A, second exploitability point: victim lc0 T1@200 (16 games per pairing: too noisy, rerun long)

- `experiments/lc0_victim_t1_n200`: as the @50 run but victim at 200 nodes and exact model `lc0-t1-n200`; 8 rounds,
  16 games per pairing, 160 total; 0 time losses, 0 illegal moves, 0 crashes, 0 warnings.
- vs lc0@200 (±19, n=16): **Stockfish 90.6%, control 87.5%, tree2-exact 65.6%, line2-g50 56.2%**. Won games vs
  lc0: tree2-exact 151 plies vs control 119 — slower, not faster. Seed-vs-seed: tree2-exact 62.5% vs the control
  and 53.1% vs Stockfish (n=16, noise).
- Telemetry (3.6k moves): tree2-exact deviated on 2.1% of moves (77); median certified cost 1 cp (max 32), median
  predicted edge 70 cp; **4.8 s per move** (control 18 ms, ~260×), 6.9 s on deviating moves. Realised change in
  our next certified eval after a deviation: **+33.5 cp (n=76) vs +3.2 baseline**; 8 deviations were followed by
  a ≥100 cp gain, none by a ≥100 cp drop. Locally the deviations look profitable while the game score says the
  opposite — the same disconnect seen with min-gain-50 steering. Suspect: the evaluator budgets (leaves at
  `eval_nodes` 5000, certifier 20k, depth ~9–12) are too shallow to be truth against an Lc0 net at 200 nodes, so
  "gains" measured by shallow Stockfish may be evaluation artefacts rather than real advantages.
- Status: the point estimate is −22 vs the control, but ±19 does not exclude a small positive effect and the
  per-move telemetry points the other way. This is a statistics problem, so time helps (Matthew: "time is on our
  side"). **Decision:** rerun long — `experiments/lc0_victim_t1_n200_long`: gauntlet, seeds Stockfish / control /
  tree2-exact vs lc0@200, 100 rounds → 200 games per seed (±5–6 at these score levels), concurrency 5, ~6 h.
  Phase 5a (blind-spot mining, PLAN) starts only if the long run confirms no margin; Stage B stays gated.
- Correction (22:20): fastchess's gauntlet mode also pairs the seeds with each other (1200 games scheduled, half of
  them slow seed-vs-seed games that answer nothing). Killed at game 7 and split into three 2-engine matches, each
  200 games vs lc0@200: `experiments/lc0_long_n200_tree2` (first, ~5 h), `lc0_long_n200_control`, `lc0_long_n200_stockfish`.

## 2026-10-22 — Long N_v=200 point: first positive signal — exact-model tree +5.5 over the control (paired, 200 games)

- `experiments/lc0_long_n200_tree2` and `lc0_long_n200_control`: 200 games each vs lc0 T1@200, identical openings per
  round (same `srand`), 20k nodes, concurrency 5; 0 time losses / illegal moves / crashes in both.
- **tree2-exact 77.0%** (115W 78D 7L) vs **control 71.5%** (93W 100D 7L). Paired by opening: **+5.5 points, SE 2.4,
  95% CI [+0.7, +10.3]**; tree2 did better in 51 openings, the control in 27, same result in 122. By colour: tree2
  80.5% / 73.5% (W/B) vs control 76.0% / 67.0%. The 16-game point (65.6%) was a low outlier, as suspected.
- Telemetry (10.8k moves): 340 deviations (3.1%), median certified cost 0 cp (max 36), median predicted edge 83 cp,
  realised next-eval change +45 cp vs +10.5 baseline, 45 large gains vs 1 large drop. 4.2 s per move (~230× the control).
- Caveats, stated before anyone gets excited: (1) this is the first positive comparison out of roughly a dozen in
  this project, so a p≈0.02 result is compatible with chance after multiple comparisons; (2) the second control
  (plain Stockfish, `lc0_long_n200_stockfish`) is still running — 39 games, 74.4% so far; (3) the gain costs ~230×
  compute per move, so at equal wall-clock it is a loss — the claim is only "the victim is exploitable by a
  certified move choice at fixed nodes", which is the Phase 5 question, not the Phase 2 one.
- **Decision:** replicate before believing it. Queued `experiments/lc0_rep_n200_tree2` + `lc0_rep_n200_control`
  (fresh openings `srand 20261022`, 400 games each, ~7 h) chained after the Stockfish match. Combined paired sample
  600 games → SE ≈ 1.4. Phase 5a (blind-spot mining) is on hold while the replication runs: if it holds, the next
  question is where the gain comes from (deviation moves in telemetry) and how to cut the 230× cost.
- Addendum 02:17 — second control done: `lc0_long_n200_stockfish` **69.8%** (89W 101D 10L, 200 games, clean). Paired
  by opening: tree2 − control **+5.5 [+0.7, +10.3]**; tree2 − Stockfish **+7.2 [+2.4, +12.1]**; control − Stockfish
  +1.8 [−2.1, +5.6] (the two controls are equivalent, as designed). Two independent controls, both beaten with
  intervals clear of zero; replication (`lc0_rep_n200_*`, 400 games each, fresh openings) started 02:10.

## 2026-10-22 07:41 — Paused for a machine shutdown; replication partial; next direction agreed (supervised victim-error predictor, GPU box coming)

- Replication `lc0_rep_n200_tree2` stopped at **355/400 games: 191W 150D 14L = 74.9%** vs lc0@200 (fresh openings,
  `srand 20261022`). The paired control on these openings (`lc0_rep_n200_control`, fast, ~50 min) has NOT run yet, so
  the replication is not yet scored; pair on the rounds tree2 completed. Bot stopped cleanly (SIGINT between games).
- Agreed with Matthew this morning: move toward learning. Plan (supersedes "Phase 5a only if Stage A fails"):
  1. Data: control-vs-lc0@200 games (~300/h at concurrency 5) + existing ~1.7k games; label every victim move with
     Stockfish loss at 100k nodes minus a depth-8 Stockfish baseline loss (isolate victim-specific error). Target 200k.
  2. Model: small conv net on board planes (PyTorch, MPS here), predicting expected victim error; GBM on hand features
     as baseline; gate = held-out AUC clearly above a sharpness-only baseline. This dataset IS the Phase 5a mine.
  3. Steering: score certified candidates by predicted victim error 2–4 plies out; exact model only where the net
     says errors are likely. Gauntlet vs control at matched nodes AND matched wall-clock.
  4. Stage B self-play on Matthew's GPU box (another machine, Claude Code being set up "over the next day or so").
- Resume, in order: (a) `nohup scripts/run_lichess_bot.sh > logs/lichess-bot.log 2>&1 &` (start once);
  (b) `nohup scripts/run_queue.sh experiments/lc0_rep_n200_control > logs/queue_rep.log 2>&1 &`, then pair with
  `lc0_rep_n200_tree2/games.pgn` by Round (snippet in DECISIONS 2026-10-22 01:49 entry's analysis: load by Round+colour);
  (c) start step 1 (write `mining/victim_errors.py`: generate + label) once the control match frees the machine.

## 2026-10-22 19:04 — Replication holds: exact-model victim-play tree is +5.8 ± 1.6 over the Stockfish-equivalent control (555 paired games)

- Replication on fresh openings (`srand 20261022`), vs lc0 T1@200, both at fixed nodes (ours 20k): `lc0_rep_n200_tree2`
  355 games (stopped for the shutdown) **74.9%** (191W 150D 14L) vs `lc0_rep_n200_control` **69.0%** on the same 355
  openings (control's full 400: 171W 207D 22L). Paired: **+5.9, SE 2.1, 95% [+1.9, +10.0]**; tree2 better in 112
  openings, worse in 69.
- Combined with last night's 200 paired games (+5.5): **n=555, +5.8, SE 1.6, 95% [+2.7, +8.9], z=3.6** (p≈0.0003
  two-sided). Against this victim that is roughly +55 Elo over Stockfish at the same node budget.
- What is established: a Stockfish-certified move choice (never outside tolerance of Stockfish's best, median
  certified cost 0 cp) that uses the victim's own search as the opponent model beats Stockfish at equal nodes
  against that victim. This is the Phase 5 claim (victim exploitable at fixed nodes), replicated. The Phase 2 claim
  (beating Stockfish at equal wall-clock against general opponents) remains closed as negative: the gain costs ~230×
  compute per move because the exact model is the victim engine itself.
- Next (per the learning plan agreed this morning): (1) where the gain comes from — telemetry join of deviations to
  game outcomes; (2) cut the cost — the supervised victim-error predictor (labelling running: `logs/label.log`,
  data generation `experiments/gen_lc0_n200_a`); (3) the curve: is the margin larger or smaller at victim@800
  (needs the GPU box for the exact model at 800 nodes)?
- Addendum 19:10 — where the gain sits (telemetry deviations joined to the 555 paired games by FEN; 883/887 matched):
  paired diff by number of deviations in the tree2 game — 0: **−8.1** (n=172, SE 3.0); 1: +2.7 (149); 2: +14.9 (104);
  3: +19.5 (59); 4+: +21.1 (71). Monotone, but NOT clean causal evidence: a deviation happens exactly when the exact
  model predicts the victim is about to err, so "0 deviations" selects games the victim played well (hence the
  negative group) — selection on the victim's play, not an effect of not deviating. The unbiased number stays the
  overall +5.8. A clean side-effect control would be a "shadow" seed (tree2 doing all its searches with
  `min_gain_cp 100000`, never deviating) vs the control: 0.0 expected if the extra searches have no hidden tax
  (hash/time effects). Planned, not queued tonight (machine busy with data generation + labelling).

## 2026-10-22 21:05 — Victim-error predictor v1: lc0@200's blunders are predictable from the board (AUC 0.69, ×3 lift), and are victim-specific

- `experiments/victim_error_v1/RESULT.md`. 118k labelled victim moves (Stockfish 100k-node labels, blunder = expected
  score drop ≥ 0.10, 1.6% of moves), 89.5k distinct positions, split by game. **ResNet 128×8: val AUC 0.692**; 64×6:
  0.685. Lift: the top 5% of positions by predicted risk blunder 5.1% of the time vs 1.6% base (×3.2); top 1% ×5.7.
- **Baselines at chance:** depth-10 Stockfish's loss on the same position has AUC 0.505 — where Lc0 errs is not
  where a conventional searcher errs. Lopsidedness |cp| 0.554. So the error structure is the victim's own, which is
  the premise of the learning direction. Errors concentrate in the middlegame (17–24 pieces: 3% rate; endgames <1%).
- Protocol lesson (recorded for Phase 3 too): deterministic engines replay identical games from shared openings →
  24% exact-duplicate positions; a plain game split leaked a third of validation positions into training (the victim
  repeats its move 94% of the time), inflating AUC 0.65 → 0.67 (0.73 on leaked rows). Dedupe by FEN before splitting.
- Decision — step 3 (steer by predicted error), two seeds vs lc0@200 against the control on matched openings:
  (a) **predictor-gated exact tree**: run the 230×-cost tree only when the predictor says a certified candidate's
  child position is high-risk (threshold ≈ top 15%); expected to keep most of the +5.8 at a fraction of the cost;
  (b) **predictor-only steering**: expected eval = cp + 300·p_blunder(child), existing `_choose` gate (min_gain 20),
  ~2 ms/move; tests whether the learned signal alone steers. Inference: torch on CPU inside the engine, optional
  import (engine runs without torch when `steer.predictor_path` is unset) — a deliberate exception to "torch is
  training-only", for the experiment. Also queued: retrain 128×8 for 60 epochs on all data once labelling pass 2
  (600 generated games) lands.

## 2026-10-22 21:52 — Step 3b, predictor-only steering: exactly 0.0 vs the control (200 paired games)

- `experiments/lc0_long_n200_predsteer` (certified candidates scored cp + 300·P(victim blunders after the move),
  deviate when ≥ 20 cp better than Stockfish's best; predictor = victim_error_v1 128×8, AUC 0.69): **71.5%** vs lc0@200
  (92W 102D 6L), control on the same openings 71.5% → paired **+0.0 (SE 2.6, 95% [−5.1, +5.1])**; vs the exact tree
  on the same openings **−5.5 [−10.6, −0.4]**. Clean run (0 time losses / illegal / crashes).
- Telemetry: deviated on 8.9% of moves (960) at a median certified cost of −2 cp (max 29); 37 ms per move, the
  predictor 6 ms of it. Max predicted risk among the K=3 children had median 0.41: the three near-equal moves lead to
  near-identical positions, so a position-level blunder predictor barely separates them.
- Reading: the learned position-risk signal alone does not steer; the exact model's +5.8 comes from knowing the
  victim's specific reply, not from the general riskiness of the position. Remaining uses of the predictor: as a
  **gate** on when to spend the exact tree (`lc0_long_n200_predgate`, running), and as a feature later. Next cheap
  test of where the exact gain lives: **depth-1 exact** (one victim search per candidate, ~3 per move ≈ 12× the
  control instead of 230×): `experiments/lc0_long_n200_line1exact`, queued after the gate match.
- Addendum 22:27 — 60-epoch retrain of 128×8 on all 159k labels (118k distinct positions): **overfits** — val AUC
  peaks 0.643 at epoch 29, then falls to 0.57 by epoch 60 while train loss drops to 0.37. Also shows split-to-split
  variance of the AUC estimate (0.692 on the earlier split vs 0.643 here, ±0.03). Lesson: early stopping (best
  checkpoint is already what we save) and stronger regularisation; more data matters more than epochs — generate
  on the GPU box. The 30-epoch c128b8 checkpoint (0.692) stays deployed in the gate experiment.

## 2026-10-22 22:53 — Step 3a, predictor-gated exact tree: +3.8 vs control at 17% of the tree's cost (200 paired games)

- `experiments/lc0_long_n200_predgate` (exact tree runs only when the predictor rates a candidate's child position
  ≥ 0.635 risk; otherwise Stockfish's best): **75.2%** vs lc0@200 (112W 77D 11L). Paired on the same openings:
  **+3.8 vs control (SE 2.7, 95% [−1.5, +9.0])**, **−1.8 vs the full tree [−6.3, +2.8]**. Clean run.
- Telemetry (11.2k moves): the gate opened on 10.0% of multi-candidate positions (601), deviations on 0.97% of
  moves (109; the full tree: 3.1%). Cost **738 ms/move** (control 18, full tree 4,246): 17% of the tree's compute
  kept ~70% of its point estimate, and the gated deviations were worth ~3.5 points per 100 vs ~1.6 for the tree's
  unfiltered ones — the predictor picks the deviations that matter, even though it cannot pick the move itself.
- Not significant alone at n=200; the point estimate is consistent with the deviation-count analysis (gain rises
  with deviations). Next: a looser gate (`predictor_gate_threshold 0.45`, roughly the validation median) on the same
  openings to map gain vs cost, queued after `lc0_long_n200_line1exact`; then more games on the best point.

## 2026-10-23 00:05 — Depth-1 exact: +3.5 vs control; the gain-vs-cost curve so far (200 paired games each, same openings)

- `experiments/lc0_long_n200_line1exact` (one victim search per certified candidate, Stockfish eval after the
  predicted reply, min_gain 50): **75.0%** vs lc0@200 (104W 92D 4L). Paired: **+3.5 vs control (SE 2.5, [−1.4, +8.4])**,
  −2.0 vs the 2-ply tree [−6.3, +2.3], −0.2 vs the gated tree [−5.2, +4.7]. Clean run. Deviations on 2.3% of moves,
  median certified cost 0 cp; realised next-eval change after a deviation **+54.8 vs +9.8** baseline. Cost 1,286 ms per
  move (71× the control): the exact model dominates even at depth 1 (~3 victim searches + reply evals).
- Curve so far, all vs the same control on the same 200 openings:

  | seed | paired gain | ms/move | × control |
  |---|---|---|---|
  | 2-ply exact tree (width 2) | +5.5 | 4,246 | 236× |
  | depth-1 exact | +3.5 | 1,286 | 71× |
  | predictor-gated 2-ply tree (gate 0.635) | +3.8 | 738 | 41× |
  | predictor-only steering | +0.0 | 37 | 2× |
  | control | 0 | 18 | 1× |

  Reading: about two-thirds of the gain is available from the first ply of exact prediction, and the predictor gate
  gets the same two-thirds at 60% of depth-1's cost. The second ply of the tree adds the remaining third at 6× the
  cost. Nothing beats Stockfish at equal wall-clock on this hardware; on a GPU where an lc0@200 search is ~15 ms,
  the gated tree would be ~50 ms per move. `lc0_long_n200_predgate45` (looser gate) running since 00:04.

## 2026-10-23 01:34 — Looser gate (0.45): +5.0 vs control, the full tree's gain at 36% of its cost

- `experiments/lc0_long_n200_predgate45`: **76.5%** vs lc0@200 (115W 76D 9L). Paired on the same openings: **+5.0 vs
  control (SE 2.5, 95% [+0.1, +9.9])**, −0.5 vs the full 2-ply tree [−4.9, +3.9], +1.2 vs the tight gate [−3.7, +6.2].
  Clean run. Gate opened on 25% of multi-candidate positions; deviations on 1.45% of moves (tree: 3.1%); **1,535 ms per
  move** (85× the control; the tree 236×).
- Curve (same 200 openings, paired vs the same control): tree2 +5.5 @236× · gate0.45 +5.0 @85× · gate0.635 +3.8
  @41× · depth-1 +3.5 @71× · predictor-only 0.0 @2×. Half of the tree's deviations carry essentially all of its gain,
  and the predictor finds them. Best gain-per-cost point near the full gain: **gate 0.45**.
- Decision: run gate 0.45 vs control long on fresh openings (`experiments/lc0_rep_n200_gate45`, `lc0_rep_n200_control2`,
  `srand 20261023`, 400 games each) to replace the 200-game estimate and test transfer to new openings; ~4 h, overnight.
  Shadow-seed side-effect control still pending (machine time).

## 2026-10-23 05:16 — Gate 0.45 replication on fresh openings: +1.2 (not +5.0); combined +2.5 ± 1.5, about half the full tree

- `experiments/lc0_rep_n200_gate45` vs `lc0_rep_n200_control2` (400 games each, fresh openings `srand 20261023`, clean):
  gate 0.45 **72.8%** (201W 180D 19L) vs control **71.5%** (192W 188D 20L) → paired **+1.2 (SE 1.8, [−2.3, +4.8])**.
  Combined with the first 200 openings (+5.0): **n=600, +2.5 (SE 1.5, 95% [−0.4, +5.4], z=1.7)**. The full tree's
  combined figure is +5.8 (SE 1.6, n=555). The +5.0 was a high draw.
- Telemetry on the fresh openings: gate opened on 26% of multi-candidate positions, deviations 1.56% of moves (the
  tree: 3.1%), 1,594 ms per move. Gain per percentage point of deviations: gate ≈ 1.6, tree ≈ 1.9 — **no evidence
  that the predictor selects higher-value deviations**; the gate cuts cost by suppressing deviations and the gain
  shrinks roughly in proportion. Last night's "the predictor picks the moments that matter" is withdrawn as unproven.
- What stands: the full exact tree +5.8 ± 1.6 (two opening sets). What is open: whether the predictor adds anything
  over a random gate at the same open rate. **Decision:** run the direct control — `steer.predictor_mode: random`
  (gate opens on a random 26% of multi-candidate positions, predictor still loaded for identical timing) vs the same
  fresh openings (`experiments/lc0_rep_n200_gaterand`, 400 games, pairs with control2 and gate45). If random ≈ gate
  0.45, the predictor's in-engine value is nil and the cost lever is simply "deviate less"; the predictor's remaining
  role is offline (Phase 5a-style analysis) and as training signal for a model that predicts the *reply*, not the risk.

## 2026-10-23 07:34 — Random-gate control: the predictor adds nothing in-engine (predictor gate vs random gate +0.5 ± 1.7)

- `experiments/lc0_rep_n200_gaterand` (exact tree on a random share of multi-candidate positions, predictor loaded but
  ignored; fresh openings, 400 games, clean): **72.2%** vs lc0@200. Paired on the same openings: random gate vs control
  **+0.8 (SE 1.9, [−3.0, +4.5])**; predictor gate vs control +1.2 (SE 1.8); **predictor gate vs random gate +0.5 (SE 1.7,
  [−2.8, +3.8])**. The random gate opened less often than intended (16% vs 26% of multi-candidate positions; 0.90% of
  moves deviated vs 1.56%) and still matched the predictor gate within noise.
- Conclusion for step 3: the victim-error predictor (AUC 0.69) has **no measurable in-engine value**, neither as a
  steerer (+0.0 ± 2.6) nor as a gate (+0.5 ± 1.7 over chance). Structural reason: certified candidates lead to
  near-identical positions, and a position-level risk score cannot separate them or pick moments better than a coin
  flip. More games could only resolve an effect too small to matter at 85× cost. **TIME WILL NOT HELP** for the
  predictor-in-engine idea; it is closed. The predictor keeps an offline role (blind-spot analysis, Phase 5a).
- Standing result, unchanged: the full exact 2-ply tree **+5.8 ± 1.6** over 555 paired games (+55 Elo vs Stockfish at
  equal nodes against lc0@200), at ~236× compute because the victim model is the victim engine itself.
- Options recorded for Matthew: (A) GPU box — the exact tree at ~50 ms/move, stronger victims (800+ nodes), the
  regime where the thesis matters; (B) cheaper *exact-ish* model on this machine: the victim at fewer nodes (lc0@25/50/
  100) as a proxy for lc0@200 — if its bestmove agrees ≥ 90% (the victim's own self-agreement on repeated positions is
  94%), most of the +5.8 may survive at a fraction of the cost; measurement started; (C) shadow-seed side-effect
  control; (D) pause steering work here until the GPU box.
- Addendum 08:05 — option (B) measured on 400 labelled positions: lc0 at fewer nodes vs the move the lc0@200 victim
  actually played — @25: 73.8% agreement (401 ms/search), @50: 77.2% (560 ms), @100: 82.2% (814 ms), @200 itself:
  86.5% (1,313 ms). Two findings: (1) the "exact" model is ~87% exact against the victim's in-game move (the victim's
  own game state and Lc0 nondeterminism account for the rest), so the cheaper proxies lose 5–13 points of agreement
  for little saving; (2) on Metal the cost is dominated by a ~350 ms fixed overhead per search, not by nodes — worth
  checking in `Lc0PolicyProxy.root_policy` (a per-call `ucinewgame`/cache clear would explain it). **Option B is
  not promising as a model change**; the overhead, if removable, is a 2–3× speed-up of the exact tree here.
- Addendum 08:10 — overhead checked: `Lc0PolicyProxy.root_policy` issues no per-call `ucinewgame`; the cost is per
  GPU dispatch on Metal with Threads=1 (≈ 5–15 ms per node evaluation, 25 nodes ≈ 400 ms, 200 nodes ≈ 1.3 s under
  light load). Inherent to the backend, nothing to fix in our code; the CUDA box removes it.

## 2026-10-23 08:45 — Paused for a machine shutdown (GPU box expected tonight)

- Nothing running. Bot stopped on SIGINT mid-game (a few minutes' notice; one game likely forfeited on time). Lichess
  since 10-22 18:12: 111 games, 43W 68D 0L.
- State: exact 2-ply tree **+5.8 ± 1.6** (555 paired games) stands; predictor-in-engine closed (TIME WILL NOT HELP);
  option (B) fewer-node proxy not promising; options (A) GPU box / (C) shadow-seed control / (D) pause are Matthew's call.
- Resume here: `nohup scripts/run_lichess_bot.sh > logs/lichess-bot.log 2>&1 &` (once). Optional idle-time job:
  shadow-seed control (tree2 with `min_gain_cp: 100000` vs the control on matched openings). GPU box: `docs/GPU_BOX.md`.

## 2026-10-25 20:50 — GPU box online (WSL2 Ubuntu 24.04, RTX 3070 Ti): exact tree 509 ms/move at n200, ~8× the Mac, not 28×; lc0 cost is per-search latency; VRAM caps concurrency

- Setup (docs/GPU_BOX.md §0–1): Windows 11, WSL 3.0.3, Ubuntu-24.04 installed today (only docker-desktop existed), driver
  610.74, hardware GPU scheduling already on. CUDA 12.9 `cuda-nvcc`/`cudart-dev`/`libcublas-dev` from NVIDIA's wsl-ubuntu
  repo suffice; lc0 v0.32.1 built from source (the project ships no Linux binaries). Stockfish 19 (sf_19 renamed its
  Linux assets to `*-universal.tar.gz`; `setup_engines.sh` fixed), fastchess 1.8.2-alpha, Syzygy 3-4-5, 8moves_v3,
  the T1 net. `pytest -q`: 195 passed, 1 skipped. Python 3.12; torch not installed (jobs 1–4 do not need it).
- lc0 T1-256x10, cuda-fp16, Threads=1: a fresh 200-node search ≈ **70 ms**, 800 nodes ≈ 112 ms (10-position benchmark
  totals 691 / 1,161 ms; the Mac's Metal: ~1,300 ms at 200). Forward pass 2.0 ms at batch 1–8, 2.7 ms at 32, 7.1 ms at
  128: a 200-node search is ~30 tiny batches, launch/sync-bound. No search knob moves it (Threads 2, MinibatchSize 8/32,
  max-collision-events 32: all within ±5%); fp32 is 2× slower; the Windows-native lc0.exe cuda12 build is identical
  (679 / 1,122 ms), so it is not a WSL artefact — the interop option in GPU_BOX §0.5 is dropped. Clocks 1,950 MHz.
- Job 1 speed check (`scripts/speed_check.py`, five middlegame positions after warm-up, 20k nodes): tree2 + lc0-t1-n200
  **median 509 ms, max 699 ms per move** (proxy 360–540 ms of it; single-candidate moves 25–30 ms); with lc0-t1-n800
  median 840 ms, max 1,069 ms. Target ≤ 150 ms missed 3–5×; Mac 4,246 ms → ~8× faster. The remaining lever is running
  the ~8–15 proxy searches per move in parallel lc0 processes (a steering-loop change that also alters tree reuse);
  not needed for fixed-node matches, so not done.
- VRAM: 1,271 MiB per lc0 process by default (cuda backend preallocates for max_batch 1024); `--backend-opts=
  max_batch=256` → **747 MiB**, search unchanged (MinibatchSize stays 256). Applied by a wrapper at /usr/local/bin/lc0
  (`engines/lc0` → it) for LostFish's proxy and explicitly as `BackendOptions` on the victim in the experiment configs.
  Budget ≈ 8 lc0 processes on 8 GB (desktop uses ~1.1 GB): single-lc0 matches at concurrency 6, the tree match at 4.
  GPU utilisation reads 100% at concurrency 6: the box delivers throughput, not per-move latency.
- Mistakes recorded so they are not repeated: writing the wrapper through the `/usr/local/bin/lc0` symlink overwrote
  the compiled binary (re-linked with ninja); `pkill -f 'bash -s'` kills the stdin script itself.
- Decision: job 2 launched 20:49 — `experiments/lc0_n800_{stockfish,control,tree2}` (200 rounds × 2, srand 20261025,
  victim lc0 T1@800 with BackendOptions max_batch=256; the control runs Profile `_generic`, which cannot change its
  moves since it never deviates, and saves one lc0 per game). Queue order Stockfish → control → tree2. Pushing to main
  is blocked until this machine gets GitHub credentials.

## 2026-10-25 21:05 — Ceiling check at victim@800: Stockfish@20k scores 51.4% vs lc0 T1@800 (parity; exploitation regime reached)

- `experiments/lc0_n800_stockfish` (plain Stockfish 19 @20k vs lc0 T1@800, 200 rounds × 2, srand 20261025, Syzygy 5,
  clean: 0 time losses / illegal / crashes; 13 min wall at concurrency 6): **51.4%** (74W 263D 63L), pentanomial
  [7, 28, 116, 45, 4] → SE ≈ 1.4, 95% ≈ [48.7, 54.0]. By colour 54.2% / 48.5% (W/B); decisive games average 140 plies.
- Against lc0@200 the Stockfish-equivalent control scored ~70%; at 800 nodes the victim is at parity with Stockfish@20k.
  GPU_BOX job 2's ceiling condition ("below 50%") is met within noise: from here a paired gain of the tree over the
  control measures exploitation headroom, not faster conversion of a won position.
- Next in the queue: `lc0_n800_control` (running), then `lc0_n800_tree2` (~4 h at concurrency 4). Pair with
  `scripts/pair_matches.py` when both are in.
- Addendum 21:16 — `lc0_n800_control` (v2 tol0 @20k, Profile `_generic`, vs lc0 T1@800, same openings; clean, 13 min):
  **51.6%** (77W 259D 64L), pentanomial [3, 37, 110, 44, 6]. Paired vs the Stockfish match: **+0.2 (SE 1.4, 95% [−2.6,
  +3.1])**, better in 43 rounds / worse in 43 / same in 114 — the two controls are equivalent at 800 nodes as at 200.
  By colour 57.8% / 45.5%. `lc0_n800_tree2` started 21:16 (concurrency 4; 8 lc0 processes, 7.2 GB of 8 GB VRAM, GPU 99%).

## 2026-10-26 01:10 — Exploitability point at victim@800: exact tree +5.0 ± 1.9 over the control (400 paired games); the margin holds while the control falls to parity

- `experiments/lc0_n800_tree2` (v2 + 2-ply victim-play tree, exact model lc0-t1-n800, 20k nodes, vs lc0 T1@800; same
  200 openings as the two controls, srand 20261025; clean: 0 time losses / illegal / crashes; 1h49 at concurrency 4):
  **56.6%** (93W 267D 40L), pentanomial [0, 30, 97, 63, 10]. By colour 62.0% / 51.2% (control 57.8% / 45.5%).
- Paired by opening (`scripts/pair_matches.py`): **tree − control +5.0 (SE 1.9, 95% [+1.3, +8.7], z=2.67)**, better in 74
  rounds / worse in 47 / same in 79; tree − Stockfish **+5.2 (SE 1.8, [+1.7, +8.8], z=2.90)**, 78 / 46 / 76.
- The curve so far (paired gain of the exact tree over the Stockfish-equivalent control, same openings):
  victim@200: +5.8 ± 1.6 (555 games, Mac, control ≈ 70%); victim@800: **+5.0 ± 1.9** (400 games, control 51.6%).
  Making the victim 4× stronger moved the control from ~70% to parity with Stockfish@20k but did not shrink the
  exploitation margin. At parity every point above 50% is exploitation, not faster conversion.
- Telemetry (22.0k moves): 57% of positions had ≥ 2 certified candidates; **387 deviations = 1.76% of moves** (the n200
  tree on the Mac: 3.1%); 1,058 ms per move mean, 791 median, 1,839 for multi-candidate positions, with four games
  sharing the GPU (control ≈ 20 ms → ~50× compute per move here; 236× on the Mac at n200).
- Caveats: one opening set, p ≈ 0.008 two-sided (same multiple-comparison warning as 2026-10-22); the fresh-openings
  replication `lc0_rep_n800_{control,tree2}` (srand 20261027, 200 rounds × 2 each) is queued after tonight's data
  generation and ceiling matches (`~/after_night.sh`). Combined with this set it gives n = 400 rounds, SE ≈ 1.3.
- Decision: the exploitability curve is flat from 200 to 800 nodes against T1. Next on the curve: a stronger net
  (T3-512x15 / BT4-1024x15 at 1,000 nodes), gated on Stockfish@20k's score against it (running tonight).

## 2026-10-26 00:45 — Data at scale: 5,000 control-vs-lc0@200 games in 1h25; labelling running; T3-512x15@1000 beats Stockfish@20k (31% after 120 games)

- `experiments/gen_lc0_n200_gpu_a` (v2 tol0 @20k, Profile `_generic`, vs lc0 T1@200, 2,500 rounds × 2, srand 20261026,
  concurrency 6; clean): 5,000 games in **1h25** (the Mac: ~300 games/h). Control **69.7%**, pentanomial
  [7, 130, 731, 1153, 479], mean game 130 plies — same level as the Mac's control vs lc0@200 (69–71.5%).
- Labelling: `mining/victim_errors.py --workers 4` → `data/victim_errors/lc0-t1-n200_gpu_a.parquet`, ~51 victim moves per
  game at 21 positions/s ⇒ ~255k rows, ~3.3 h (ETA 04:00). Dedupe FENs before any split (24% duplicates last time).
- Stronger-net ceiling: `lc0_t3_n1000_stockfish` interim after 120 games: Stockfish@20k **31.3%** (3W 48L 69D) vs
  T3-512x15x16h@1000 — T3 at 1,000 nodes is the "victim that beats Stockfish@20k" GPU_BOX job 4 asks for (final
  numbers and the BT4 match follow). The T3@1000 point (`experiments/lc0_t3_n1000_{control,tree2}`, profile
  `lc0-t3-n1000`, same openings as its Stockfish match) is queued after the n800 replication (`~/after_night.sh`, starts
  when the BT4 match finishes; the labelling is CPU-only and runs alongside).
- Addendum 01:10 — `lc0_t3_n1000_stockfish` final (400 games, clean, 34 min at concurrency 4): Stockfish@20k **30.5%**
  (7W 230D 163L), pentanomial [28, 104, 64, 4, 0] → SE ≈ 1.2 (≈ −140 Elo); by colour 34.5% / 26.5%. The victim
  ladder vs Stockfish@20k: T1@200 ≈ 30% for the victim, T1@800 ≈ 49%, T3@1000 ≈ 70%. The T3@1000 point stays queued
  (control ~1 h, tree ~1 day at 200 rounds: ~10 s per steered move); shorten it if a day of GPU is too much.
- Addendum 01:30 — `lc0_bt4_n1000_stockfish` (placement, 50 rounds × 2, clean, 17 min at concurrency 3): Stockfish@20k
  **27.0%** (1W 52D 47L), pentanomial [9, 28, 13, 0, 0] → SE ≈ 2.3; by colour 35.0% / 19.0%. BT4@1000 is only a little
  stronger than T3@1000 (30.5 ± 1.2) against Stockfish@20k at ~2× the search cost (1,169 vs 879 MiB VRAM, ~2.4 vs ~1.2 s
  per 1,000-node search under load), so **T3-512x15@1000 is the stronger victim for the next point**; BT4 is parked.
  GPU queue (`~/after_night.sh`) now on `lc0_rep_n800_control` → `lc0_rep_n800_tree2` → `lc0_t3_n1000_control` → `lc0_t3_n1000_tree2`.

## 2026-10-26 03:45 — n800 replication holds: +6.4 on fresh openings; combined exact tree +5.7 ± 1.4 over the control at victim@800 (800 paired games)

- `experiments/lc0_rep_n800_tree2` vs `lc0_rep_n800_control` (fresh openings, srand 20261027, 200 rounds × 2 each,
  victim lc0 T1@800; both clean, 1h49 and 13 min): tree **57.2%** (101W 256D 43L, pentanomial [1, 25, 99, 65, 10]) vs
  control **50.9%** (76W 255D 69L). Paired **+6.4 (SE 2.1, 95% [+2.4, +10.4], z=3.11)**, better in 81 rounds / worse in
  48 / same in 71. By colour: tree 62.8% / 51.8%, control 55.0% / 46.8%.
- Combined with the first set (srand 20261025, +5.0 ± 1.9): **n = 400 rounds (800 games), +5.7 (SE 1.4, 95% [+3.0,
  +8.4], z=4.10)**, p ≈ 4·10⁻⁵ two-sided. Two independent opening sets, both clear of zero.
- The exploitability curve against lc0 T1, paired gain of the exact 2-ply tree over the Stockfish-equivalent control
  at 20k nodes: **victim@200: +5.8 ± 1.6** (555 games; control ≈ 70%); **victim@800: +5.7 ± 1.4** (800 games; control
  ≈ 51%). Flat. Four times the victim's search moved the control from winning to parity and left the exploitation
  margin unchanged: what the tree extracts is not a share of a won position but a victim-specific error the victim's
  own extra search does not remove at 800 nodes.
- Cost at this point: ~1.1 s per move (1.8 s on multi-candidate positions) with four games sharing the GPU, ~50× the
  control; deviations 1.8–2.0% of moves (387 and 432 of ~21.7k). Not a wall-clock engine; the Phase 5 fixed-nodes claim only.
- Next on the curve: T3-512x15@1000, the victim that beats Stockfish@20k (30.5%). `lc0_t3_n1000_control` running
  (fastchess queue), `lc0_t3_n1000_tree2` follows (~10 s per steered move → ~1 day at 200 rounds; Matthew may cut it).

## 2026-10-26 04:10 — Labels at scale: 264k victim moves from 5,000 games (3.0% blunders ≥ 100 cp, 0.02% duplicate FENs); control vs T3@1000 = 31.6%

- `mining/victim_errors.py` over `gen_lc0_n200_gpu_a` (4 workers, Stockfish 100k-node labels, depth-10 baseline): 3h32,
  **264,127 rows → `data/victim_errors/lc0-t1-n200_gpu_a.parquet`** (8.8 MB; `data/` stays untracked). Victim loss
  ≥ 100 cp on **3.03%** of moves (mean clipped loss 15.4 cp); the depth-10 Stockfish baseline loses ≥ 100 cp on 1.28%
  of the same positions. Distinct FENs 264,066 of 264,127: a single run on 2,500 distinct openings has essentially no
  duplicates (the Mac's 24% came from several experiments sharing openings). Still dedupe across files when merging
  with the Mac's 160k rows. Retraining the predictor (torch not installed here yet) is not in this session's scope;
  the data is ready for it and for the Phase 5a blind-spot analysis.
- `lc0_t3_n1000_control` (v2 tol0 @20k vs T3-512x15@1000, same openings as its Stockfish match; clean, 400 games):
  **31.6%** (10W 233D 157L); paired vs Stockfish@20k (30.5%) **+1.1 (SE 1.2)** — the controls are equivalent against
  T3 as well. `lc0_t3_n1000_tree2` started 04:04 at concurrency 3 (6 T3 processes, ~5.3 GB VRAM).

## 2026-10-26 08:12 — pause (GPU box shutting down); docket

**Change.** Paused `experiments/lc0_t3_n1000_tree2` (exact tree, Profile lc0-t3-n1000, vs T3@1000) at the
08:10 autosave: fastchess was sent SIGINT two seconds after the autosave and rewrote `config.json` on exit, so
the saved state is 296 of 400 games (W12 L97 D187 from the tree's side). `games.pgn` holds 313 games: the three
in flight at the pause plus the 159–173 block replayed after the 05:57 Windows Update reboot appear twice by
Round; take the last occurrence per (Round, colour) when pairing.

**Resume.**
`cd experiments/lc0_t3_n1000_tree2 && ../../engines/fastchess -config file=config.json >> run_resume.log 2>&1`
(restarts at game 297; ~70 min at 1.5 games/min with concurrency 3). Then RESULT.md by hand, pair against
`lc0_t3_n1000_control` and `lc0_t3_n1000_stockfish` with `scripts/pair_matches.py`, telemetry ms/move and
deviation counts for `"lc0-t3-n1000"` lines, DECISIONS entry, delete `config.autosave-before-resume.json`.

**Interim, unpaired, not a result.** Tree 35.6 % of 296 games vs T3@1000, against control 31.6 % and
Stockfish@20k 30.5 % on the same openings. Direction matches the n800 points; the paired estimate waits
for the full 400.

**Docket after the T3 run (agreed with Matthew 2026-10-26).** Measure whether cheap raw-net labels predict the
victim's real search blunders before any training run:
1. `Lc0PolicyProxy(nodes=1)` (one batch per position, ~3 ms vs ~70 ms for the 200-node search) over all
   264,127 FENs in `data/victim_errors/lc0-t1-n200_gpu_a.parquet`; report positions/s, agreement of the raw
   top move with the move played at 200 nodes, and AUC + precision@3 % of (a) policy mass on Stockfish's best
   move, (b) cp loss of the raw top move where the parquet gives it, (c) |raw Q − Stockfish eval| as
   predictors of the blunder label, with 95 % intervals.
2. If (1) carries signal: stream ~2 M positions from the Lichess evaluation database
   (`lichess_db_eval.jsonl.zst`, depth ≥ 20, ≥ 2 PVs) and label them the same way, using the DB's PV evals as
   the reference (exact cp loss when the raw top move is among the PVs, censored otherwise); compare blunder
   rate and phase/material distribution with the on-policy rows.
3. Only then a pretrain-on-cheap-labels / fine-tune-on-search-labels run, gated by a gauntlet against the
   current predictor. Batched inference outside lc0 (leela2onnx export) only if the nodes=1 path proves useful
   and too slow.

## 2026-10-26 21:55 — T3@1000 exploitability point: exact tree +4.9 ± 1.7 over the control (z = 2.9)

**Change.** `experiments/lc0_t3_n1000_tree2` finished (400 games, exact tree `v2_tree2_g50.yaml`, Profile
lc0-t3-n1000, vs lc0 T3 512x15 @ 1000 nodes, 8moves_v3 openings, srand 20261025, concurrency 3). Run history:
Windows Update reboot at game ~176, resumed from the game-158 autosave; paused at 296 for a shutdown; resumed
and finished 21:44. 417 games in the PGN, 399 unique (Round, colour) after taking the last replay of each;
one scheduled game has no surviving record. Zero engine errors.

**Measurement (same openings, paired by Round and colour, SE over rounds).**

| vs lc0 T3@1000 | score | W / D / L | paired diff vs tree | 95 % |
|---|---|---|---|---|
| exact tree (Profile lc0-t3-n1000) | 36.6 % | 14 / 265 / 121 | — | — |
| control (tol 0, `_generic`) | 31.6 % | 10 / 233 / 157 | +4.9 ± 1.7 | [+1.6, +8.2], z = 2.89 |
| Stockfish @ 20k nodes | 30.5 % | 7 / 230 / 163 | +6.1 ± 1.7 | [+2.9, +9.4], z = 3.69 |

Context: the same tree gained +5.8 ± 1.6 at T1@200 and +5.7 ± 1.4 at T1@800 (combined 800 games). Against
a net four times larger searched five times deeper, where Stockfish@20k itself scores 30 %, the gain is the
same +5 points. Telemetry (23,612 LostFish moves under this profile, replays included): 266 deviations from
Stockfish's first choice (1.1 %); reasons single_candidate 48 %, fallback_best 18 %, steer 34 %; ms/move
median 961, mean 1,902 — the exact T3@1000 proxy costs ~1 s per move, 6–13× the 150 ms target.

**Decision.** The exploit transfers to the stronger victim at unchanged size; the ceiling moved (36.6 % vs
51–53 % at T1@800) because the victim is stronger, not because steering stopped working. More games would
only narrow the interval; the next levers are proxy cost (the T3 tree is too slow for play) and the
predictor. The cheap-label docket (below, 08:12 entry) is the next measurement.

## 2026-10-26 22:20 — cheap raw-net labels, step 1: the raw policy carries real signal about search blunders (preliminary)

**Change.** `mining/cheap_labels.py` evaluates each unique FEN with the T1 net at one node
(`Lc0PolicyProxy(nodes=1)`: root policy and root Q, no search); `scripts/cheap_labels_report.py` scores the
cheap quantities as predictors of the search label in `data/victim_errors/lc0-t1-n200_gpu_a.parquet`
(264,127 rows, 264,066 unique FENs, label from the 200-node victim and Stockfish@100k).

**Measurement.** Throughput 359 positions/s with 6 workers (735 s for all 264k; median 16 ms per position
per process, i.e. ~4× cheaper per process than the 70 ms 200-node search and ~7× cheaper end to end than
playing and labelling games, which yielded 52 labels/s). Raw top move = move played at 200 nodes 69.9 %;
= Stockfish best 52.1 %. Blunder rate (dWP ≥ 0.10) 1.0 % when the search followed the raw top move
(n = 184,522) vs 2.5 % when it deviated (n = 79,605).

| predictor of dWP ≥ 0.10 (rate 1.45 %) | AUC [95 %] | precision@3 % | lift |
|---|---|---|---|
| policy miss (1 − p_best) | 0.710 [0.701, 0.719] | 4.7 % | 3.2× |
| raw-top cp loss (75 % of rows; see caveat) | 0.843 [0.834, 0.853] | 29.9 % | 23× |
| \|raw Q − cp_best\| | 0.564 [0.554, 0.573] | 0.1 % | 0.1× |
| baseline: depth-10 Stockfish loss | 0.502 [0.493, 0.512] | 1.1 % | 0.8× |
| baseline: \|cp_best\| | 0.544 [0.535, 0.554] | 0.0 % | 0.0× |

For loss ≥ 100 cp (rate 3.03 %): policy miss 0.708, raw-top loss 0.885, value error 0.740 (but \|cp_best\|
alone scores 0.771 there, so the value error adds little beyond eval magnitude), depth-10 loss 0.593.

**Caveat.** The raw-top cp-loss row is partly tautological on this data: the loss is only known when the
top move is Stockfish's best (loss 0) or the move the victim played (then the loss *is* the label).
`mining/cheap_labels_fill.py` is computing Stockfish@100k losses for the 65,268 censored rows (25 %); the
honest number, including the subset where the search deviated from the policy, follows as an addendum.
Policy miss has no such leak.

**Decision.** Signal confirmed for the policy-miss label (AUC 0.71 against baselines at chance), so step 2
(2 M Lichess positions, `mining/lichess_eval.py`, labelling running) proceeds. The training decision waits
for the filled cp-loss numbers and the off-policy comparison.

## 2026-10-26 22:35 — Replicable opponents on Lichess: a short list

**Change.** `mining/bot_registry.py` scans the public bios of online bots (no token) for Lc0/Leela/Maia
setups; output `docs/REPLICABLE_BOTS.md` (table) and `data/bots/registry.json` (every bot seen, raw bio;
untracked). One run sees only the bots online at that moment; rerun with `--merge` on other days.

**Measurement.** 300 online bots, 14 bio hits. Reading them: exactly replicable today are the official Maia
bots `maia1`/`maia5`/`maia9` (public nets, one node; profiles exist) and `MostlyHuman1900` (Maia-1900 plus
opening-explorer openings). `ilovecatgirl` (2904 blitz, 5.4k games) runs Lc0 0.32.1 with BT4 on an M4 Mac
at a time budget, so a fixed-node model is only approximate. `LeelaAlien`/`LeelaTroll` pick deliberately
unexpected moves from BT4 and maia3 (not the engine's move), `Joan_clone`/`Bot5551`/`maia2200_10n` use
private nets, the odds bots are not standard chess, and `FetaCompli` is a Leela net trained against Maia.

**Decision.** The first deployment's opponent set is the Maia bots (exact at one node, cheap) and
MostlyHuman1900; `ilovecatgirl` is the one BT4 target worth a mismatch test. No strong public-net Lc0 bot
at fixed nodes was online in this scan.

## 2026-10-26 23:00 — cheap labels step 1b (addendum): honest numbers after filling the 65k censored rows

**Change.** `mining/cheap_labels_fill.py` evaluated the net's top move with Stockfish@100k for the 65,280 rows
where it was neither Stockfish's best nor the move played (21 positions/s on 3 workers, 52 min). Every
on-policy row now has an exact raw-top loss; `scripts/cheap_labels_report.py` adds the transfer table.

**Measurement (264,127 rows).** Raw-top cp loss as a predictor of the search blunder: AUC 0.824 [0.816, 0.833]
for dWP ≥ 0.10 and 0.829 [0.823, 0.834] for loss ≥ 100; precision@3 % 6.9 % (4.8× lift) and 25.2 % (8.3×).
The 0.843 / 29.9 % in the 22:20 entry were inflated by the leak. Policy miss unchanged at 0.710.
Transfer of the cheap label "raw top move loses ≥ 100 cp":

| rows | P(search blunder, cheap = 1) | P(search blunder, cheap = 0) | AUC raw-top loss |
|---|---|---|---|
| all | 10.9 % [10.4, 11.3] | 0.7 % | 0.824 |
| search followed the raw top move (70 %) | 31.1 % [29.7, 32.4] | 0.3 % | 0.987 |
| search overrode it (30 %) | 4.9 % [4.6, 5.2] | 1.9 % | 0.594 [0.581, 0.607] |

(dWP ≥ 0.10 label; for loss ≥ 100: 29.2 % vs 0.9 % overall, 100 % vs 0.1 % when followed, 8.2 % vs 3.3 %
when overridden, AUC 0.550 when overridden.)

**Reading.** The cheap label is the policy's error, and it is nearly exact for the 70 % of decisions where
200 nodes of search follow the policy. Where the search overrides the policy it carries little (AUC 0.55–0.59,
2.6× ratio): those residual blunders are what search labels are for. Overall a position flagged by the raw net
is 7.5× (dWP) to 9.6× (cp) more likely to be a real blunder than the base rate, which is the enrichment a
gate needs; the exact tree then verifies with the real search.

**Decision.** Pretraining on cheap labels is justified as a *policy-error* model with fine-tuning on search
labels for the residual; the off-policy comparison (Lichess 2 M, running) decides the data mix. Protocol for
the run: train `training/victim_error_model.py` on the cheap-labelled pool, then fine-tune from that
state_dict on the 264k on-policy rows, compare validation AUC with the from-scratch model, and gate on the
predictor-gated tree gauntlet (`lc0_long_n200_predgate` protocol) before any deployment.

## 2026-10-26 23:40 — Priority: the largest net (BT4). Clock gate deferred; certifier ladder and BT4 blind-spot pass queued

**Change (Matthew, 2026-10-26).** The target is overcoming the largest Lc0 net, not a registry of replicable
Lichess bots. BT4-1024x15x32h is the largest released net; BT5 (late 2025) is larger in training but measured
weaker than BT4 at equal nodes (Lc0 FAQ: ~12 Elo at equal nodes, ~50 at short time controls), so BT4 stays the
victim. The queued clocked 3+0 matches (`clock_3m_*`, clock-safety gate for `clock_skip`) were cancelled before
starting and wait for the bot setup; `clock_skip` is inert for fixed-node play and unit-tested.

**Queued tonight (GPU after the Lichess pass).** (1) Certifier ladder `lc0_bt4_n1000_sf{100k,400k,1m}`:
Stockfish@100k/400k/1M vs BT4@1000, 200 games each, same openings as the 27.0 % @20k point — finds the
certify budget at parity, which bounds any exploit (Rule 2). (2) Blind-spot pass 1 with the BT4 net
(`mining/cheap_labels.py --weights BT4`, one node) over the 264k on-policy positions and the 2 M Lichess
positions. Pass 2 (`--nodes 1000`/`4000`, the victim's own search on the flagged shortlist, Stockfish fill
for the losses) follows in the morning: the survival rate of raw-net errors under BT4's search is the
number that says whether the big net has a systematic hole.

## 2026-10-26 23:45 — cheap labels step 2: 2 M Lichess positions labelled by the raw T1 net; pools are comparable

**Change.** `mining/lichess_eval.py` streamed the first 2,000,000 qualifying positions (depth ≥ 20, ≥ 2 PVs)
from `lichess_db_eval.jsonl.zst` (343 s, 3.77 M records read, 65 % kept, 89 MB parquet); `mining/cheap_labels.py`
labelled them with the raw T1 net at 342 positions/s (97 min). `scripts/cheap_labels_offpolicy_report.py`
compares the pools.

**Measurement.**

| | Lichess 2 M (off-policy) | control-vs-lc0@200 games (on-policy, 264k) |
|---|---|---|
| raw top = Stockfish best | 54.5 % [54.4, 54.5] | 52.1 % [51.9, 52.2] |
| raw-top loss ≥ 100 cp | 4.2 % sure … 17.4 % upper bound (14.7 % censored, 13.2 % undecidable) | 7.5 % (exact) |
| phase mix opening / middlegame / endgame | 40 / 33 / 27 % | 14 / 40 / 47 % |
| sure-blunder by phase | 1.4 / 7.7 / 4.0 % | 3.2 / 9.1 / 7.4 % |
| \|cp_best\| median / mean; within 100 cp of equal | 61 / 573; 60 % | 44 / 304; 63 % |

The net errs at a similar rate in both pools once phase is accounted for; the Lichess pool has more openings
(our games start after 16 book plies) and more decided positions (users analyse the interesting ones).

**Decision.** The off-policy pool is fit for pretraining a policy-error model, with the on-policy rows as
validation and fine-tuning data and phase re-weighting if the validation AUC asks for it. Started
`mining/cheap_labels_fill.py` on the 294k censored Lichess rows (Stockfish@100k, ~4 h on 3 CPU workers) so
every pretraining label is exact. The training run waits for the BT4 queue to release the GPU.

## 2026-10-27 02:15 — Certifier ladder: Stockfish@100k is at parity with BT4@1000

**Change.** Ran `lc0_bt4_n1000_sf{100k,400k,1m}` (Stockfish @ 100k / 400k / 1M nodes, Threads 1, Hash 64,
Syzygy 5-piece, vs BT4-1024x15x32h @ 1000 nodes; 200 games each on the 8moves_v3 openings, srand 20261025,
concurrency 3). With the earlier 27.0 % @20k point this locates the Stockfish node budget at which the
certifier matches the victim. The v2 tree points so far certify at 20k nodes (`nodes = 20000` in the tree
configs), a certifier weaker than T3@1000 (30.5 %) and much weaker than BT4@1000 (27.0 %).

**Measurement** (Stockfish score vs BT4@1000; ± is one pentanomial SE; Elo ± is fastchess's 95 %):

| Stockfish nodes | score | Elo | W / D / L | Ptnml(0-2) | wall, 200 games |
|---|---|---|---|---|---|
| 20k (100 games, earlier) | 27.0 ± 2.3 % | −173 ± 41 | 1 / 52 / 47 | [9, 28, 13, 0, 0] | — |
| 100k | 51.0 ± 1.3 % | +7 ± 17 | 18 / 168 / 14 | [0, 11, 74, 15, 0] | 35 min |
| 400k | 55.8 ± 1.2 % | +40 ± 17 | 25 / 173 / 2 | [0, 2, 74, 23, 1] | 42 min |
| 1M | 59.3 ± 1.4 % | +65 ± 20 | 38 / 161 / 1 | [0, 1, 65, 30, 4] | 71 min |

Parity sits at about 100k nodes (log-linear interpolation of the 20k and 100k points puts 50 % near 90k).
Above parity the curve flattens: +4.8 points for 4× the nodes, +3.5 for the next 2.5×, with draws above
80 % in every rung. At 1M nodes Stockfish loses one game in 200 and wins 38.

**Decision.** The BT4 exploitability point certifies at Stockfish@100k (parity, +7 ± 17 Elo), five times
the 20k budget of the T3 points, so Rule 2's damage bound comes from an engine as strong as the victim rather
than a weaker one. 400k is the conservative fallback if the control at 100k shows the tolerance window
admitting moves BT4 punishes. Next on the GPU after the blind-spot passes: the BT4 control (v2, Steering
off, certify 100k) and the BT4 tree point with the exact BT4 proxy, 200 rounds × 2 each on the same
openings; the control measures the per-move cost of a 100k MultiPV certify plus 1000-node BT4 proxy
searches before the tree point commits to it.

## 2026-10-27 05:30 — cheap labels step 2b: the 2 M Lichess labels are exact; the raw T1 net blunders at 7.65 % there, 7.53 % on-policy

**Change.** The Stockfish@100k fill of the 294,910 censored Lichess rows finished (265,942 rows in 2.85 h on
4 workers after a relaunch; 294,880 filled in all, 30 unfillable). The first launch had died at 28,938 rows:
the Lichess evaluation DB contains positions Stockfish refuses (one with eight rooks a side exits with code 1),
and the worker that hit one swallowed every later `EngineTerminatedError` and drained the queue in a minute.
`mining/cheap_labels_fill.py` now reopens the engine and retries once (test in `tests/test_cheap_labels_fill.py`);
the relaunch logged 60 such deaths, all recovered.

**Measurement** (raw T1 net, top-policy move, loss ≥ 100 cp, exact labels):

| | Lichess 2 M (off-policy) | control-vs-lc0@200 games (on-policy, 264k) |
|---|---|---|
| raw-top blunder rate | 7.65 % | 7.53 % |
| by phase: opening / middlegame / endgame | 3.4 / 12.8 / 7.7 % | 3.2 / 9.1 / 7.4 % |
| raw top = Stockfish best | 54.5 % | 52.1 % |

The 4.2–17.4 % interval from the censored labels collapses to 7.65 %, within 0.1 points of the on-policy
rate; openings and endgames match to within 0.3 points and the Lichess middlegames err more often (users
analyse their sharp positions). `training/cheap_dataset.py` therefore keeps all 2 M rows for pretraining.

**Decision.** The pretraining protocol runs as queued (scratch c128b8 on the 264k on-policy rows, then
3 epochs on the 2 M cheap rows, then fine-tuning from that checkpoint), after the BT4 Lichess pass releases
the GPU. The comparison that matters is validation AUC on held-out on-policy games, scratch vs fine-tuned.

## 2026-10-27 05:50 — BT4 blind-spot pass 1: the raw BT4 net errs half as often as T1, and almost only where T1 errs too

**Change.** `mining/cheap_labels.py --weights BT4 --nodes 1` over the 264k on-policy positions (197 pos/s,
22 min, 5 workers) and the 2 M Lichess positions (194 pos/s, 2.9 h). BT4's raw-top loss is exact where the
move is a reference move or coincides with T1's (filled) raw top; the Stockfish fill of the rest is running
(56,772 on-policy rows, then the Lichess rows), so the rates below are on known rows and the pass-2 entry
restates them exact.

**Measurement** (raw net, one node, loss ≥ 100 cp):

| | BT4 raw | T1 raw |
|---|---|---|
| on-policy: raw top = Stockfish best | 57.2 % | 52.1 % |
| on-policy: blunder rate (known rows, 85.7 % of 264k) | 3.21 % | 7.53 % |
| on-policy by phase opening / middlegame / endgame | 1.0 / 3.6 / 3.6 % | 3.2 / 9.1 / 7.4 % |
| Lichess: raw top = best | 61.1 % | 54.5 % |
| Lichess: sure blunders … upper bound | 2.2 % … 12.6 % | 7.65 % (exact) |
| mean policy mass on Stockfish's best | 0.327 | 0.253 |

Overlap on the on-policy pool: BT4's raw top equals T1's on 67.7 % of positions. Where T1's raw top is a
blunder, BT4's is one 40.4 % of the time (the same move 30.7 %); where T1's is not, 0.35 %. That is a 115×
enrichment, and about nine in ten of BT4's raw blunders sit on positions where T1 also blunders.

**Decision.** The big net's raw mistakes are close to a subset of the small net's, which is what a
transferable error model needs: a predictor trained on T1 labels also ranks BT4's raw mistakes. Whether
those mistakes survive BT4's search is pass 2, queued behind the pretraining runs:
`scripts/raw_error_survival.py build` takes every flagged on-policy position (BT4 raw loss ≥ 100 cp) plus
3,000 random known-clean controls, `mining/cheap_labels.py --nodes 1000` plays BT4's own 1000-node search on
them, the Stockfish fill prices the chosen moves, and `report` gives the search-blunder rate per group with
Wilson intervals. The control group is BT4@1000's base blunder rate; a flagged rate several times higher
says the net has holes its search does not close.

## 2026-10-27 06:00 — Pretraining on cheap labels: no measurable gain for the T1 error model

**Change.** The protocol from 2026-10-26 23:00 ran on the GPU box, all three runs with the c128b8
architecture (2.52 M parameters) and the same game split: (1) scratch on the 264k on-policy rows (245,370
after dedupe, 5,000 games, 10 epochs, lr 1e-3; 3 min); (2) the same net on the 2 M cheap Lichess rows
(1,613,084 after the trainer's filters, one position per "game", 3 epochs; 6 min), val AUC 0.740 on its own
task; (3) fine-tune from that checkpoint on the on-policy rows (10 epochs, lr 3e-4, best at epoch 5; 3 min).

**Measurement** (on-policy validation, 37,376 positions from held-out games):

| | scratch | pretrained + fine-tuned |
|---|---|---|
| val AUC, blunder = dWP ≥ 0.10 (1.5 % positives) | 0.680 | 0.686 |
| val AUC, blunder = loss ≥ 100 cp (1,104 positives) | 0.621 | 0.611 |
| precision@3 %, loss ≥ 100 cp (base 3.0 %) | 6.5 % | 6.5 % |

Paired bootstrap of the AUC difference on the loss ≥ 100 cp label (300 resamples of the same validation rows):
−0.010 ± 0.008 (1 SE), 95 % [−0.024, +0.005]. The two label definitions disagree on the sign and neither
difference clears one standard error; the top-3 % shortlist is identical in precision.

**Decision.** More seeds or epochs cannot move this: the effect is bounded at about ±0.01 AUC either way,
below what the predictor-gated tree gauntlet resolves, so pretraining on cheap labels is dropped as a lever
for the T1 error model. The cheap-label pipeline keeps its other job, the blind-spot scan of the big net
(pass 1 above, pass 2 running), where the raw-policy error is the quantity itself and not a proxy. The
predictor's ceiling (0.68 AUC from 5,000 games) is an on-policy data question: more victim games, not more
off-policy positions.

## 2026-10-27 07:50 — BT4 blind-spot pass 2: at 1000 nodes the search keeps the raw net's flagged move 90 % of the time, but the 100k reference cannot price it

**Change.** `scripts/raw_error_survival.py build` took the 13,243 on-policy positions where BT4's raw top
loses ≥ 100 cp (5.0 % of 264k, all exact after the fill) and 3,000 known-clean controls;
`mining/cheap_labels.py --nodes 1000` played BT4's own 1000-node search on each (3 workers, 2.8 pos/s,
median 1.1 s per search, 1.6 h); the Stockfish@100k fill priced the 9,002 chosen moves that had no
reference eval.

**Measurement** (BT4@1000's chosen move, loss against the Stockfish@100k reference):

| | flagged (raw loss ≥ 100) | control (raw loss < 100) |
|---|---|---|
| positions | 13,243 | 3,000 |
| search keeps the raw net's move | 89.7 % | 97.9 % |
| chosen move = Stockfish's best | 4.9 % | 60.2 % |
| loss ≥ 100 cp | 85.3 % [84.7, 85.9] | 1.43 % [1.07, 1.93] |
| win-prob drop ≥ 0.10 | 52.2 % | 1.1 % |
| loss ≥ 100 by phase, opening / middlegame / endgame | 84 / 87 / 84 % | 0.5 / 1.1 / 2.0 % |

**Caveat that blocks the conclusion.** Mixing the two groups by their pool shares implies BT4@1000 loses
≥ 100 cp on 5.6 % of the pool's positions (3.7 % by win-prob drop), more than the T1@200 victim that
actually played them (3.0 % / 1.5 %). That is not credible for a far stronger engine. The reference is the
problem: Stockfish@100k is at parity with BT4@1000 (ladder entry above), so where the two disagree by 100 cp
either may be right, and the label books every disagreement as BT4's error; for T1@200, far below the
reference, the same label is almost always T1's error. Pass 2 therefore measures how policy-dominated
BT4's 1000-node search is (it overrides its raw top on 10 % of flagged positions and 2 % of clean ones), not
yet how often BT4 blunders.

**Decision.** Re-price before concluding. `scripts/deep_recheck.py` searches root and child at
Stockfish@1M (ten times the reference; 59 % against BT4@1000) for 1,500 flagged positions, the 43 control
blunders, 300 clean controls and 1,000 of T1@200's own blunders. The share of 100k losses that hold at 1M,
BT4 against T1, is the real-error rate; the BT4 tree point waits for it, since a hole the reference cannot
price is one the certifier cannot certify either.

## 2026-10-27 08:20 — Deep re-pricing: the 100k reference prices BT4's moves as reliably as T1's; the parity caveat is withdrawn, the rate anomaly is not

**Change.** `scripts/deep_recheck.py` searched root and child at Stockfish@1M (4 workers, 2.2 positions/s,
21 min) for 1,500 flagged BT4@1000 moves, the 43 control blunders, 300 clean controls and 1,000 of T1@200's
own played blunders (189 FEN+move pairs occur in both blunder groups and are counted in each).

**Measurement** (share of 100k losses ≥ 100 cp that are still ≥ 100 cp at 1M):

| | BT4@1000 flagged | T1@200 played |
|---|---|---|
| all | 74.3 % (n 1,563) | 72.6 % (n 1,063) |
| \|cp_best\| ≤ 100 | 93.1 % | 85.6 % |
| 100–300 | 90.3 % | 87.5 % |
| 300–1500 | 67.5 % | 69.3 % |
| > 1500 | 3.8 % | 18.5 % |
| middlegame / endgame | 87 / 60 % | 85 / 65 % |
| win-prob drop ≥ 0.10 at 1M | 51.5 % | 33.2 % |

Label-noise floor: 5.0 % of BT4's 100k-clean control moves lose ≥ 100 cp at 1M, and 3.2 % of the moves
that *are* Stockfish@100k's own best do. The 43 control "blunders" were nearly all in decided positions
(median \|cp_best\| 3000) and 28 % held. Pass-2 rates are the same for both colours (flagged 85.5 / 85.1 %,
control 1.7 / 1.2 % for Black / White), so no POV error.

The caveat of 07:50 is withdrawn in the form stated: the reference confirms BT4's flagged moves at depth at
the same rate as T1's, and better in near-equal positions. What remains unexplained is the rate itself:
BT4@1000's implied ≥ 100 cp rate on T1's game positions (5.6 %, 4.2 % after the 74 % hold) exceeds
T1@200's played rate (3.0 %, 2.2 %), although BT4 raw errs less often than T1 raw (5.0 % vs 7.5 % on this
pool, 4.4 % vs 7.65 % on Lichess, now exact). The suspect is procedure: T1's played-move labels come from
`mining/victim_errors.py`, BT4's from pass 2's search-plus-fill, and T1@200's 200-node search would have to
remove 60 % of its raw blunders where BT4's 1000-node search removes 15 %.

**Decision.** Two checks run before the BT4 tree point: (1) T1's own pass 2 under the identical procedure
(`raw_error_survival.py build` on the exact T1 labels, `cheap_labels.py --nodes 200`, fill, report) gives
T1@200's survival rate; if it is also ~85 %, the `victim_errors` labels are the odd ones and the BT4 result
stands; if it is ~40 %, BT4's search genuinely closes fewer of its policy's holes. (2) `victim_errors.py`
on BT4@1000's own 200 games against Stockfish@100k gives its blunder rate in positions of its own making,
against the 5.6 % on T1's.

## 2026-10-27 08:40 — Correction: pass 2 re-priced the prior's move, not the search's; survival from the games is 29 % for T1@200 and 10 % for BT4@1000

**Change.** `mining/cheap_labels.py` took `raw_top` from `Lc0PolicyProxy.root_policy()`, which returns the
net's prior at any node count: at `--nodes 1000` the search ran (1.1 s per position) but the label was still
the prior's top move. The pass-2 survival (85 %) and "keeps the raw move" (90 / 98 %) figures of 07:50 are
the prior re-priced, and the "anomaly" of BT4@1000 scoring more reference losses than T1@200 was this bug.
Fixed: at N > 1 the labelled policy is the visit distribution with lc0's bestmove strictly on top
(`searched_policy`, test added). Found by labelling BT4@1000's own 200 ladder games with
`mining/victim_errors.py` and comparing the played move with the raw top.

**Measurement** (the victim's actual game move against its raw top; Stockfish@100k reference; loss ≥ 100 cp):

| | T1@200, 264k positions of its games | BT4@1000, 10,462 positions of its games |
|---|---|---|
| raw-top blunder rate | 7.53 % | 2.47 % |
| played-move blunder rate | 3.03 % | 0.37 % |
| played move = raw top: overall / on raw blunders | 69.9 / 22.8 % | 72.4 / 8.5 % |
| survival P(played blunder \| raw blunder) | 29.2 % | 10.5 % |
| survival in near-equal positions (\|cp_best\| ≤ 100) | 11.6 % | 2.7 % |
| P(played blunder \| raw clean) | 0.90 % | 0.12 % |

The 1000-node search closes nine in ten of BT4's raw holes in its own games; the 200-node search closes
seven in ten of T1's. The 1M re-pricing (08:20) stands as a statement about the prior's move: where BT4's
prior is wrong it is wrong by Stockfish's lights at any depth, but the search usually does not follow the
prior there. Positions from T1's games are twice as hard for BT4's prior as its own (5.0 % vs 2.5 % raw
blunders).

**Decision.** Pass 2b re-runs both shortlists with the fixed labeller: T1 at 200 nodes first, whose survival
must land near the game-derived 29 % (the validation of the fix), then BT4 at 1000 nodes (1.6 h). The number
for the BT4 point is the corrected survival on T1's game positions against the 10.5 % in BT4's own games:
it bounds how many reachable positions keep a BT4 error after its search.

## 2026-10-27 09:00 — Pause (box shutdown): pass 2b stopped at 11,520 / 22,882 of the T1 search; resume recipe

**State.** Pass 2b (the fixed labeller on the two shortlists) was stopped cleanly during the T1@200 search
step; `data/cheap_labels/t1_pass2b_n200.parquet` holds the flushed half and `mining/cheap_labels.py --resume`
skips it. Nothing else is running. The BT4 search (1.6 h), both fills and both reports are still to do.

**Resume (GPU box).** `~/pass2b_queue.sh` now passes `--resume`; run
`setsid nohup ~/pass2b_queue.sh > logs/pass2b_queue.log 2>&1 < /dev/null &` from `~/dev/LostFish`. Validation
first: the T1 report's flagged `search_blunder_pct` must land near the game-derived 29 % (entry 08:40). Then
the BT4 report's flagged rate, against 10.5 % in BT4's own games, is the number the BT4 tree point waits for.

**Done today, all pushed.** Certifier ladder (Stockfish@100k at parity with BT4@1000); Lichess fill complete
and exact (raw T1 7.65 %, raw BT4 4.44 %); BT4 blind-spot pass 1 (raw BT4 errs on 5.0 % of T1's game
positions, 2.5 % of its own, nine in ten of them where T1 also errs); pretraining on cheap labels dropped
(no measurable gain); 1M re-pricing (74 % of the prior's flagged losses hold); the pass-2 labeller bug
found and fixed; game-derived search survival 29 % (T1@200) and 10.5 % (BT4@1000).
