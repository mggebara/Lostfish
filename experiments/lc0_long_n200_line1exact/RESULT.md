# lc0_long_n200_line1exact — gauntlet result

- Started: 2026-10-23T05:48:36Z, finished: 2026-10-23T07:02:18Z, fastchess exit status: 0
- Config: `experiments/lc0_long_n200_line1exact/config.toml`; LostFish commit: `e3cd8ce`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 3

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line1-exact args=--config\ configs/variants/v2_line1_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261021 -rounds 100 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_long_n200_line1exact/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-line1-exact vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 190.85 +/- 33.54, nElo: 334.32 +/- 48.15
LOS: 100.00 %, DrawRatio: 27.00 %, PairsRatio: inf
Games: 200, Wins: 104, Losses: 4, Draws: 92, Points: 150.0 (75.00 %)
Ptnml(0-2): [0, 0, 27, 46, 27], WL/DD Ratio: 0.17
--------------------------------------------------
Finished match
Total Time: 01:13:41 (hours:minutes:seconds)
```
