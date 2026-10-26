# lc0_rep_n800_control — gauntlet result

- Started: 2026-10-26T08:23:27Z, finished: 2026-10-26T08:36:39Z, fastchess exit status: 0
- Config: `experiments/lc0_rep_n800_control/config.toml`; LostFish commit: `4beb658`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=_generic option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t1-n800 nodes=800 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261027 -rounds 200 -games 2 -repeat -concurrency 6 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_rep_n800_control/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tol0 vs lc0-t1-n800 (20000 nodes - 800 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 6.08 +/- 19.79, nElo: 10.48 +/- 34.05
LOS: 72.67 %, DrawRatio: 50.50 %, PairsRatio: 1.20
Games: 400, Wins: 76, Losses: 69, Draws: 255, Points: 203.5 (50.88 %)
Ptnml(0-2): [7, 38, 101, 49, 5], WL/DD Ratio: 0.20
--------------------------------------------------
Finished match
Total Time: 00:13:11 (hours:minutes:seconds)
```
