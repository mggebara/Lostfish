# lc0_bt4_n1000_stockfish — gauntlet result

- Started: 2026-10-26T08:05:22Z, finished: 2026-10-26T08:22:47Z, fastchess exit status: 0
- Config: `experiments/lc0_bt4_n1000_stockfish/config.toml`; LostFish commit: `442ad65`
- Games in games.pgn: 100
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-bt4-n1000 nodes=1000 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/BT4-1024x15x32h-swa-6147500-policytune-332.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 50 -games 2 -repeat -concurrency 3 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_bt4_n1000_stockfish/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of Stockfish vs lc0-bt4-n1000 (20000 nodes - 1000 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: -172.78 +/- 40.52, nElo: -343.24 +/- 68.10
LOS: 0.00 %, DrawRatio: 26.00 %, PairsRatio: 0.00
Games: 100, Wins: 1, Losses: 47, Draws: 52, Points: 27.0 (27.00 %)
Ptnml(0-2): [9, 28, 13, 0, 0], WL/DD Ratio: 0.08
--------------------------------------------------
Finished match
Total Time: 00:17:24 (hours:minutes:seconds)
```
