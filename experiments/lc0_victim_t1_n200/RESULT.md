# lc0_victim_t1_n200 — gauntlet result

- Started: 2026-10-22T03:32:07Z, finished: 2026-10-22T05:00:23Z, fastchess exit status: 0
- Config: `experiments/lc0_victim_t1_n200/config.toml`; LostFish commit: `acee792`
- Games in games.pgn: 160
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-line2-g50 args=--config\ configs/variants/v2_line2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tree2-exact args=--config\ configs/variants/v2_tree2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 8 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_victim_t1_n200/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 157 of 160 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 149 (LostFish-v2-line2-g50 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by 3-fold repetition}
Started game 158 of 160 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 156 (Stockfish vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 159 of 160 (Stockfish vs lc0-t1-n200)
Finished game 157 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 160 of 160 (lc0-t1-n200 vs Stockfish)
Finished game 159 (Stockfish vs lc0-t1-n200): 1-0 {White mates}
Finished game 160 (lc0-t1-n200 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 LostFish-v2-tree2-exact        58.45      47.99     109.87      87.91         60      58.3%      53.3%     [0, 3, 16, 9, 2]
   2 LostFish-v2-tol0               50.79      64.63      69.78      86.48         62      57.3%      45.2%     [2, 3, 14, 8, 4]
   3 Stockfish                      43.66      57.75      65.66      85.12         64      56.2%      53.1%     [0, 6, 17, 4, 5]
   4 LostFish-v2-line2-g50          21.74      56.51      33.13      85.12         64      53.1%      40.6%     [0, 9, 13, 7, 3]
   5 lc0-t1-n200                  -190.85      82.89    -249.74      86.48         62      25.0%      19.4%    [12, 10, 6, 3, 0]
--------------------------------------------------
Finished game 143 (LostFish-v2-tol0 vs LostFish-v2-tree2-exact): 0-1 {Black mates}
Finished game 158 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black wins by adjudication: SyzygyTB}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 LostFish-v2-tree2-exact        65.92      46.44     124.58      85.12         64      59.4%      50.0%    [0, 3, 16, 11, 2]
   2 LostFish-v2-tol0               43.66      63.77      59.58      85.12         64      56.2%      43.8%     [2, 4, 14, 8, 4]
   3 Stockfish                      43.66      57.75      65.66      85.12         64      56.2%      53.1%     [0, 6, 17, 4, 5]
   4 LostFish-v2-line2-g50          21.74      56.51      33.13      85.12         64      53.1%      40.6%     [0, 9, 13, 7, 3]
   5 lc0-t1-n200                  -190.85      80.13    -253.73      85.12         64      25.0%      18.8%    [12, 11, 6, 3, 0]
--------------------------------------------------
Finished match
Total Time: 01:28:15 (hours:minutes:seconds)

```
