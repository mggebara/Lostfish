# LostFish — Development Plan

An adversarial chess engine. It does not try to play the best move. It tries to steer the game into positions its specific opponent misjudges, while never falling outside a safety margin that a strong engine (Stockfish) certifies.

Name: **LostFish**. Package: `lostfish`.

---

## 1. Thesis

Every engine has a search horizon and an evaluation function, and both have systematic errors. Against a *known* opponent you do not need to play minimax (assume the best reply); you can play against the opponent's *actual* policy. Among moves that are all roughly equal by deep analysis, pick the one whose consequences the opponent is least likely to see.

Three ideas carry the project:

1. **Certified candidates.** Stockfish (deep, MultiPV) produces a set of moves within a tolerance of the best move. LostFish only ever picks from this set, so it can never blunder more than the tolerance.
2. **Exploit search instead of minimax.** For each candidate, predict the opponent's reply using a *model of that opponent* (not best play), then evaluate the resulting position deeply. Choose the candidate with the best outcome against the *predicted* reply. This is the chess form of the "victim-play" idea from the adversarial Go attack (Wang et al., ICML 2023).
3. **Opponent models from public data.** Lichess bot games are public. Fingerprint each bot's effective search depth and position-type weaknesses from its game history, and use that as the opponent model. Start with "Stockfish at the fingerprinted depth" as the model; learn a better one later.

## 2. Non-goals (for now)

- Beating full-strength Stockfish or Lc0 from the starting position. Stretch goal, Phase 5.
- Writing our own search, move generator, or evaluation. Stockfish does the chess; LostFish does the steering.
- Playing humans. Lichess BOT accounts may play humans, but every metric here is vs. engines.

## 3. Key decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Primary language | Python 3.11+ | All heavy work happens inside Stockfish/Lc0 (C++) subprocesses. Python's overhead per move is ~1–5 ms, irrelevant next to a 300 ms search. Training code is Python regardless. |
| When to add Rust | Only if profiling shows feature extraction or game orchestration above ~10% of per-move time | Use PyO3 for a hot path, not a rewrite. Expected: never needed before Phase 4. |
| Engine interface | LostFish is itself a **UCI engine** | Then it plugs into `lichess-bot`, `cutechess-cli`/`fastchess`, and any GUI with zero glue. |
| Chess library | `python-chess` | UCI client, board, PGN, Syzygy probing all included. |
| Local match runner | `fastchess` (or `cutechess-cli`) | Parallel, battle-tested, produces PGN + SPRT stats. Do not write a game runner. |
| Lichess bridge | `lichess-bot` (github.com/lichess-bot-devs/lichess-bot) | Handles challenges, clocks, reconnects, and auto-challenging other bots (matchmaking). |
| Certifier engine | Stockfish (latest stable), NNUE, Threads=1 per instance | Deterministic with fixed nodes; easy to run many instances in parallel. |
| Tablebases | Syzygy 5-piece locally (~1 GB); 6-piece optional | Ground truth for Phase 1 blind-spot mining and for never botching won endgames. |
| GPU use | Phase 3+ only (opponent-model training) | Phases 0–2 are CPU-only. |

## 4. Architecture

```
                         ┌──────────────────────────────┐
  lichess-bot  ──UCI──►  │           LostFish (UCI)          │
  fastchess    ──UCI──►  │                               │
                         │  1. certify()   ──► Stockfish │  MultiPV, deep, node-limited
                         │  2. model_reply()──► Proxy    │  opponent model (SF @ depth d, later a net)
                         │  3. evaluate()  ──► Stockfish │  deep eval after predicted reply
                         │  4. steer()                   │  score = eval_after_predicted_reply
                         │                               │        + λ · weakness_match(features)
                         │  5. pick argmax within        │
                         │     tolerance; fall back to   │
                         │     best move if unsure       │
                         └──────────────────────────────┘
                                      ▲
                                      │ reads
                         ┌────────────┴─────────────────┐
                         │   Opponent profile store      │
                         │   profiles/<bot>.json         │
                         │   - effective depth (fingerprint)
                         │   - loss clusters by feature  │
                         │   - opening repertoire        │
                         └──────────────────────────────┘
                                      ▲
                                      │ built by
                         ┌────────────┴─────────────────┐
                         │   Mining pipeline (offline)   │
                         │   lichess API → PGN → annotate│
                         │   → fingerprint → cluster     │
                         └──────────────────────────────┘
```

