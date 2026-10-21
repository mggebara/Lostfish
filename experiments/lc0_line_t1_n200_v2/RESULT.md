# lc0_line_t1_n200_v2 — gauntlet result

- Started: 2026-10-21T05:33:21Z, finished: 2026-10-21T06:28:16Z, fastchess exit status: 0
- Config: `experiments/lc0_line_t1_n200_v2/config.toml`; LostFish commit: `73bf911`
- Games in games.pgn: 640
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-tol0 args=--config\ configs/variants/tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-line1 nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-line2 args=--config\ configs/variants/line2.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_line_t1_n200_v2/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 637 of 640 (LostFish-line2 vs lc0-t1-n200)
Finished game 634 (lc0-t1-n200 vs LostFish-line1): 1/2-1/2 {Draw by 3-fold repetition}
Started game 638 of 640 (lc0-t1-n200 vs LostFish-line2)
Finished game 633 (LostFish-line1 vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 639 of 640 (Stockfish vs lc0-t1-n200)
Finished game 636 (Stockfish vs LostFish-line2): 0-1 {Black mates}
Started game 640 of 640 (lc0-t1-n200 vs Stockfish)
Finished game 638 (lc0-t1-n200 vs LostFish-line2): 0-1 {Black wins by adjudication: SyzygyTB}
Finished game 640 (lc0-t1-n200 vs Stockfish): 0-1 {Black wins by adjudication: SyzygyTB}
Finished game 639 (Stockfish vs lc0-t1-n200): 1/2-1/2 {Draw by adjudication: SyzygyTB}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     166.37      29.50     279.45      42.56        256      72.3%      25.0%   [0, 5, 32, 63, 28]
   2 LostFish-tol0                   5.43      29.44       7.87      42.56        256      50.8%      39.8%   [8, 28, 51, 34, 7]
   3 LostFish-line2                -20.54      25.17     -35.01      42.73        254      47.0%      46.5%   [6, 33, 59, 28, 1]
   4 LostFish-line1                -50.57      26.44     -82.74      42.56        256      42.8%      39.1%   [8, 46, 50, 23, 1]
   5 lc0-t1-n200                   -92.40      29.65    -139.95      42.73        254      37.0%      34.6%  [17, 50, 44, 14, 2]
--------------------------------------------------
Finished game 637 (LostFish-line2 vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     166.37      29.50     279.45      42.56        256      72.3%      25.0%   [0, 5, 32, 63, 28]
   2 LostFish-tol0                   5.43      29.44       7.87      42.56        256      50.8%      39.8%   [8, 28, 51, 34, 7]
   3 LostFish-line2                -19.02      25.14     -32.32      42.56        256      47.3%      46.1%   [6, 33, 59, 29, 1]
   4 LostFish-line1                -50.57      26.44     -82.74      42.56        256      42.8%      39.1%   [8, 46, 50, 23, 1]
   5 lc0-t1-n200                   -93.10      29.48    -141.36      42.56        256      36.9%      34.4%  [17, 51, 44, 14, 2]
--------------------------------------------------
Finished match
Total Time: 00:54:54 (hours:minutes:seconds)

```
