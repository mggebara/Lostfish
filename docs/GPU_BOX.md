# GPU box — setup checklist and first jobs

Why: the exact victim model is the victim engine (Lc0) searched to its own node budget, ~15 times per move. On the
M1 Pro (Metal) one lc0@200 search is ~0.7 s, so the winning seed costs 4.2 s/move (236× Stockfish). On an NVIDIA card
it is ~10–20 ms, which makes the same seed a playable rapid-game engine and lets us test stronger victims.
Context: `docs/DECISIONS.md` 2026-10-22/23 (exact tree +5.8 ± 1.6 over 555 paired games; predictor-in-engine closed).

## 1. Setup (Linux x86_64 + NVIDIA)

1. Driver + CUDA: `nvidia-smi` must work (driver ≥ 550; CUDA 12.x runtime).
2. Repo: `git clone https://github.com/mggebara/Lostfish.git LostFish && cd LostFish`
3. Python 3.11+: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,training]"`.
   If `python -c "import torch; print(torch.cuda.is_available())"` prints False, reinstall torch from the CUDA index:
   `pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu124`.
4. Engines: `scripts/setup_engines.sh` (handles Linux-x86_64: Stockfish 19 avx2, fastchess, Syzygy 3-4-5 ≈ 1 GB).
5. Lc0 with CUDA: use the release `lc0-v0.32.x-linux-cuda` (or `cudnn`) build from github.com/LeelaChessZero/lc0/releases,
   or build from source (`./build.sh`, needs meson, ninja, cuda toolkit). Put the binary on PATH **and** symlink it at
   `engines/lc0` (experiment configs use `cmd = "engines/lc0"`; `configs/lostfish.yaml` uses `lc0_path: lc0` from PATH).
6. Net: `engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz` (not in git). rsync it from the Mac or download it from
   https://storage.lczero.org/files/networks-contrib/ (same file name). Profiles reference this relative path.
7. Verify: `engines/lc0 benchmark --weights=engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz --backend=cuda-fp16 --nodes=200`
   should report well under 50 ms; and `pytest -q` (engine tests are marked slow: `pytest -q -m slow`).
8. Lichess: nothing. The bot and its token stay on the Mac.

## 2. Data from the Mac (small)

```bash
rsync -av matthew@<mac>:/Users/matthew/dev/LostFish/data/victim_errors/ data/victim_errors/   # 160k labelled victim moves, 5 MB
rsync -av matthew@<mac>:/Users/matthew/dev/LostFish/data/models/ data/models/                 # predictor checkpoints, 26 MB
rsync -av matthew@<mac>:/Users/matthew/dev/LostFish/engines/lc0nets/ engines/lc0nets/         # the T1 net
```
`experiments/*/games.pgn` are gitignored; rsync `experiments/` too if you need to pair against the Mac's matches.

## 3. First jobs, in order

1. **Speed check.** `scripts/lostfish --config configs/variants/v2_tree2_g50.yaml` with `Profile lc0-t1-n200`, one
   `go nodes 20000` from a middlegame position; read `timings_ms.proxy` in the last line of `logs/moves.jsonl`.
   Target: total ≤ 150 ms per move (Mac: 4,246 ms). If the Lc0 proxy is slow, check the backend (`cuda-fp16`).
2. **Exploitability point 3, victim @800.** Add `profiles/lc0-t1-n800.json` (copy `lc0-t1-n200.json`, set
   `notes.lc0_nodes: 800`, name) and two 2-engine matches modelled on `experiments/lc0_long_n200_{tree2,control}`
   with the victim at `nodes = 800`, 200 rounds, same `srand` for both; pair by Round (snippet in DECISIONS 2026-10-22
   01:49). Question: does the margin grow, hold or vanish as the victim gets stronger? Stockfish@20k's score vs
   lc0@800 is the ceiling check — if it is below 50%, we are finally in the regime where exploitation matters.
3. **Data at scale.** 5,000 control-vs-lc0@200 games (`experiments/gen_lc0_n200_a/config.toml` is the template;
   concurrency = physical cores), then `python -m mining.victim_errors --pgn "experiments/gen_*/games.pgn" --workers <cores-2>`
   (Stockfish, CPU-bound). The predictor overfit on 160k positions; this is what fixes it. Dedupe FENs before splitting.
4. **Stronger victim.** A bigger net (T2/T3-class or BT4) at 1,000+ nodes. First measure plain Stockfish@20k against
   it; the interesting victim is one that beats Stockfish@20k. Then repeat job 2 against it.
5. Later: Stage B (self-play against the frozen victim, PLAN §6 Phase 5).

## 4. Gotchas carried over from the Mac

- fastchess `-tournament gauntlet` pairs the seeds with each other too — use 2-engine matches and pair by Round.
- `[each] nodes` overrides per-engine node limits; set nodes per engine.
- Deterministic engines replay identical games from shared openings: dedupe FENs before any train/val split.
- `pgrep -f` matches its own `bash -c` wrapper; wait on PIDs with `kill -0`.
- `seed_scores.py` prints no rows for 2-engine matches; use `scripts/game_length.py <exp> <opponent>` or the pairing snippet.
- Never commit `.env`, `configs/lichess-bot.config.yml`, or anything under `data/`, `engines/`, `tb/`.