Per-move flow at 3+0 blitz (budgets scale with the clock):

| Step | Call | Budget |
| --- | --- | --- |
| Certify | Stockfish `go nodes N` with `MultiPV=K` | ~300 ms, K=4–6 |
| Model reply | Proxy per candidate (SF at depth d, `go depth d`) | ~15 ms × K |
| Evaluate | Stockfish `go nodes N/4` per resulting position | ~60 ms × K |
| Steer + pick | Python feature scoring | <5 ms |
| **Total** | | **~700 ms** |

Bullet (1+0) uses K=3 and halves every budget. The time manager is the first thing to tune on Lichess.

### Components (one Python package: `lostfish/`)

- `lostfish/uci.py` — UCI front end. Parses `position`, `go`, time controls; emits `bestmove`. Must stay a valid UCI engine at all times (tested).
- `lostfish/engines.py` — pool of Stockfish/Lc0 subprocesses via `python-chess`. Persistent processes; never respawn per move.
- `lostfish/certify.py` — MultiPV search → list of `(move, cp, pv, eval_by_depth)` within tolerance.
- `lostfish/opponent.py` — opponent model interface: `predict_reply(board) -> move distribution`. Implementations: `StockfishDepthProxy`, later `PolicyNetProxy`.
- `lostfish/steer.py` — scores candidates: exploit search result + feature-based weakness match. Owns the tolerance policy (tighter when behind, when the position is sharp, or when the clock is low).
- `lostfish/features.py` — cheap position features (see §6, Phase 2).
- `lostfish/timeman.py` — clock → node budgets.
- `lostfish/profiles.py` — load/save opponent profiles; default "generic bot" profile when the opponent is unknown.
- `mining/` — offline scripts: `fetch_games.py`, `annotate.py`, `fingerprint.py`, `cluster.py`, `build_profile.py`.
- `training/` — Phase 3+: dataset builders and PyTorch training for the opponent policy net.
- `experiments/` — fastchess configs and result notebooks. Every steering change gets a gauntlet.
- `configs/` — `lostfish.yaml` (budgets, tolerance, K), `lichess-bot/config.yml`.
- `tests/` — pytest. UCI conformance, determinism, tolerance invariants, time management.

## 5. Repository layout

```
lostfish/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── configs/
│   ├── lostfish.yaml
│   └── lichess-bot.config.yml.example
├── docs/
│   ├── PLAN.md            (this file)
│   └── DECISIONS.md       (append-only log of decisions + results)
├── lostfish/                  (engine package)
├── mining/
├── training/
├── experiments/
├── profiles/              (generated; committed for known bots)
├── scripts/
│   ├── setup_engines.sh   (download Stockfish, Lc0, Syzygy 5-piece, fastchess)
│   └── run_gauntlet.sh
└── tests/
```

## 6. Phases

Each phase ends with a measurable gate. Do not start the next phase until the gate passes; the gates are what make this a research project instead of a pile of code.

### Phase 0 — Playable passthrough (week 1)

Goal: LostFish is a real UCI engine that plays on Lichess, even though it just forwards Stockfish's best move.

