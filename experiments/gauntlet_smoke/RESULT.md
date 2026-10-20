# gauntlet_smoke — gauntlet result

- Started: 2026-10-20T03:37:35Z, finished: 2026-10-20T03:38:21Z, fastchess exit status: 0
- Config: `experiments/gauntlet_smoke/config.toml`; LostFish commit: `5e5a31d`
- Games in games.pgn: 10
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 2

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-steer option.Steering=true option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d6 depth=6 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo2000 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=2000 -each nodes=100000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 1 -games 2 -repeat -concurrency 2 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/gauntlet_smoke/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Finished game 4 (SF-d6 vs LostFish-steer): 0-1 {Black mates}
Started game 6 of 10 (SF-elo2000 vs LostFish-steer)
Warning; Bestmove does not match beginning of last PV - move g7f6 from SF-elo2000
Info; info depth 245 seldepth 5 multipv 1 score mate -2 nodes 19180 nps 2740000 hashfull 0 tbhits 0 time 7 pv f8e8 f6f7 h6h5 b7a8
Position; startpos
Moves; e2e4 c7c5 g1f3 e7e6 b1c3 b8c6 d2d4 c5d4 f3d4 g8f6 a2a3 f8e7 f1e2 e8g8 c1e3 d7d6 d1d3 e6e5 d4b3 a7a6 e1c1 b7b5 e3g5 f6e8 g5e7 d8e7 c3d5 e7b7 c1b1 c6e7 b3a5 b7a7 d5e7 a7e7 d3d5 e7c7 d5a8 h7h6 a8c6 c7a5 c6c8 e8f6 c8b7 b5b4 a3b4 a5d8 e2a6 f6g4 d1d2 d8f6 h1d1 g4f2 d1f1 f6d8 d2f2 f7f5 f2f5 f8f6 a6c4 d6d5 c4d5 g8f8 f5f6 d8f6 f1f6
Finished game 5 (LostFish-steer vs SF-elo2000): 1-0 {White mates}
Started game 7 of 10 (Stockfish vs SF-d6)
Finished game 6 (SF-elo2000 vs LostFish-steer): 0-1 {Black mates}
Started game 8 of 10 (SF-d6 vs Stockfish)
Finished game 7 (Stockfish vs SF-d6): 1-0 {White mates}
Started game 9 of 10 (Stockfish vs SF-elo2000)
Finished game 8 (SF-d6 vs Stockfish): 0-1 {Black mates}
Started game 10 of 10 (SF-elo2000 vs Stockfish)
Warning; Bestmove does not match beginning of last PV - move f5f4 from SF-elo2000
Info; info depth 245 seldepth 5 multipv 1 score mate -2 nodes 89113 nps 5940866 hashfull 0 tbhits 0 time 15 pv h7h6 e7e8q h5h4 e8h5
Position; startpos
Moves; e2e4 c7c5 g1f3 e7e6 b1c3 b8c6 d2d4 c5d4 f3d4 g8f6 a2a3 f8e7 f1e2 e8g8 c1e3 d7d6 d1d3 c8d7 f2f4 a7a6 e1c1 c6d4 e3d4 d8a5 d3e3 a8c8 d1d3 a5d8 h1d1 c8c6 c1b1 b7b5 d4f6 g7f6 e4e5 d6d5 c3d5 e6d5 d3d5 f6e5 d5d7 e7c5 e3g3 c6g6 d7d8 g6g3 h2g3 c5e3 f4e5 e3d4 d1d4 f7f5 e5e6 h7h6 d4d7 h6h5 e6e7 f8e8 d8e8 g8h7 e8f8
Finished game 9 (Stockfish vs SF-elo2000): 1-0 {White mates}
Finished game 10 (SF-elo2000 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     416.56        nan     868.59     278.00          6      91.7%       0.0%      [0, 0, 0, 1, 2]
   2 LostFish-steer                190.85        nan     173.72     278.00          6      75.0%       0.0%      [0, 1, 0, 0, 2]
   3 SF-d6                           -inf        nan       -inf        nan          4       0.0%       0.0%      [2, 0, 0, 0, 0]
   4 SF-elo2000                      -inf        nan       -inf        nan          4       0.0%       0.0%      [2, 0, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:00:46 (hours:minutes:seconds)

```
