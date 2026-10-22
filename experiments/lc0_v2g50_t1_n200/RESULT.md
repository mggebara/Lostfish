# lc0_v2g50_t1_n200 — gauntlet result

- Started: 2026-10-22T01:08:46Z, finished: 2026-10-22T02:10:51Z, fastchess exit status: 0
- Config: `experiments/lc0_v2g50_t1_n200/config.toml`; LostFish commit: `78e378e`
- Games in games.pgn: 640
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 17

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line1-g50 args=--config\ configs/variants/v2_line1_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line2-g50 args=--config\ configs/variants/v2_line2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_v2g50_t1_n200/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 633 of 640 (LostFish-v2-line1-g50 vs lc0-t1-n200)
Finished game 632 (Stockfish vs LostFish-v2-line1-g50): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 634 of 640 (lc0-t1-n200 vs LostFish-v2-line1-g50)
Finished game 634 (lc0-t1-n200 vs LostFish-v2-line1-g50): 1/2-1/2 {Draw by 3-fold repetition}
Started game 635 of 640 (LostFish-v2-line2-g50 vs Stockfish)
Finished game 627 (LostFish-v2-tol0 vs lc0-t1-n200): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 636 of 640 (Stockfish vs LostFish-v2-line2-g50)
Finished game 635 (LostFish-v2-line2-g50 vs Stockfish): 1-0 {White wins by adjudication: SyzygyTB}
Started game 637 of 640 (LostFish-v2-line2-g50 vs lc0-t1-n200)
Finished game 628 (lc0-t1-n200 vs LostFish-v2-tol0): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 638 of 640 (lc0-t1-n200 vs LostFish-v2-line2-g50)
Finished game 636 (Stockfish vs LostFish-v2-line2-g50): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 639 of 640 (Stockfish vs lc0-t1-n200)
Finished game 637 (LostFish-v2-line2-g50 vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 640 of 640 (lc0-t1-n200 vs Stockfish)
Finished game 633 (LostFish-v2-line1-g50 vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Finished game 638 (lc0-t1-n200 vs LostFish-v2-line2-g50): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 639 (Stockfish vs lc0-t1-n200): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 640 (lc0-t1-n200 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 LostFish-v2-line2-g50          49.18      23.99      88.58      42.56        256      57.0%      47.7%   [0, 19, 61, 41, 7]
   2 LostFish-v2-line1-g50          36.78      21.77      72.55      42.56        256      55.3%      60.9%   [0, 15, 78, 28, 7]
   3 Stockfish                      34.04      23.16      63.06      42.56        256      54.9%      59.4%   [2, 14, 76, 29, 7]
   4 LostFish-v2-tol0               27.20      23.50      49.53      42.56        256      53.9%      53.9%   [2, 19, 69, 33, 5]
   5 lc0-t1-n200                  -156.34      27.71    -274.72      42.56        256      28.9%      23.4%   [22, 70, 30, 6, 0]
--------------------------------------------------
Finished match
Total Time: 01:02:05 (hours:minutes:seconds)

```