Tasks:
- [ ] `pyproject.toml`, package skeleton, pytest, ruff, pre-commit.
- [ ] `scripts/setup_engines.sh`: fetch Stockfish binary, Syzygy 5-piece, fastchess. Pin versions in `configs/lostfish.yaml`.
- [ ] `lostfish/engines.py`: persistent Stockfish process with `Threads=1`, `Hash` fixed, `MultiPV` settable.
- [ ] `lostfish/uci.py`: full UCI loop. Handle `uci`, `isready`, `ucinewgame`, `position`, `go` (wtime/btime/winc/binc/movetime/nodes/depth), `stop`, `quit`. Identify as `LostFish`.
- [ ] `lostfish/timeman.py` v0: spend `remaining/30 + inc*0.8`, hard cap, bullet floor.
- [ ] Tests: UCI conformance (feed scripted sessions, assert `bestmove`); same position + same nodes → same move (determinism).
- [ ] Local: `fastchess` match LostFish vs Stockfish-same-nodes, 200 games, 3+0 equivalent (`tc=180+0` or node-based). Expect ~50%.
- [ ] Lichess: create a **fresh** account (an account that has ever played a game cannot become a BOT), upgrade to BOT via API, token with `bot:play`. Install `lichess-bot`, point it at LostFish, play 20 games against bots.

Gate: 20 rated bot games on Lichess with no time losses, crashes, or illegal moves. Elo reported.

### Phase 1 — Opponent mining (weeks 2–3)

Goal: for the top ~200 active Lichess bots in bullet/blitz, a profile describing how they fail.

Tasks:
- [ ] `mining/fetch_games.py`: list active BOT accounts (Lichess API `GET /api/bot/online` for online bots; also crawl opponents of known bots), download each bot's rated games as PGN (`GET /api/games/user/{username}`, rate-limited, incremental by `since`). Store as `data/games/<bot>.pgn.zst`.
- [ ] `mining/annotate.py`: for each bot game, run Stockfish at a fixed modest node budget on every position after move 10. Record eval, best move, and the eval trajectory across depths 1..d (iterative deepening gives this in one search). Parallelize across cores; store Parquet.
- [ ] `mining/fingerprint.py`: **effective depth**. For each bot, compute agreement between its actual moves and Stockfish's best move at each depth 1..20. The depth that best predicts the bot's moves (and the residual agreement curve) is the fingerprint. Also fingerprint against Lc0 small nets and Maia for bots that are not Stockfish-like.
- [ ] `mining/cluster.py`: take every position where the bot's move lost ≥ X cp vs. best. Compute `lostfish/features.py` features. Cluster (k-means or HDBSCAN) and report per-cluster blunder rate vs. the base rate. Those clusters are the bot's weak spots.
- [ ] `mining/build_profile.py`: write `profiles/<bot>.json`: effective depth, proxy engine, weak-cluster centroids with uplift, opening lines it plays, draw/resign tendencies. Plus `profiles/_generic.json` aggregated over the whole field.
- [ ] Tablebase disagreement probe: sample 6–7 piece positions from bot games, compare bot moves and shallow Stockfish evals against Syzygy truth. This seeds the feature list with endgame types engines misjudge.

Gate: profiles for ≥100 bots. A held-out test shows the fingerprinted proxy predicts the bot's move better than any single fixed-depth Stockfish (top-1 agreement, measured per bot).

### Phase 2 — Steering v1: exploit search + hand features (weeks 3–5)

Goal: LostFish beats plain Stockfish at an equal node budget against the bot field. This is the core experiment of the project.

