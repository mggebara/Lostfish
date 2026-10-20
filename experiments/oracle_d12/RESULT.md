# oracle_d12 — gauntlet result

- Started: 2026-10-20T09:52:49Z, finished: 2026-10-20T10:40:52Z, fastchess exit status: 0
- Config: `experiments/oracle_d12/config.toml`; LostFish commit: `c365fb4`
- Games in games.pgn: 192
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-oracle-d12 option.Steering=true option.Profile=sf-d12 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d12 depth=12 option.Threads=1 option.Hash=16 -each nodes=600000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/oracle_d12/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Started game 184 of 192 (SF-d12 vs LostFish-oracle-d12)
Finished game 175 (LostFish-oracle-d12 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 185 of 192 (Stockfish vs SF-d12)
Finished game 182 (Stockfish vs LostFish-oracle-d12): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 186 of 192 (SF-d12 vs Stockfish)
Finished game 186 (SF-d12 vs Stockfish): 1/2-1/2 {Draw by 3-fold repetition}
Started game 187 of 192 (LostFish-oracle-d12 vs Stockfish)
Finished game 185 (Stockfish vs SF-d12): 1-0 {White mates}
Started game 188 of 192 (Stockfish vs LostFish-oracle-d12)
Finished game 181 (LostFish-oracle-d12 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 189 of 192 (LostFish-oracle-d12 vs SF-d12)
Finished game 184 (SF-d12 vs LostFish-oracle-d12): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 190 of 192 (SF-d12 vs LostFish-oracle-d12)
Finished game 189 (LostFish-oracle-d12 vs SF-d12): 1-0 {White mates}
Started game 191 of 192 (Stockfish vs SF-d12)
Finished game 188 (Stockfish vs LostFish-oracle-d12): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 192 of 192 (SF-d12 vs Stockfish)
Finished game 190 (SF-d12 vs LostFish-oracle-d12): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 191 (Stockfish vs SF-d12): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 192 (SF-d12 vs Stockfish): 0-1 {Black mates}
Finished game 187 (LostFish-oracle-d12 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                     118.38      33.02     233.78      60.19        128      66.4%      46.9%    [0, 0, 30, 26, 8]
   2 LostFish-oracle-d12            49.18      29.27     102.76      60.19        128      57.0%      51.6%    [0, 7, 33, 23, 1]
   3 SF-d12                       -176.66      31.95    -395.09      60.19        128      26.6%      20.3%    [9, 42, 13, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:48:02 (hours:minutes:seconds)

```
