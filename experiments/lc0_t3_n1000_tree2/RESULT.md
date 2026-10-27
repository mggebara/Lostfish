# lc0_t3_n1000_tree2 — gauntlet result (hand-written: the run was resumed twice from fastchess autosaves)

- Finished: 2026-10-27T04:44:09Z (21:44 PDT); written 2026-10-27T04:47:58Z; fastchess exit status: 0 (last segment)
- Config: `experiments/lc0_t3_n1000_tree2/config.toml` (exact tree, `configs/variants/v2_tree2_g50.yaml`, Profile lc0-t3-n1000, vs lc0 T3@1000, concurrency 3); LostFish engine code at `26e89f0`
- Games in games.pgn: 417 (399 unique (Round, White) records for 400 scheduled games; the rest are replays after the two resumes, so take the last occurrence per (Round, colour))
- Problems in fastchess output (all segments): 0
- History: started 2026-10-26 ~04:20 PDT; Windows Update rebooted the box at 05:57 (game ~176); resumed 06:38 from the autosave at game 158; paused 08:10 at game 296 for a shutdown (SIGINT after the autosave); resumed 20:25 from game 296; finished 21:44.

## Command (from command.txt)

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tree2-exact args=--config\ configs/variants/v2_tree2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t3-n1000 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t3-n1000 nodes=1000 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t3-512x15x16h-distill-swa-2767500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 200 -games 2 -repeat -concurrency 3 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_t3_n1000_tree2/games.pgn notation=san nodes=true
```

## fastchess final summary (last segment; its stats include the games loaded from the autosave)

```
--------------------------------------------------
Results of LostFish-v2-tree2-exact vs lc0-t3-n1000 (20000 nodes - 1000 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: -95.26 +/- 18.15, nElo: -188.00 +/- 34.05
LOS: 0.00 %, DrawRatio: 46.50 %, PairsRatio: 0.08
Games: 400, Wins: 14, Losses: 121, Draws: 265, Points: 146.5 (36.62 %)
Ptnml(0-2): [16, 83, 93, 8, 0], WL/DD Ratio: 0.07
--------------------------------------------------
Finished match
Total Time: 01:15:34 (hours:minutes:seconds)
```

## Paired by (Round, colour) against the same openings

vs `lc0_t3_n1000_control` (tolerance 0, Profile _generic):

```
A LostFish-v2-tree2-exact     399 games  14W 264D 121L   36.6%  (W 41.7 / B 31.5)
B LostFish-v2-tol0            400 games  10W 233D 157L   31.6%  (W 36.8 / B 26.5)
paired A - B: +4.9 points (SE 1.7, 95% [+1.6, +8.2], z=2.89) over 399 games in 200 rounds; A better in 72, worse in 43, same in 85
```

vs `lc0_t3_n1000_stockfish` (Stockfish@20k):

```
A LostFish-v2-tree2-exact     399 games  14W 264D 121L   36.6%  (W 41.7 / B 31.5)
B Stockfish                   400 games  7W 230D 163L   30.5%  (W 34.5 / B 26.5)
paired A - B: +6.1 points (SE 1.7, 95% [+2.9, +9.4], z=3.69) over 399 games in 200 rounds; A better in 79, worse in 35, same in 86
```

## Telemetry (logs/moves.jsonl, profile lc0-t3-n1000; replayed games counted too)

```
profile lc0-t3-n1000 moves=23612 deviations=266 (1.1%) reasons={'single_candidate': 11252, 'fallback_best': 4303, 'steer': 8057} ms/move median=961 mean=1902
```
