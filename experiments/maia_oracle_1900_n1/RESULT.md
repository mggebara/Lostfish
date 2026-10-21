# maia_oracle_1900_n1 — gauntlet result

- Started: 2026-10-21T05:21:37Z, finished: 2026-10-21T05:27:06Z, fastchess exit status: 0
- Config: `experiments/maia_oracle_1900_n1/config.toml`; LostFish commit: `73bf911`
- Games in games.pgn: 192
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-maia1900 nodes=100000 option.Steering=true option.Profile=maia-1900 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish nodes=100000 option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/opt/homebrew/bin/lc0 name=maia-1900-n1 nodes=1 option.WeightsFile=/Users/matthew/dev/LostFish/engines/maia/maia-1900.pb.gz option.Threads=1 -each proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/maia_oracle_1900_n1/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Started game 184 of 192 (maia-1900-n1 vs LostFish-maia1900)
Finished game 176 (Stockfish vs LostFish-maia1900): 1/2-1/2 {Draw by 3-fold repetition}
Started game 185 of 192 (Stockfish vs maia-1900-n1)
Finished game 185 (Stockfish vs maia-1900-n1): 1-0 {White mates}
Started game 186 of 192 (maia-1900-n1 vs Stockfish)
Finished game 184 (maia-1900-n1 vs LostFish-maia1900): 0-1 {Black mates}
Started game 187 of 192 (LostFish-maia1900 vs Stockfish)
Finished game 186 (maia-1900-n1 vs Stockfish): 0-1 {Black mates}
Started game 188 of 192 (Stockfish vs LostFish-maia1900)
Finished game 181 (LostFish-maia1900 vs Stockfish): 1/2-1/2 {Draw by 3-fold repetition}
Started game 189 of 192 (LostFish-maia1900 vs maia-1900-n1)
Finished game 189 (LostFish-maia1900 vs maia-1900-n1): 1-0 {White mates}
Started game 190 of 192 (maia-1900-n1 vs LostFish-maia1900)
Finished game 190 (maia-1900-n1 vs LostFish-maia1900): 0-1 {Black mates}
Started game 191 of 192 (Stockfish vs maia-1900-n1)
Finished game 182 (Stockfish vs LostFish-maia1900): 1/2-1/2 {Draw by 3-fold repetition}
Started game 192 of 192 (maia-1900-n1 vs Stockfish)
Finished game 191 (Stockfish vs maia-1900-n1): 1-0 {White mates}
Finished game 187 (LostFish-maia1900 vs Stockfish): 0-1 {Black wins by adjudication: SyzygyTB}
Finished game 192 (maia-1900-n1 vs Stockfish): 0-1 {Black mates}
Finished game 188 (Stockfish vs LostFish-maia1900): 1-0 {White mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     338.04      73.77     505.59      60.19        128      87.5%      14.1%    [0, 0, 9, 14, 41]
   2 LostFish-maia1900              88.74      73.51      77.21      60.19        128      62.5%      14.1%    [9, 14, 9, 0, 32]
   3 maia-1900-n1                    -inf        nan       -inf        nan        128       0.0%       0.0%     [64, 0, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:05:29 (hours:minutes:seconds)

```
