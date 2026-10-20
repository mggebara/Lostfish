# oracle_d8 — gauntlet result

- Started: 2026-10-20T08:30:42Z, finished: 2026-10-20T09:09:25Z, fastchess exit status: 0
- Config: `experiments/oracle_d8/config.toml`; LostFish commit: `c365fb4`
- Games in games.pgn: 192
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-oracle-d8 option.Steering=true option.Profile=sf-d8 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d8 depth=8 option.Threads=1 option.Hash=16 -each nodes=600000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/oracle_d8/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Started game 184 of 192 (SF-d8 vs LostFish-oracle-d8)
Finished game 183 (LostFish-oracle-d8 vs SF-d8): 1-0 {White mates}
Started game 185 of 192 (Stockfish vs SF-d8)
Finished game 185 (Stockfish vs SF-d8): 1-0 {White mates}
Started game 186 of 192 (SF-d8 vs Stockfish)
Finished game 184 (SF-d8 vs LostFish-oracle-d8): 0-1 {Black wins by adjudication: SyzygyTB}
Started game 187 of 192 (LostFish-oracle-d8 vs Stockfish)
Finished game 186 (SF-d8 vs Stockfish): 0-1 {Black mates}
Started game 188 of 192 (Stockfish vs LostFish-oracle-d8)
Finished game 181 (LostFish-oracle-d8 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 189 of 192 (LostFish-oracle-d8 vs SF-d8)
Finished game 182 (Stockfish vs LostFish-oracle-d8): 1/2-1/2 {Draw by fifty moves rule}
Started game 190 of 192 (SF-d8 vs LostFish-oracle-d8)
Finished game 189 (LostFish-oracle-d8 vs SF-d8): 1-0 {White wins by adjudication: SyzygyTB}
Started game 191 of 192 (Stockfish vs SF-d8)
Finished game 191 (Stockfish vs SF-d8): 1-0 {White mates}
Started game 192 of 192 (SF-d8 vs Stockfish)
Finished game 190 (SF-d8 vs LostFish-oracle-d8): 0-1 {Black mates}
Finished game 188 (Stockfish vs LostFish-oracle-d8): 1-0 {White wins by adjudication: SyzygyTB}
Finished game 187 (LostFish-oracle-d8 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 192 (SF-d8 vs Stockfish): 0-1 {Black mates}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     225.13      55.39     324.47      60.19        128      78.5%      31.2%   [0, 0, 20, 15, 29]
   2 LostFish-oracle-d8            118.38      54.72     142.05      60.19        128      66.4%      31.2%  [0, 12, 20, 10, 22]
   3 SF-d8                        -508.67      96.55   -1097.24      60.19        128       5.1%       0.0%    [51, 13, 0, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:38:42 (hours:minutes:seconds)

```
