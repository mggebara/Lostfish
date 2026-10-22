# lc0_victim_t1_n50 — gauntlet result

- Started: 2026-10-22T02:10:52Z, finished: 2026-10-22T03:31:24Z, fastchess exit status: 0
- Config: `experiments/lc0_victim_t1_n50/config.toml`; LostFish commit: `8551af1`
- Games in games.pgn: 320
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 13

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line2-g50 args=--config\ configs/variants/v2_line2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tree2-exact args=--config\ configs/variants/v2_tree2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n50 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n50 nodes=50 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 16 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_victim_t1_n50/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 319 of 320 (Stockfish vs lc0-t1-n50)
Finished game 319 (Stockfish vs lc0-t1-n50): 1-0 {White mates}
Started game 320 of 320 (lc0-t1-n50 vs Stockfish)
Finished game 320 (lc0-t1-n50 vs Stockfish): 0-1 {Black wins by adjudication: SyzygyTB}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 LostFish-v2-tree2-exact        87.22      48.35     116.83      61.65        122      62.3%      42.6%   [1, 8, 26, 12, 14]
   2 LostFish-v2-tol0               80.11      48.56     103.62      60.19        128      61.3%      48.4%   [4, 3, 31, 12, 14]
   3 LostFish-v2-line2-g50          75.62      40.03     118.87      60.66        126      60.7%      46.0%    [0, 8, 29, 17, 9]
   4 Stockfish                      55.62      45.19      76.40      60.66        126      57.9%      57.1%    [1, 9, 36, 3, 14]
   5 lc0-t1-n50                   -425.78      82.20    -780.93      60.66        126       7.9%       3.2%    [45, 16, 2, 0, 0]
--------------------------------------------------
Finished game 316 (Stockfish vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 317 (LostFish-v2-tree2-exact vs lc0-t1-n50): 1-0 {White wins by adjudication: SyzygyTB}
Warning; PV continues after threefold repetition - move d1d8 from LostFish-v2-tree2-exact
Info; info depth 21 score cp 1 nodes 20000 time 2914 pv d1e1 e6d5 e1d1 d5e6 d1d8 g6f7 d8d3 f7g6 d3d1 g6f7 d1d4 f7g6 d4d2 g6f7 d2d8
Position; startpos
Moves; c2c4 e7e5 b1c3 b8c6 g1f3 g8f6 g2g3 f8b4 f1g2 e8g8 e1g1 f8e8 d2d3 h7h6 c3d5 b4f8 f3d2 a7a5 b2b3 c6b4 d5f6 d8f6 c1b2 f6d8 a2a3 b4a6 b2c3 c7c6 b3b4 d7d5 c4d5 c6d5 b4a5 d5d4 c3b4 a6b4 a3b4 f8b4 d2c4 a8a7 a1b1 b4a5 b1b5 c8d7 b5b7 a7b7 g2b7 d8c7 b7d5 c7c5 e2e4 d4e3 d1f3 e3f2 f1f2 e8f8 d5f7 g8h8 f3d5 a5b6 c4b6 c5c1 f2f1 c1e3 g1g2 e3d2 f1f2 d7h3 g2h3 d2f2 f7h5 f2b6 d5e5 h8g8 e5e4 g8h8 h5g6 b6f2 e4c6 f2e2 c6d5 e2f1 h3g4 f1c1 g4h3 c1c8 h3g2 c8c1 g2h3 c1f1 h3g4 f1d1 g4h3 d1e2 g6e4 e2d1 d5c5 d1f1 h3g4 f1d1 g4h3 d1f1 h3g4 f1f6 c5d5 f8d8 d5a2 f6g5 g4h3 d8f8 a2e6 g5f6 e6f6 f8f6 h3g2 g7g5 e4f3 f6d6 f3e2 h8g7 g2f2 g7g6 h2h3 g6f6 f2e3 d6a6 e3f2 a6a2 f2e3 f6g6 h3h4 g5h4 g3h4 a2a4 h4h5 g6g5 d3d4 a4a3 e3e4 a3a7 e4e3 a7e7 e3d2 e7a7 d2e3 a7e7 e3d2 e7b7 d2e3 b7a7 e2f3 a7a1 f3e2 a1h1 e2f3 h1h2 e3e4 g5f6 e4e3 h2h4 f3e2 f6g5 e2d1 g5f6 d1e2 f6g5 e2d1 h4h3 e3e4 h3h1 d1e2 h1b1 e4e3 b1b3 e3e4 b3b7 e4e3 b7a7 e2d1 a7a3 e3e4 a3a1 d1e2 a1a8 e4e3 a8a3 e3e4 a3a1 d4d5 a1e1 e4d3 g5f6 d5d6 e1g1 d3d4 g1g5 e2d1 g5a5 d4e4 a5e5 e4d4 e5g5 d4e4 g5g1 d1e2 g1e1 e4d3 f6f7 e2f3 e1e5 d3d4 e5f5 d4e4 f5g5 f3d1 f7e8 e4f4 e8d7 d1a4 d7d6 a4e8 d6d5 e8f7 d5d4 f7g6 g5d5 g6f7 d5d8 f4f5 d8c8 f5f6 d4e4 f7g6 e4f4 f6e6 c8d8 g6f7 d8d3 f7g6 d3d1 g6f7 d1d4 f7g6 d4d2 g6f7 d2d1 f7g6 d1d4 g6f7 d4d3 f7g6 d3d1 g6f7 d1d2 f7g6 d2d8 g6f7 d8d2 f7g6 d2d4 g6f7 d4d1 f7g6
Finished game 309 (LostFish-v2-line2-g50 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by fifty moves rule}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 LostFish-v2-tree2-exact        85.85      46.93     115.46      60.19        128      62.1%      40.6%   [1, 9, 26, 14, 14]
   2 LostFish-v2-tol0               80.11      48.56     103.62      60.19        128      61.3%      48.4%   [4, 3, 31, 12, 14]
   3 LostFish-v2-line2-g50          71.57      39.99     111.33      60.19        128      60.2%      45.3%    [0, 9, 29, 17, 9]
   4 Stockfish                      57.52      44.72      79.32      60.19        128      58.2%      56.2%    [1, 9, 36, 4, 14]
   5 lc0-t1-n50                   -419.54      79.18    -772.15      60.19        128       8.2%       3.1%    [45, 17, 2, 0, 0]
--------------------------------------------------
Finished match
Total Time: 01:20:32 (hours:minutes:seconds)

```