Tasks:
- [ ] `lostfish/certify.py`: MultiPV candidates within `tolerance_cp` (default 30 at even positions). Tolerance policy: shrink toward 0 when `|eval| > 150` against us, when eval volatility across depths is high (sharp position), or when the clock is low. Expand slightly when ahead.
- [ ] `lostfish/opponent.py` `StockfishDepthProxy`: predict the reply by searching the candidate position with Stockfish at the fingerprinted depth. Return top-2 replies with weights (from MultiPV at that depth).
- [ ] Exploit search: for each candidate, `expected_eval = Σ w_i · deep_eval(after reply_i)`. Pick the candidate with the highest expected eval. This alone should produce wins: it prefers moves whose refutation the opponent will not find.
- [ ] `lostfish/features.py` v1 (all cheap, all from `python-chess`): locked pawn pairs, pawn rams, open/half-open files, material imbalance class (e.g., R vs 2 minors, Q vs R+minor, opposite-colored bishops), king-zone attackers, mobility differential, passed pawns and their blockade status, phase, and **depth gap** = `eval_deep − eval_shallow` from the eval trajectory (positive means a shallow searcher overestimates itself here).
- [ ] `lostfish/steer.py`: `score = expected_eval + λ · weakness_match`, where `weakness_match` is the profile's uplift for the cluster the resulting position falls in. λ small at first (10–20 cp equivalent); tune on the gauntlet.
- [ ] Opponent identification: `lichess-bot` passes the opponent name via the UCI option `UCI_Opponent`. Load the profile; fall back to `_generic`.
- [ ] Gauntlet: a local field of 10–15 engines mimicking the Lichess population (Stockfish at depths 4–12, Lc0 with small nets at low nodes, Maia 1500/1900, a few open-source engines). `experiments/gauntlet_v1/` with fastchess configs. Run **LostFish vs. field** and **Stockfish-same-nodes vs. field**, ≥500 games each, same openings.

Gate: LostFish's score against the field exceeds plain Stockfish's by a margin with p < 0.05 (fastchess reports this). If it does not, the thesis is wrong at this budget; investigate before adding complexity. Deploy on Lichess regardless and log everything.

### Phase 3 — Learned opponent model (weeks 6–10, GPU)

Goal: replace "Stockfish at depth d" with a policy net that predicts each bot's move better, and learn λ-weights instead of hand-tuning.

Tasks:
- [ ] Dataset: from Phase 1 annotations, (position, bot, move played). Hundreds of thousands of positions per well-known bot; pool the long tail into a generic model with a bot-embedding.
- [ ] Model: start from Maia-style architecture or fine-tune a small Lc0 net; input = board planes + bot embedding; output = move policy + "will blunder within 3 plies" head. Train on the GPU.
- [ ] `PolicyNetProxy` in `lostfish/opponent.py`. Batch all K candidate positions in one forward pass; must stay under 20 ms on GPU, or fall back to the depth proxy.
- [ ] Learn steering weights: logistic regression / small MLP from features of the position-after-our-move to "opponent errs within N plies", per profile. Replace the hand `weakness_match`.
- [ ] Re-run the Phase 2 gauntlet with the learned model. Also measure top-1 move agreement per bot vs. the depth proxy.

Gate: learned proxy beats the depth proxy on held-out move prediction for ≥70% of bots, and the gauntlet margin over plain Stockfish grows.

### Phase 4 — Lichess hardening and operations (ongoing from Phase 0)

- [ ] Time management tuned per time control; never below 50 ms/move in bullet; pondering off at first, on later.
- [ ] Draw/resign policy: never offer a draw; accept only when `eval < −300` for 10 plies; resign only when mated in tablebase or `eval < −900` for 20 plies.
- [ ] Per-opponent opening book: from the profile, pick openings that lead to the bot's weak clusters. Generate with Phase 1 data; store Polyglot `.bin` per bot.
- [ ] Matchmaking: configure `lichess-bot` to challenge bots in the target rating band automatically; prefer bots with profiles.
- [ ] Telemetry: log every move's candidate set, scores, chosen move, and outcome to SQLite. A nightly script re-profiles opponents from new games and reports LostFish's results per opponent and per weak-cluster.
- [ ] A `systemd` unit or Docker Compose for 24/7 operation on the desktop.

### Phase 5 — Stretch: true adversarial training against a fixed victim

Only after Phase 3. This is the original research plan:

- Freeze a victim (Stockfish or Lc0 at a fixed node budget).
- Train an adversary net with reward = wins only, using the victim model inside the adversary's search (victim-play MCTS, as in Wang et al.). Seed from Phase 1 weak-cluster positions. Raise the victim's budget as the win rate stabilizes.
- Expect mostly draws against Stockfish; Lc0 is the closer analogue to the Go attack and the better first victim.
- Report the exploitability curve: win rate vs. victim node budget.

