# lc0_rep_n200_gaterand — gauntlet result

- Started: 2026-10-23T12:18:44Z, finished: 2026-10-23T14:32:19Z, fastchess exit status: 0
- Config: `experiments/lc0_rep_n200_gaterand/config.toml`; LostFish commit: `fd6c979`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 1

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-gate-random args=--config\ configs/variants/v2_pred_gaterand.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261023 -rounds 200 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_rep_n200_gaterand/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-gate-random vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 166.23 +/- 25.15, nElo: 261.73 +/- 34.05
LOS: 100.00 %, DrawRatio: 24.50 %, PairsRatio: 12.73
Games: 400, Wins: 199, Losses: 21, Draws: 180, Points: 289.0 (72.25 %)
Ptnml(0-2): [0, 11, 49, 91, 49], WL/DD Ratio: 0.26
--------------------------------------------------
Finished match
Total Time: 02:13:35 (hours:minutes:seconds)
```
