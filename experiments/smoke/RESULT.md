# smoke — gauntlet result

- Started: 2026-10-20T03:20:53Z, finished: 2026-10-20T03:21:12Z, fastchess exit status: 0
- Config: `experiments/smoke/config.toml`; LostFish commit: `64de84f` (dirty tree)
- Games in games.pgn: 10
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish option.Steering=false option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -each nodes=50000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 1 -rounds 5 -games 2 -repeat -concurrency 4 -ratinginterval 10 -pgnout file=/Users/matthew/dev/LostFish/experiments/smoke/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish vs Stockfish (50000 nodes, 1t, 64MB, 8moves_v3.pgn):
Elo: -0.00 +/- 0.00, nElo: nan +/- nan
LOS: nan %, DrawRatio: 100.00 %, PairsRatio: nan
Games: 10, Wins: 3, Losses: 3, Draws: 4, Points: 5.0 (50.00 %)
Ptnml(0-2): [0, 0, 5, 0, 0], WL/DD Ratio: 1.50
--------------------------------------------------
Finished match
Total Time: 00:00:18 (hours:minutes:seconds)
```