## 7. Core metric and protocol

The only number that matters in Phases 2–3: **score vs. the field at equal node budget, LostFish minus plain Stockfish.** Everything else (Lichess Elo, per-bot results) is supporting evidence, because the Lichess field changes daily.

Protocol for every steering change:
1. Same opening suite (e.g., 8-move book positions, both colors).
2. Same node budgets for LostFish's certifier and the baseline Stockfish.
3. ≥500 games, fastchess with `-sprt` or report the Elo difference with error bars.
4. Record in `docs/DECISIONS.md`: change, result, kept or reverted.

## 8. Performance budget

| Time control | Avg time/move | Certify nodes | K | Proxy depth cap | Target total |
| --- | --- | --- | --- | --- | --- |
| 1+0 bullet | ~1.0 s | 200k | 3 | 8 | 500 ms |
| 2+1 / 3+0 blitz | ~3 s | 600k | 5 | 12 | 1.2 s |
| 5+0 blitz | ~6 s | 1.5M | 6 | 14 | 2.5 s |

Rules of thumb:
- LostFish's own overhead must stay under 10 ms/move. Profile with `cProfile` before optimizing anything.
- Run certifier and evaluator searches on separate Stockfish processes so they can overlap.
- If Python becomes the bottleneck (it should not), move `features.py` to Rust via PyO3. Nothing else is worth porting.

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| Steering never beats plain Stockfish at equal budget | That is a legitimate result. Phase 2 gate is explicit so you find out in week 5, not week 20. |
| The strongest bots are just Stockfish at high depth; no exploitable gap | Target the rating band where the gap exists. Report the exploitability curve by opponent depth; it is the paper-worthy finding either way. |
| Bullet latency on Lichess | Node-based budgets, persistent processes, hard floors; measure time losses from day one. |
| Bot game data is sparse for most bots | Pool into the generic profile with a bot embedding; depth fingerprinting needs only ~50 games. |
| Lichess ToS | BOT accounts are permitted and must be flagged as such; `lichess-bot` does this. Keep API calls within rate limits (the game export endpoint is throttled). |
| Over-engineering | No custom search, no custom runner, no Rust until profiled. |

## 10. First Claude Code session

Paste this as the first prompt after seeding the repo:

> Read CLAUDE.md and docs/PLAN.md. Implement Phase 0 only. Start with `pyproject.toml` and `scripts/setup_engines.sh`, then `lostfish/engines.py` and `lostfish/uci.py` as a Stockfish passthrough, with tests for UCI conformance and determinism. Stop when `fastchess` can play LostFish against Stockfish for 10 games with no errors, and show me the command you used.

Then, in order: Lichess deployment (end of Phase 0), `mining/fetch_games.py`, `mining/fingerprint.py`, and so on down the task list. Keep each session scoped to one or two checkboxes.

## 11. References

- Wang et al., "Adversarial Policies Beat Superhuman Go AIs," ICML 2023. https://arxiv.org/abs/2211.00241
- Tseng et al., "Can Go AIs be adversarially robust?" 2024. https://arxiv.org/abs/2406.12843
- Haque et al., "Stockfish or Leela Chess Zero? A Comparison Against Endgame Tablebases," ACG 2023. https://webdocs.cs.ualberta.ca/~mmueller//ps/2023/ACG_2023_Stockfish.pdf
- McIlroy-Young et al., "Aligning Superhuman AI with Human Behavior: Chess as a Model System" (Maia), KDD 2020.
- lichess-bot: https://github.com/lichess-bot-devs/lichess-bot
- Lichess API (bot endpoints, game export): https://lichess.org/api
- fastchess: https://github.com/Disservin/fastchess
- python-chess: https://python-chess.readthedocs.io
