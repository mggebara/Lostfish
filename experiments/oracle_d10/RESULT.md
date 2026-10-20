# oracle_d10 — gauntlet result

- Started: 2026-10-20T09:09:25Z, finished: 2026-10-20T09:52:49Z, fastchess exit status: 0
- Config: `experiments/oracle_d10/config.toml`; LostFish commit: `c365fb4`
- Games in games.pgn: 192
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-oracle-d10 option.Steering=true option.Profile=sf-d10 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d10 depth=10 option.Threads=1 option.Hash=16 -each nodes=600000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/oracle_d10/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Started game 184 of 192 (SF-d10 vs LostFish-oracle-d10)
Finished game 181 (LostFish-oracle-d10 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 185 of 192 (Stockfish vs SF-d10)
Finished game 176 (Stockfish vs LostFish-oracle-d10): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 186 of 192 (SF-d10 vs Stockfish)
Finished game 182 (Stockfish vs LostFish-oracle-d10): 1/2-1/2 {Draw by 3-fold repetition}
Started game 187 of 192 (LostFish-oracle-d10 vs Stockfish)
Finished game 186 (SF-d10 vs Stockfish): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 188 of 192 (Stockfish vs LostFish-oracle-d10)
Finished game 185 (Stockfish vs SF-d10): 1-0 {White mates}
Started game 189 of 192 (LostFish-oracle-d10 vs SF-d10)
Finished game 184 (SF-d10 vs LostFish-oracle-d10): 1/2-1/2 {Draw by 3-fold repetition}
Started game 190 of 192 (SF-d10 vs LostFish-oracle-d10)
Finished game 189 (LostFish-oracle-d10 vs SF-d10): 1-0 {White mates}
Started game 191 of 192 (Stockfish vs SF-d10)
Finished game 190 (SF-d10 vs LostFish-oracle-d10): 0-1 {Black mates}
Started game 192 of 192 (SF-d10 vs Stockfish)
Finished game 191 (Stockfish vs SF-d10): 1-0 {White mates}
Finished game 188 (Stockfish vs LostFish-oracle-d10): 1-0 {White mates}
Finished game 192 (SF-d10 vs Stockfish): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 187 (LostFish-oracle-d10 vs Stockfish): 1-0 {White mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     173.20      45.54     271.27      60.19        128      73.0%      39.1%   [0, 0, 25, 19, 20]
   2 LostFish-oracle-d10           103.38      45.13     147.17      60.19        128      64.5%      43.8%   [0, 7, 28, 14, 15]
   3 SF-d10                       -338.04      58.48    -628.53      60.19        128      12.5%       4.7%    [35, 26, 3, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:43:23 (hours:minutes:seconds)

```
