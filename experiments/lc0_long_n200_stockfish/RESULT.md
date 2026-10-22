# lc0_long_n200_stockfish — gauntlet result

- Started: 2026-10-22T08:43:40Z, finished: 2026-10-22T09:09:33Z, fastchess exit status: 0
- Config: `experiments/lc0_long_n200_stockfish/config.toml`; LostFish commit: `9d7f9b1`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261021 -rounds 100 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_long_n200_stockfish/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of Stockfish vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 145.13 +/- 32.05, nElo: 245.32 +/- 48.15
LOS: 100.00 %, DrawRatio: 29.00 %, PairsRatio: 13.20
Games: 200, Wins: 89, Losses: 10, Draws: 101, Points: 139.5 (69.75 %)
Ptnml(0-2): [0, 5, 29, 48, 18], WL/DD Ratio: 0.21
--------------------------------------------------
Finished match
Total Time: 00:25:52 (hours:minutes:seconds)
```
