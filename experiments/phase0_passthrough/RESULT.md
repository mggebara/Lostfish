# phase0_passthrough — gauntlet result

- Started: 2026-10-20T03:26:19Z, finished: 2026-10-20T04:14:42Z, fastchess exit status: 0
- Config: `experiments/phase0_passthrough/config.toml`; LostFish commit: `3670239`
- Games in games.pgn: 200
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish option.Steering=false option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -each nodes=600000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 100 -games 2 -repeat -concurrency 4 -ratinginterval 10 -pgnout file=/Users/matthew/dev/LostFish/experiments/phase0_passthrough/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish vs Stockfish (600000 nodes, 1t, 64MB, 8moves_v3.pgn):
Elo: -0.00 +/- 0.00, nElo: nan +/- nan
LOS: nan %, DrawRatio: 100.00 %, PairsRatio: nan
Games: 200, Wins: 8, Losses: 8, Draws: 184, Points: 100.0 (50.00 %)
Ptnml(0-2): [0, 0, 100, 0, 0], WL/DD Ratio: 0.09
--------------------------------------------------
Finished match
Total Time: 00:48:22 (hours:minutes:seconds)
```
