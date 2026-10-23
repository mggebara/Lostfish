# lc0_rep_n200_control2 — gauntlet result

- Started: 2026-10-23T11:14:47Z, finished: 2026-10-23T12:04:41Z, fastchess exit status: 0
- Config: `experiments/lc0_rep_n200_control2/config.toml`; LostFish commit: `871f04a`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261023 -rounds 200 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_rep_n200_control2/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tol0 vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 159.78 +/- 24.06, nElo: 259.99 +/- 34.05
LOS: 100.00 %, DrawRatio: 27.50 %, PairsRatio: 15.11
Games: 400, Wins: 192, Losses: 20, Draws: 188, Points: 286.0 (71.50 %)
Ptnml(0-2): [0, 9, 55, 91, 45], WL/DD Ratio: 0.25
--------------------------------------------------
Finished match
Total Time: 00:49:53 (hours:minutes:seconds)
```
