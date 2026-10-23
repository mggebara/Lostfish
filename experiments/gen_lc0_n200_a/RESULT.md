# gen_lc0_n200_a — gauntlet result

- Started: 2026-10-23T02:04:03Z, finished: 2026-10-23T04:07:04Z, fastchess exit status: 0
- Config: `experiments/gen_lc0_n200_a/config.toml`; LostFish commit: `6042a2c` (dirty tree)
- Games in games.pgn: 600
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261101 -rounds 300 -games 2 -repeat -concurrency 3 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/gen_lc0_n200_a/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tol0 vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 130.28 +/- 18.94, nElo: 209.98 +/- 27.80
LOS: 100.00 %, DrawRatio: 28.33 %, PairsRatio: 8.35
Games: 600, Wins: 254, Losses: 39, Draws: 307, Points: 407.5 (67.92 %)
Ptnml(0-2): [2, 21, 85, 144, 48], WL/DD Ratio: 0.20
--------------------------------------------------
Finished match
Total Time: 02:03:01 (hours:minutes:seconds)
```
