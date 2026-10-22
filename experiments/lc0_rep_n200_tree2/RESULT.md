# lc0_rep_n200_tree2 — gauntlet result

- Started: 2026-10-22T09:10:06Z, finished: 2026-10-22T14:41:14Z, fastchess exit status: 143
- Config: `experiments/lc0_rep_n200_tree2/config.toml`; LostFish commit: `c2831c7`
- Games in games.pgn: 355
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 2

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tree2-exact args=--config\ configs/variants/v2_tree2_g50.yaml nodes=20000 option.Steering=true option.Profile=lc0-t1-n200 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/Users/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261022 -rounds 200 -games 2 -repeat -concurrency 5 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/lc0_rep_n200_tree2/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tree2-exact vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 186.59 +/- 29.01, nElo: 294.03 +/- 37.83
LOS: 100.00 %, DrawRatio: 21.60 %, PairsRatio: 24.40
Games: 324, Wins: 173, Losses: 14, Draws: 137, Points: 241.5 (74.54 %)
Ptnml(0-2): [2, 3, 35, 78, 44], WL/DD Ratio: 0.25
--------------------------------------------------
Started game 332 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 330 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 333 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 325 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White mates}
Started game 334 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 328 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 335 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 331 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Started game 336 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 333 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 337 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 337 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Started game 338 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 336 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black mates}
Started game 339 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 338 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black mates}
Started game 340 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 334 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 341 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 332 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 342 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 335 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 343 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 342 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black mates}
Started game 344 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 339 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1/2-1/2 {Draw by 3-fold repetition}
Started game 345 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 340 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 346 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 343 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White mates}
Started game 347 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 341 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White mates}
Started game 348 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 346 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 349 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 344 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 350 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 345 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 351 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 348 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 352 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 350 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by 3-fold repetition}
Started game 353 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 349 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 354 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 347 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 355 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 352 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 1/2-1/2 {Draw by 3-fold repetition}
Started game 356 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 351 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 357 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 355 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 358 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
Finished game 357 (LostFish-v2-tree2-exact vs lc0-t1-n200): 1-0 {White wins by adjudication: SyzygyTB}
Started game 359 of 400 (LostFish-v2-tree2-exact vs lc0-t1-n200)
Finished game 356 (lc0-t1-n200 vs LostFish-v2-tree2-exact): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 360 of 400 (lc0-t1-n200 vs LostFish-v2-tree2-exact)
scripts/run_gauntlet.sh: line 106: 93265 Terminated: 15          "$FASTCHESS" "${ARGS[@]}"
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
```
