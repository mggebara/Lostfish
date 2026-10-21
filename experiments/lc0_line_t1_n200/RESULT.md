# lc0_line_t1_n200 — gauntlet result

- Started: 2026-10-21T04:09:02Z, finished: 2026-10-21T05:02:37Z, fastchess exit status: 0
- Config: `experiments/lc0_line_t1_n200/config.toml`; LostFish commit: `327cca7`
- Games in games.pgn: 640
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-tol0 args=--config\ configs/variants/tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-line1 nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-line2 args=--config\ configs/variants/line2.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_line_t1_n200/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 637 of 640 (LostFish-line2 vs lc0-t1-n200)
Finished game 636 (Stockfish vs LostFish-line2): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 638 of 640 (lc0-t1-n200 vs LostFish-line2)
Finished game 628 (lc0-t1-n200 vs LostFish-tol0): 0-1 {Black mates}
Started game 639 of 640 (Stockfish vs lc0-t1-n200)
Finished game 633 (LostFish-line1 vs lc0-t1-n200): 1-0 {White mates}
Started game 640 of 640 (lc0-t1-n200 vs Stockfish)
Finished game 637 (LostFish-line2 vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 639 (Stockfish vs lc0-t1-n200): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 640 (lc0-t1-n200 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     161.32      27.25     290.71      42.56        256      71.7%      25.0%   [0, 4, 32, 69, 23]
   2 LostFish-tol0                 -12.22      27.53     -18.95      42.56        256      48.2%      42.2%   [8, 31, 54, 32, 3]
   3 LostFish-line2                -15.06      29.00     -22.26      42.73        254      47.8%      38.6%   [6, 39, 49, 26, 7]
   4 LostFish-line1                -40.90      28.99     -60.76      42.56        256      44.1%      37.5%   [9, 44, 48, 22, 5]
   5 lc0-t1-n200                   -85.10      31.23    -121.55      42.73        254      38.0%      27.6%  [17, 52, 35, 21, 2]
--------------------------------------------------
Finished game 638 (lc0-t1-n200 vs LostFish-line2): 1/2-1/2 {Draw by fifty moves rule}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     161.32      27.25     290.71      42.56        256      71.7%      25.0%   [0, 4, 32, 69, 23]
   2 LostFish-tol0                 -12.22      27.53     -18.95      42.56        256      48.2%      42.2%   [8, 31, 54, 32, 3]
   3 LostFish-line2                -14.94      28.77     -22.17      42.56        256      47.9%      39.1%   [6, 39, 50, 26, 7]
   4 LostFish-line1                -40.90      28.99     -60.76      42.56        256      44.1%      37.5%   [9, 44, 48, 22, 5]
   5 lc0-t1-n200                   -84.41      30.98    -120.95      42.56        256      38.1%      28.1%  [17, 52, 36, 21, 2]
--------------------------------------------------
Finished match
Total Time: 00:53:35 (hours:minutes:seconds)

```
