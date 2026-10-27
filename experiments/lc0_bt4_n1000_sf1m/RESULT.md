# lc0_bt4_n1000_sf1m — gauntlet result

- Started: 2026-10-27T07:54:43Z, finished: 2026-10-27T09:05:34Z, fastchess exit status: 0
- Config: `experiments/lc0_bt4_n1000_sf1m/config.toml`; LostFish commit: `f1a7f30`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/engines/stockfish name=Stockfish-1M nodes=1000000 option.Threads=1 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-bt4-n1000 nodes=1000 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/BT4-1024x15x32h-swa-6147500-policytune-332.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 100 -games 2 -repeat -concurrency 3 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_bt4_n1000_sf1m/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of Stockfish-1M vs lc0-bt4-n1000 (1000000 nodes - 1000 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 65.02 +/- 20.37, nElo: 157.50 +/- 48.15
LOS: 100.00 %, DrawRatio: 65.00 %, PairsRatio: 34.00
Games: 200, Wins: 38, Losses: 1, Draws: 161, Points: 118.5 (59.25 %)
Ptnml(0-2): [0, 1, 65, 30, 4], WL/DD Ratio: 0.00
--------------------------------------------------
Finished match
Total Time: 01:10:51 (hours:minutes:seconds)
```
