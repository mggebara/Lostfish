# lc0_long_n200_predgate — gauntlet result

- Started: 2026-10-23T04:51:34Z, finished: 2026-10-23T05:48:19Z, fastchess exit status: 0
- Config: `experiments/lc0_long_n200_predgate/config.toml`; LostFish commit: `eb53b13`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-pred-gate args=--config\ configs/variants/v2_pred_gate.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261021 -rounds 100 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_long_n200_predgate/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-pred-gate vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 193.17 +/- 31.48, nElo: 361.97 +/- 48.15
LOS: 100.00 %, DrawRatio: 17.00 %, PairsRatio: 40.50
Games: 200, Wins: 112, Losses: 11, Draws: 77, Points: 150.5 (75.25 %)
Ptnml(0-2): [0, 2, 17, 59, 22], WL/DD Ratio: 1.12
--------------------------------------------------
Finished match
Total Time: 00:56:45 (hours:minutes:seconds)
```
