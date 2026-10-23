# lc0_long_n200_predgate45 — gauntlet result

- Started: 2026-10-23T07:04:07Z, finished: 2026-10-23T08:28:22Z, fastchess exit status: 0
- Config: `experiments/lc0_long_n200_predgate45/config.toml`; LostFish commit: `c8858b7`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 2

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-pred-gate45 args=--config\ configs/variants/v2_pred_gate45.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261021 -rounds 100 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_long_n200_predgate45/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-pred-gate45 vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 205.04 +/- 40.98, nElo: 303.46 +/- 48.15
LOS: 100.00 %, DrawRatio: 19.00 %, PairsRatio: 15.20
Games: 200, Wins: 115, Losses: 9, Draws: 76, Points: 153.0 (76.50 %)
Ptnml(0-2): [0, 5, 19, 41, 35], WL/DD Ratio: 0.27
--------------------------------------------------
Finished match
Total Time: 01:24:15 (hours:minutes:seconds)
```
