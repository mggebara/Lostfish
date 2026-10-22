# lc0_long_n200_tree2 — gauntlet result

- Started: 2026-10-22T05:16:47Z, finished: 2026-10-22T08:17:41Z, fastchess exit status: 0
- Config: `experiments/lc0_long_n200_tree2/config.toml`; LostFish commit: `4be2166`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tree2-exact args=--config\ configs/variants/v2_tree2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261021 -rounds 100 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_long_n200_tree2/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tree2-exact vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 209.91 +/- 37.30, nElo: 344.38 +/- 48.15
LOS: 100.00 %, DrawRatio: 17.00 %, PairsRatio: 26.67
Games: 200, Wins: 115, Losses: 7, Draws: 78, Points: 154.0 (77.00 %)
Ptnml(0-2): [0, 3, 17, 49, 31], WL/DD Ratio: 0.31
--------------------------------------------------
Finished match
Total Time: 03:00:53 (hours:minutes:seconds)
```
