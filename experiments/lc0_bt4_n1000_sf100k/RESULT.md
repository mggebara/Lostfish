# lc0_bt4_n1000_sf100k — gauntlet result

- Started: 2026-10-27T06:37:57Z, finished: 2026-10-27T07:13:02Z, fastchess exit status: 0
- Config: `experiments/lc0_bt4_n1000_sf100k/config.toml`; LostFish commit: `f1a7f30`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/engines/stockfish name=Stockfish-100k nodes=100000 option.Threads=1 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-bt4-n1000 nodes=1000 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/BT4-1024x15x32h-swa-6147500-policytune-332.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 100 -games 2 -repeat -concurrency 3 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_bt4_n1000_sf100k/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of Stockfish-100k vs lc0-bt4-n1000 (100000 nodes - 1000 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 6.95 +/- 17.33, nElo: 19.33 +/- 48.15
LOS: 78.43 %, DrawRatio: 74.00 %, PairsRatio: 1.36
Games: 200, Wins: 18, Losses: 14, Draws: 168, Points: 102.0 (51.00 %)
Ptnml(0-2): [0, 11, 74, 15, 0], WL/DD Ratio: 0.04
--------------------------------------------------
Finished match
Total Time: 00:35:05 (hours:minutes:seconds)
```
