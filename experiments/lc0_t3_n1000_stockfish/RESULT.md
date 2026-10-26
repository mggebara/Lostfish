# lc0_t3_n1000_stockfish — gauntlet result

- Started: 2026-10-26T07:31:19Z, finished: 2026-10-26T08:05:22Z, fastchess exit status: 0
- Config: `experiments/lc0_t3_n1000_stockfish/config.toml`; LostFish commit: `f76ee4c`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t3-n1000 nodes=1000 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t3-512x15x16h-distill-swa-2767500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 200 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_t3_n1000_stockfish/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of Stockfish vs lc0-t3-n1000 (20000 nodes - 1000 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: -143.07 +/- 19.94, nElo: -273.31 +/- 34.05
LOS: 0.00 %, DrawRatio: 32.00 %, PairsRatio: 0.03
Games: 400, Wins: 7, Losses: 163, Draws: 230, Points: 122.0 (30.50 %)
Ptnml(0-2): [28, 104, 64, 4, 0], WL/DD Ratio: 0.05
--------------------------------------------------
Finished match
Total Time: 00:34:02 (hours:minutes:seconds)
```
