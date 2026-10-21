# maia_line_1900_n400 — gauntlet result

- Started: 2026-10-21T05:02:38Z, finished: 2026-10-21T05:21:37Z, fastchess exit status: 0
- Config: `experiments/maia_line_1900_n400/config.toml`; LostFish commit: `73bf911`
- Games in games.pgn: 640
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-tol0 args=--config\ configs/variants/tol0.yaml nodes=20000 option.Steering=true option.Profile=maia-1900 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-line1 nodes=20000 option.Steering=true option.Profile=maia-1900 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-line2 args=--config\ configs/variants/line2.yaml nodes=20000 option.Steering=true option.Profile=maia-1900 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=20000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=maia-1900-n400 nodes=400 option.WeightsFile=/Users/matthew/dev/LostFish/engines/maia/maia-1900.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/maia_line_1900_n400/games.pgn notation=san nodes=true -tournament gauntlet -seeds 4 
```

## fastchess final summary

```
Started game 633 of 640 (LostFish-line1 vs maia-1900-n400)
Finished game 632 (Stockfish vs LostFish-line1): 1-0 {White wins by adjudication: SyzygyTB}
Started game 634 of 640 (maia-1900-n400 vs LostFish-line1)
Finished game 628 (maia-1900-n400 vs LostFish-tol0): 0-1 {Black mates}
Started game 635 of 640 (LostFish-line2 vs Stockfish)
Finished game 635 (LostFish-line2 vs Stockfish): 0-1 {Black mates}
Started game 636 of 640 (Stockfish vs LostFish-line2)
Finished game 627 (LostFish-tol0 vs maia-1900-n400): 1-0 {White mates}
Started game 637 of 640 (LostFish-line2 vs maia-1900-n400)
Finished game 636 (Stockfish vs LostFish-line2): 1-0 {White mates}
Started game 638 of 640 (maia-1900-n400 vs LostFish-line2)
Finished game 633 (LostFish-line1 vs maia-1900-n400): 1-0 {White mates}
Started game 639 of 640 (Stockfish vs maia-1900-n400)
Finished game 634 (maia-1900-n400 vs LostFish-line1): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 640 of 640 (maia-1900-n400 vs Stockfish)
Finished game 637 (LostFish-line2 vs maia-1900-n400): 1-0 {White mates}
Finished game 638 (maia-1900-n400 vs LostFish-line2): 0-1 {Black mates}
Finished game 640 (maia-1900-n400 vs Stockfish): 0-1 {Black wins by adjudication: SyzygyTB}
Finished game 639 (Stockfish vs maia-1900-n400): 1-0 {White mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     241.67      40.96     343.60      42.56        256      80.1%      21.9%   [0, 3, 28, 37, 60]
   2 LostFish-tol0                  96.02      41.99     102.95      42.56        256      63.5%      22.7%  [8, 24, 29, 25, 42]
   3 LostFish-line1                 23.11      40.42      24.52      42.56        256      53.3%      24.2% [12, 38, 31, 15, 32]
   4 LostFish-line2                 14.94      43.20      14.81      42.56        256      52.1%      25.0% [23, 24, 32, 17, 32]
   5 maia-1900-n400               -802.42     225.64   -2486.54      42.56        256       1.0%       0.0%    [123, 5, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:18:59 (hours:minutes:seconds)

```
