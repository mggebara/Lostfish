# gauntlet_v1_tol15 — gauntlet result

- Started: 2026-10-20T11:32:04Z, finished: 2026-10-20T15:01:15Z, fastchess exit status: 0
- Config: `experiments/gauntlet_v1_tol15/config.toml`; LostFish commit: `4326b3b`
- Games in games.pgn: 1088
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 214

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-steer args=--config\ configs/variants/tol15.yaml nodes=600000 option.Steering=true option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=600000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d8 depth=8 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d10 depth=10 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d12 depth=12 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d14 depth=14 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-n150k nodes=150000 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-n300k nodes=300000 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo2600 nodes=600000 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=2600 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo3000 nodes=600000 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=3000 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/gauntlet_v1_tol15/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Position; startpos
Moves; g2g3 e7e5 c2c4 g8f6 f1g2 c7c6 g1f3 e5e4 f3d4 d7d5 c4d5 c6d5 b1c3 b8c6 d4c6 b7c6 d2d3 f8b4 d3e4 e8g8 e4d5 f6d5 c1d2 d5c3 b2c3 b4c5 e1g1 a8b8 d2f4 b8b2 d1d8 f8d8 f1d1 d8f8 e2e3 b2c2 d1c1 c2c1 a1c1 c8d7 a2a4 f8c8 a4a5 d7f5 g2f3 h7h5 f3h5 c8d8 h5f3 d8d2 f3c6 f5d3 f4e5 d2a2 c1d1 d3e2 d1d8 c5f8 e5d6 g7g5 d6f8 g5g4 g1g2 g8h8 h2h3 e2f1 g2f1 a2d2 d8d2 f7f6 c6d5 a7a6 h3g4 h8h7 d5f7
Warning; Bestmove does not match beginning of last PV - move h7h8 from SF-elo2600
Info; info depth 245 seldepth 3 multipv 1 score mate -1 nodes 2763 nps 2763000 hashfull 0 tbhits 0 time 1 pv f5f4 d6h6
Position; startpos
Moves; g2g3 e7e5 c2c4 g8f6 f1g2 c7c6 g1f3 e5e4 f3d4 d7d5 c4d5 c6d5 b1c3 b8c6 d4c6 b7c6 d2d3 f8b4 d3e4 e8g8 e4d5 f6d5 c1d2 d5c3 b2c3 b4c5 e1g1 a8b8 d2f4 b8b2 d1d8 f8d8 f1d1 d8f8 e2e3 b2c2 d1c1 c2c1 a1c1 c8d7 a2a4 f8c8 a4a5 d7f5 g2f3 h7h5 f3h5 c8d8 h5f3 d8d2 f3c6 f5d3 f4e5 d2a2 c1d1 d3e2 d1d8 c5f8 e5d6 g7g5 d6f8 g5g4 g1g2 g8h8 h2h3 e2f1 g2f1 a2d2 d8d2 f7f6 c6d5 a7a6 h3g4 h8h7 d5f7 f6f5 d2d6
Finished game 1085 (Stockfish vs SF-elo2600): 1-0 {White mates}
Started game 1087 of 1088 (Stockfish vs SF-elo3000)
Finished game 1083 (Stockfish vs SF-n300k): 1-0 {White mates}
Started game 1088 of 1088 (SF-elo3000 vs Stockfish)
Finished game 1086 (SF-elo2600 vs Stockfish): 0-1 {Black mates}
Finished game 1084 (SF-n300k vs Stockfish): 1-0 {White mates}
Finished game 1087 (Stockfish vs SF-elo3000): 1-0 {White mates}
Finished game 1088 (SF-elo3000 vs Stockfish): 0-1 {Black wins by adjudication: SyzygyTB}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     216.76      25.13     314.46      28.37        576      77.7%      32.6%  [0, 0, 94, 69, 125]
   2 LostFish-steer                176.66      24.16     245.80      28.37        576      73.4%      37.8% [0, 9, 109, 61, 109]
   3 SF-n300k                       -2.71      14.07     -11.62      60.19        128      49.6%      89.1%     [0, 4, 57, 3, 0]
   4 SF-n150k                      -51.96      22.70    -140.04      60.19        128      42.6%      73.4%    [2, 15, 47, 0, 0]
   5 SF-d14                       -100.42      29.40    -217.86      60.19        128      35.9%      51.6%    [5, 26, 33, 0, 0]
   6 SF-d12                       -205.64      39.35    -396.41      60.19        128      23.4%      18.8%   [16, 36, 12, 0, 0]
   7 SF-d10                       -320.13      51.16    -640.87      60.19        128      13.7%       3.1%    [31, 31, 2, 0, 0]
   8 SF-d8                        -539.11     108.60   -1190.45      60.19        128       4.3%       0.0%    [53, 11, 0, 0, 0]
   9 SF-elo3000                   -962.62        nan   -3930.91      60.19        128       0.4%       0.0%     [63, 1, 0, 0, 0]
  10 SF-elo2600                      -inf        nan       -inf        nan        128       0.0%       0.0%     [64, 0, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 03:29:10 (hours:minutes:seconds)

```
