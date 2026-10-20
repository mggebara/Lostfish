# gauntlet_v1 — gauntlet result

- Started: 2026-10-20T04:17:02Z, finished: 2026-10-20T08:30:34Z, fastchess exit status: 0
- Config: `experiments/gauntlet_v1/config.toml`; LostFish commit: `7b2dfeb`
- Games in games.pgn: 1088
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 216

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-steer option.Steering=true option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d8 depth=8 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d10 depth=10 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d12 depth=12 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d14 depth=14 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-n150k nodes=150000 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-n300k nodes=300000 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo2600 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=2600 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo3000 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=3000 -each nodes=600000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/gauntlet_v1/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Finished game 1086 (SF-elo2600 vs Stockfish): 0-1 {Black mates}
Started game 1088 of 1088 (SF-elo3000 vs Stockfish)
Warning; Bestmove does not match beginning of last PV - move e4d5 from SF-elo3000
Info; info depth 245 seldepth 5 multipv 1 score mate -2 nodes 23797 nps 4759400 hashfull 0 tbhits 0 time 5 pv e4d3 h5g3 h1h2 f4e4
Position; startpos
Moves; c2c4 e7e5 b1c3 g8f6 g1f3 b8c6 g2g3 c6d4 f1g2 d4f3 g2f3 f8b4 f3g2 h7h6 d1b3 b4c5 b3c2 c7c6 d2d3 e8g8 c1d2 d7d5 c3d1 c5b6 b2b4 f8e8 e1g1 c8f5 d1e3 b6e3 f2e3 d8d7 a1c1 a8c8 a2a4 h6h5 c2b3 f5h3 g2h3 d7h3 f1f2 b7b6 a4a5 b6b5 c4b5 c6b5 e3e4 c8c1 d2c1 e8c8 b3b1 d5e4 f2g2 f6d5 g1h1 e4e3 g2g1 h3e6 c1b2 h5h4 g1f1 h4g3 b2e5 e6e5 h1g2 g3h2 d3d4 d5f4 g2f3 e5g5 f1h1 f4h5 f3e4 g5f4
Finished game 1088 (SF-elo3000 vs Stockfish): 0-1 {Black mates}
Finished game 1084 (SF-n300k vs Stockfish): 1-0 {White mates}
Warning; Bestmove does not match beginning of last PV - move e8f7 from SF-elo3000
Info; info depth 245 seldepth 5 multipv 1 score mate -2 nodes 37923 nps 7584600 hashfull 0 tbhits 0 time 5 pv e8d7 d4c5 d7c7 h4h7
Position; startpos
Moves; c2c4 e7e5 b1c3 g8f6 g1f3 b8c6 g2g3 c6d4 f1g2 d4f3 g2f3 f8b4 f3g2 h7h6 d1b3 b4c5 c3a4 c5d6 e1g1 c7c6 f1d1 d6c7 d2d4 d8e7 d4e5 c7e5 c1d2 d7d6 d2b4 c6c5 b4d2 g7g5 d2c3 a8b8 c3e5 e7e5 d1d3 e8g8 a4c3 c8e6 a2a4 f8d8 h2h3 f6d7 a1d1 d7b6 b3c2 d8d7 b2b3 b8d8 g3g4 a7a5 d3e3 e5h8 g2d5 e6d5 c3d5 b6d5 d1d5 h8h7 c2d2 g8f8 d5f5 h7g7 g1g2 f8g8 d2a5 g7f8 a5d2 b7b6 h3h4 g5h4 g2h3 f8g7 e3e4 d6d5 c4d5 d7a7 d2f4 a7d7 e4e5 g8f8 e5e6 b6b5 a4b5 d7b7 e6h6 g7d4 f4g5 d8e8 g5h4 e8e3 f2e3 f8e8 e3d4 f7f6 h6h8
Finished game 1087 (Stockfish vs SF-elo3000): 1-0 {White mates}
Finished game 1083 (Stockfish vs SF-n300k): 1/2-1/2 {Draw by 3-fold repetition}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     199.81      25.29     277.91      28.37        576      76.0%      36.1% [0, 4, 104, 57, 123]
   2 LostFish-steer                152.68      24.22     203.26      28.37        576      70.7%      36.1% [1, 21, 104, 63, 99]
   3 SF-n150k                       24.47      14.88      99.38      60.19        128      53.5%      85.9%     [0, 0, 55, 9, 0]
   4 SF-n300k                       24.47      14.88      99.38      60.19        128      53.5%      85.9%     [0, 0, 55, 9, 0]
   5 SF-d14                       -103.38      29.47    -224.53      60.19        128      35.5%      45.3%    [4, 30, 29, 1, 0]
   6 SF-d12                       -169.77      32.56    -367.91      60.19        128      27.3%      23.4%    [9, 40, 15, 0, 0]
   7 SF-d10                       -331.92      51.19    -687.93      60.19        128      12.9%       1.6%    [32, 31, 1, 0, 0]
   8 SF-d8                        -508.67     128.77    -873.14      60.19        128       5.1%       4.7%     [54, 7, 3, 0, 0]
   9 SF-elo3000                   -647.92     176.95   -1606.68      60.19        128       2.3%       0.0%     [58, 6, 0, 0, 0]
  10 SF-elo2600                      -inf        nan       -inf        nan        128       0.0%       0.0%     [64, 0, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 04:13:31 (hours:minutes:seconds)

```
