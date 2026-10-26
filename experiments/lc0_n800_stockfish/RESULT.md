# lc0_n800_stockfish — gauntlet result

- Started: 2026-10-26T03:49:31Z, finished: 2026-10-26T04:02:53Z, fastchess exit status: 0
- Config: `experiments/lc0_n800_stockfish/config.toml`; LostFish commit: `04ea58e`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t1-n800 nodes=800 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 200 -games 2 -repeat -concurrency 6 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_n800_stockfish/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of Stockfish vs lc0-t1-n800 (20000 nodes - 800 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 9.56 +/- 18.40, nElo: 17.71 +/- 34.05
LOS: 84.60 %, DrawRatio: 58.00 %, PairsRatio: 1.40
Games: 400, Wins: 74, Losses: 63, Draws: 263, Points: 205.5 (51.38 %)
Ptnml(0-2): [7, 28, 116, 45, 4], WL/DD Ratio: 0.22
--------------------------------------------------
Finished match
Total Time: 00:13:21 (hours:minutes:seconds)
```
