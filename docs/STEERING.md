# Steering (Phase 2)

Code: `lostfish/certify.py`, `opponent.py`, `steer.py`, `play.py`. All evals are centipawns from
LostFish's point of view (`engines.py` converts via `pov=`); mates are `±(MATE_CP − n)`.

## Per-move algorithm (`SteeringPlayer.choose`)

1. **Certify.** Certifier engine: `go nodes certify_nodes`, MultiPV = `budget.k`, with the rank-1
   eval trajectory. `tolerance_policy` gives T; candidates are lines with `cp ≥ best − T`, in rank
   order. If best mates, only mates that are no slower pass; if we are getting mated, only best.
2. **Single candidate** → play it (reason `single_candidate`). Out of time or UCI `stop` →
   play best (`fallback_best`, `deadline_hit`).
3. **Exploit search** (`steer.pick_detailed`), best first, then the rest in rank order. For each
   candidate c: push c. If the opponent has no legal moves, eval = +MATE_CP (mate) or 0
   (stalemate). Otherwise the proxy predicts the top `replies` replies with weights; for each
   reply, the evaluator searches `go nodes eval_nodes` (or −MATE_CP / 0 if the reply ends the
   game). `expected_eval(c) = Σ w_i · eval_i`.
4. **Weakness.** `features.extract` on the position after c, from the **bot's** side (the side to
   move, with evals negated to its view, matching how `mining/` builds clusters). z = x / scale;
   nearest centroid by Euclidean distance; if within `weakness_radius · √n_features`,
   weakness = `uplift − 1`, clamped to [−1, `max_weakness`]; else 0. No clusters → 0.
5. **Score and pick.** `score = expected_eval + λ · 100 · weakness` (λ = 0.15, uplift 2.0 adds
   15 cp). Highest score wins; ties go to the better certified rank.
6. Telemetry: per candidate cp/rank/expected_eval/weakness/score/replies; chosen, best, reason
   (`single_candidate | steer | fallback_best | error`), tolerance, proxy depth, per-stage ms.

Proxy depth = `min(profile.effective_depth, budget.proxy_depth_cap)`, recomputed every move.
Engines: certifier (cfg Hash, Syzygy), proxy (16 MB Hash, no Syzygy: it models the bot),
evaluator (cfg Hash, Syzygy). All three are persistent and `Threads=1`.

## Tolerance formula (`certify.tolerance_policy`)

    T = Tmin + (T0 − Tmin) · f_behind · f_vol · f_clock · f_ahead, clamped to [Tmin, 2·T0]
    f_behind = 1 − min(1, −best/150)                for best < 0     (T = Tmin at −150 or below)
    f_vol    = 1 / (1 + V / 100)                    V = max − min of the eval, deepest 4 depths
    f_clock  = 0.5 + 0.5 · clock / 0.15             for clock_fraction < 0.15
    f_ahead  = 1 + 0.5 · min(1, (best − 150)/150)   for best > 150   (+50 % at best ≥ 300)

T0 = 30 and Tmin = 0. T never decreases as the eval or the clock goes up, and never increases
as volatility goes up (tested).

## Reply weights (`opponent.StockfishDepthProxy`)

`go depth d`, MultiPV = `replies`, side-to-move POV, then `w_i = softmax(cp_i / 100)`. A reply
100 cp worse than the top one gets ≈27 % of the weight, 200 cp worse ≈12 %, 400 cp worse ≈2 %.
Replies under `min_reply_weight` are not evaluated, and the remaining weights are renormalised.
One legal reply gets weight 1.0 with no search; no legal replies gives `[]`. A depth-limited
engine choosing between near-equal moves is close to a coin flip, so a soft distribution
models it better than argmax.

## Safety invariants (tested in `tests/test_steer.py`, `tests/test_play.py`)

- The chosen move is always in `certified.candidates`. A 500-iteration random test with
  failing fakes checks this.
- Any exception inside steering → `certified.best.move` (reason `error`, message logged).
- If the argmax's `expected_eval` is below `best.expected_eval − T` → play best
  (`fallback_best`). A weakness bonus can never buy more than T of expected eval.
- Deadline = start + `soft_ms`. Best is always evaluated. Another candidate starts only if
  `now + (cost of the previous candidate) ≤ deadline`; skipped candidates get score −inf.
- If certification fails: a fresh MultiPV=1 search on the evaluator, then the first legal move.
  `choose` always returns a legal move.

## Knobs (`configs/lostfish.yaml`)

| key | default | meaning |
| --- | --- | --- |
| `certify.tolerance_cp` / `tolerance_min_cp` | 30 / 0 | T0 / Tmin |
| `certify.tighten_when_behind_cp` | 150 | eval at which T reaches Tmin |
| `certify.volatility_depths` / `volatility_half_cp` | 4 / 100 | volatility window / V that halves T |
| `certify.low_clock_fraction` | 0.15 | below this the clock shrinks T (to 50 % at 0) |
| `certify.expand_when_ahead_cp` / `expand_when_ahead` | 150 / 0.5 | widen T when ahead |
| `steer.lambda_weakness` | 0.15 | λ; bonus = λ · 100 · weakness cp |
| `steer.replies` / `reply_temperature_cp` / `min_reply_weight` | 2 / 100 / 0.02 | proxy distribution |
| `steer.weakness_radius` / `max_weakness` | 1.5 / 2.0 | cluster match radius / clamp |
| `steer.proxy_hash_mb` | 16 | proxy engine Hash |
| `budgets.<tc>.{certify_nodes, eval_nodes, k, proxy_depth_cap}` | §8 | per time control |

`SteeringPlayer(cfg, steering_lambda=…, tolerance_cp=…)` overrides λ and T0 for experiments
without mutating `cfg`.
