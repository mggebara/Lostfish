# lc0_rep_n800_tree2 — gauntlet result

- Started: 2026-10-26T08:36:39Z, finished: 2026-10-26T10:25:53Z, fastchess exit status: 0
- Config: `experiments/lc0_rep_n800_tree2/config.toml`; LostFish commit: `4beb658`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 2

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tree2-exact args=--config\ configs/variants/v2_tree2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n800 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t1-n800 nodes=800 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261027 -rounds 200 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_rep_n800_tree2/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tree2-exact vs lc0-t1-n800 (20000 nodes - 800 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 50.74 +/- 18.84, nElo: 93.08 +/- 34.05
LOS: 100.00 %, DrawRatio: 49.50 %, PairsRatio: 2.88
Games: 400, Wins: 101, Losses: 43, Draws: 256, Points: 229.0 (57.25 %)
Ptnml(0-2): [1, 25, 99, 65, 10], WL/DD Ratio: 0.19
--------------------------------------------------
Finished match
Total Time: 01:49:14 (hours:minutes:seconds)
```
