# lc0_v2_t1_n200 — gauntlet result

- Started: 2026-10-21T06:39:35Z, finished: 2026-10-21T07:35:04Z, fastchess exit status: 0
- Config: `experiments/lc0_v2_t1_n200/config.toml`; LostFish commit: `da4f1d6`
- Games in games.pgn: 640
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 53

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line1 args=--config\ configs/variants/v2_line1.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line2 args=--config\ configs/variants/v2_line2.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_v2_t1_n200/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 633 of 640 (LostFish-v2-line1 vs lc0-t1-n200)
Finished game 632 (Stockfish vs LostFish-v2-line1): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 634 of 640 (lc0-t1-n200 vs LostFish-v2-line1)
Finished game 628 (lc0-t1-n200 vs LostFish-v2-tol0): 0-1 {Black mates}
Started game 635 of 640 (LostFish-v2-line2 vs Stockfish)
Finished game 634 (lc0-t1-n200 vs LostFish-v2-line1): 1/2-1/2 {Draw by 3-fold repetition}
Started game 636 of 640 (Stockfish vs LostFish-v2-line2)
Finished game 635 (LostFish-v2-line2 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 637 of 640 (LostFish-v2-line2 vs lc0-t1-n200)
Finished game 636 (Stockfish vs LostFish-v2-line2): 1/2-1/2 {Draw by 3-fold repetition}
Started game 638 of 640 (lc0-t1-n200 vs LostFish-v2-line2)
Finished game 633 (LostFish-v2-line1 vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Started game 639 of 640 (Stockfish vs lc0-t1-n200)
Finished game 639 (Stockfish vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Started game 640 of 640 (lc0-t1-n200 vs Stockfish)
Finished game 619 (Stockfish vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 637 (LostFish-v2-line2 vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 638 (lc0-t1-n200 vs LostFish-v2-line2): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 640 (lc0-t1-n200 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 LostFish-v2-tol0               43.66      23.90      78.68      42.56        256      56.2%      53.9%   [0, 18, 69, 32, 9]
   2 Stockfish                      43.66      22.64      83.05      42.56        256      56.2%      60.2%   [0, 14, 77, 28, 9]
   3 LostFish-v2-line1              31.30      25.33      52.98      42.56        256      54.5%      50.8%   [2, 21, 65, 32, 8]
   4 LostFish-v2-line2              25.83      23.99      46.08      42.56        256      53.7%      49.2%   [2, 22, 63, 37, 4]
   5 lc0-t1-n200                  -153.05      29.57    -250.82      42.56        256      29.3%      26.6%   [26, 61, 34, 7, 0]
--------------------------------------------------
Finished match
Total Time: 00:55:29 (hours:minutes:seconds)

```
