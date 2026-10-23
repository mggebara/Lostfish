# lc0_rep_n200_control — gauntlet result

- Started: 2026-10-23T01:12:36Z, finished: 2026-10-23T02:03:44Z, fastchess exit status: 0
- Config: `experiments/lc0_rep_n200_control/config.toml`; LostFish commit: `560800d`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261022 -rounds 200 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_rep_n200_control/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tol0 vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 135.96 +/- 22.41, nElo: 228.79 +/- 34.05
LOS: 100.00 %, DrawRatio: 34.50 %, PairsRatio: 13.56
Games: 400, Wins: 171, Losses: 22, Draws: 207, Points: 274.5 (68.62 %)
Ptnml(0-2): [0, 9, 69, 86, 36], WL/DD Ratio: 0.23
--------------------------------------------------
Finished match
Total Time: 00:51:07 (hours:minutes:seconds)
```
