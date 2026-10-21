# gauntlet_v1_tol0 — gauntlet result

- Started: 2026-10-21T01:11:21Z, finished: 2026-10-21T04:03:02Z, fastchess exit status: 0
- Config: `experiments/gauntlet_v1_tol0/config.toml`; LostFish commit: `eec6d8e`
- Games in games.pgn: 1088
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 224

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-steer args=--config\ configs/variants/tol0.yaml nodes=600000 option.Steering=true option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=600000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d8 depth=8 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d10 depth=10 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d12 depth=12 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d14 depth=14 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-n150k nodes=150000 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-n300k nodes=300000 option.Threads=1 option.Hash=16 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo2600 nodes=600000 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=2600 -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-elo3000 nodes=600000 option.Threads=1 option.Hash=16 option.UCI_LimitStrength=true option.UCI_Elo=3000 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/gauntlet_v1_tol0/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Warning; Bestmove does not match beginning of last PV - move d8c7 from SF-elo3000
Info; info depth 245 seldepth 7 multipv 1 score mate -3 nodes 385736 nps 10150947 hashfull 1 tbhits 0 time 38 pv d7e8 f8e8 d8c7 e8d7 c7b8 d7b7
Position; startpos
Moves; c2c4 e7e5 b1c3 g8f6 g1f3 b8c6 g2g3 c6d4 f1g2 d4f3 g2f3 f8b4 f3g2 h7h6 d1b3 b4c5 c3a4 c5d6 e1g1 e8g8 f1d1 f8e8 d2d4 e5d4 d1d4 d8e7 c1d2 e7e2 a1e1 e2h5 e1e8 f6e8 d4e4 e8f6 e4e1 c7c6 d2c3 f6h7 e1e8 d6f8 c3b4 d7d6 b4d6 h5g6 d6b4 g6b1 e8e1 b1g6 e1e8 g6b1 e8e1 b1g6 h2h4 f7f5 b4f8 h7f8 a4c5 f5f4 g3f4 b7b6 c5e4 c8e6 e4g3 a8d8 g2c6 e6f7 c6g2 d8d4 f4f5 g6d6 g3e4 d6e5 b3c3 g7g6 f2f4 e5h8 f5f6 d4d8 b2b4 h8h7 c4c5 f7a2 e4d6 a2e6 f6f7 e6f7 c5c6 f7e6 c6c7 h7d7 c7d8q d7d8 d6e4 d8e7 e4f6 g8f7 f6d5 e7h4 b4b5 e6d7 e1e7 h4e7 d5e7 f7e7 c3g7 e7e8 g2c6 g6g5 f4f5 g5g4 f5f6 e8d8 g7f8
Warning; Bestmove does not match beginning of last PV - move a7a5 from SF-elo3000
Info; info depth 245 seldepth 5 multipv 1 score mate -2 nodes 60359 nps 8622714 hashfull 0 tbhits 0 time 7 pv h6h5 e7d7 c7b8 d7d8
Position; startpos
Moves; c2c4 e7e5 b1c3 g8f6 g1f3 b8c6 g2g3 c6d4 f1g2 d4f3 g2f3 f8b4 f3g2 h7h6 d1b3 b4c5 c3a4 c5d6 e1g1 e8g8 f1d1 f8e8 d2d4 e5d4 d1d4 d8e7 c1d2 e7e2 a1e1 e2h5 e1e8 f6e8 d4e4 e8f6 e4e1 c7c6 d2c3 f6h7 e1e8 d6f8 c3b4 d7d6 b4d6 h5g6 d6b4 g6b1 e8e1 b1g6 e1e8 g6b1 e8e1 b1g6 h2h4 f7f5 b4f8 h7f8 a4c5 f5f4 g3f4 b7b6 c5e4 c8e6 e4g3 a8d8 g2c6 e6f7 c6g2 d8d4 f4f5 g6d6 g3e4 d6e5 b3c3 g7g6 f2f4 e5h8 f5f6 d4d8 b2b4 h8h7 c4c5 f7a2 e4d6 a2e6 f6f7 e6f7 c5c6 f7e6 c6c7 h7d7 c7d8q d7d8 d6e4 d8e7 e4f6 g8f7 f6d5 e7h4 b4b5 e6d7 e1e7 h4e7 d5e7 f7e7 c3g7 e7e8 g2c6 g6g5 f4f5 g5g4 f5f6 e8d8 g7f8 d8c7 f8e7
Finished game 1087 (Stockfish vs SF-elo3000): 1-0 {White mates}
Warning; Bestmove does not match beginning of last PV - move b3b4 from SF-elo3000
Info; info depth 245 seldepth 5 multipv 1 score mate -2 nodes 9016 nps 4508000 hashfull 0 tbhits 0 time 2 pv e1f1 d1b3 f1e1 g4g1
Position; startpos
Moves; c2c4 e7e5 b1c3 g8f6 g1f3 b8c6 g2g3 c6d4 f1g2 d4f3 g2f3 f8b4 f3g2 h7h6 d1b3 b4c5 e1g1 e8g8 e2e3 c5b6 c3d5 f6d5 g2d5 c7c6 d5g2 d7d6 a2a4 a7a5 b3d3 h6h5 b2b3 h5h4 c1a3 b6c5 f2f4 c5a3 a1a3 h4h3 g2h1 f7f5 f1b1 e5e4 d3d4 d8e7 a3a1 f8d8 d2d3 d6d5 c4c5 c8e6 d4e5 d8e8 d3e4 f5e4 e5d4 a8a6 b1b2 b7b6 a1c1 e7f6 g1f2 f6d4 e3d4 b6c5 f2e3 e8b8 d4c5 g8f7 f4f5 e6f5 g3g4 f5g4 c1f1 f7g8 f1b1 g4d7 b1g1 b8b4 g1d1 a6a7 b2b1 g8f7 d1d4 a7b7 b1f1 f7e7 d4b4 b7b4 f1b1 d7f5 e3e2 e7e6 b1b2 e6e5 h1e4 d5e4 b2b1 e4e3 b1g1 e5e4 g1c1 f5g4 e2f1 e4d3 c1a1 g4e2 f1e1 b4g4 a1d1 e2d1
Finished game 1088 (SF-elo3000 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     215.89      24.89     315.52      28.37        576      77.6%      32.3%  [0, 0, 93, 72, 123]
   2 LostFish-steer                186.85      25.15     254.61      28.37        576      74.6%      37.5% [0, 8, 108, 53, 119]
   3 SF-n300k                       -5.43      10.56     -30.95      60.19        128      49.2%      93.8%     [0, 3, 60, 1, 0]
   4 SF-n150k                      -54.74      23.01    -145.78      60.19        128      42.2%      71.9%    [2, 16, 46, 0, 0]
   5 SF-d14                        -94.55      26.87    -222.92      60.19        128      36.7%      51.6%    [3, 28, 33, 0, 0]
   6 SF-d12                       -217.19      42.66    -396.53      60.19        128      22.3%      18.8%   [19, 33, 12, 0, 0]
   7 SF-d10                       -386.27      60.67    -810.39      60.19        128       9.8%       0.0%    [39, 25, 0, 0, 0]
   8 SF-d8                        -620.44     153.78   -1488.19      60.19        128       2.7%       0.0%     [57, 7, 0, 0, 0]
   9 SF-elo3000                   -647.92     176.95   -1606.68      60.19        128       2.3%       0.0%     [58, 6, 0, 0, 0]
  10 SF-elo2600                      -inf        nan       -inf        nan        128       0.0%       0.0%     [64, 0, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 02:51:40 (hours:minutes:seconds)

```
