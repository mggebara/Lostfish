# oracle_d14 — gauntlet result

- Started: 2026-10-20T10:40:52Z, finished: 2026-10-20T11:32:04Z, fastchess exit status: 0
- Config: `experiments/oracle_d14/config.toml`; LostFish commit: `c365fb4`
- Games in games.pgn: 192
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/Users/matthew/dev/LostFish/engines/fastchess -engine cmd=/Users/matthew/dev/LostFish/scripts/lostfish name=LostFish-oracle-d14 option.Steering=true option.Profile=sf-d14 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=Stockfish option.Threads=1 option.Hash=64 option.SyzygyPath=/Users/matthew/dev/LostFish/tb/syzygy -engine cmd=/Users/matthew/dev/LostFish/engines/stockfish name=SF-d14 depth=14 option.Threads=1 option.Hash=16 -each nodes=600000 proto=uci -openings file=/Users/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261019 -rounds 32 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /Users/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/Users/matthew/dev/LostFish/experiments/oracle_d14/games.pgn notation=san nodes=true -tournament gauntlet -seeds 2 
```

## fastchess final summary

```
Started game 184 of 192 (SF-d14 vs LostFish-oracle-d14)
Finished game 183 (LostFish-oracle-d14 vs SF-d14): 1/2-1/2 {Draw by 3-fold repetition}
Started game 185 of 192 (Stockfish vs SF-d14)
Finished game 182 (Stockfish vs LostFish-oracle-d14): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 186 of 192 (SF-d14 vs Stockfish)
Finished game 181 (LostFish-oracle-d14 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 187 of 192 (LostFish-oracle-d14 vs Stockfish)
Finished game 185 (Stockfish vs SF-d14): 1-0 {White wins by adjudication: SyzygyTB}
Started game 188 of 192 (Stockfish vs LostFish-oracle-d14)
Finished game 186 (SF-d14 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 189 of 192 (LostFish-oracle-d14 vs SF-d14)
Finished game 184 (SF-d14 vs LostFish-oracle-d14): 1/2-1/2 {Draw by 3-fold repetition}
Started game 190 of 192 (SF-d14 vs LostFish-oracle-d14)
Finished game 189 (LostFish-oracle-d14 vs SF-d14): 1/2-1/2 {Draw by 3-fold repetition}
Started game 191 of 192 (Stockfish vs SF-d14)
Finished game 188 (Stockfish vs LostFish-oracle-d14): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Started game 192 of 192 (SF-d14 vs Stockfish)
Finished game 190 (SF-d14 vs LostFish-oracle-d14): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 191 (Stockfish vs SF-d14): 1/2-1/2 {Draw by 3-fold repetition}
Finished game 187 (LostFish-oracle-d14 vs Stockfish): 1/2-1/2 {Draw by adjudication: SyzygyTB}
Finished game 192 (SF-d14 vs Stockfish): 1/2-1/2 {Draw by 3-fold repetition}
--------------------------------------------------
Rank Name                             Elo        +/-       nElo        +/-      Games      Score       Draw           Ptnml(0-2)
   1 Stockfish                      74.40      24.70     187.24      60.19        128      60.5%      60.9%    [0, 0, 39, 23, 2]
   2 LostFish-oracle-d14            32.67      29.35      67.56      60.19        128      54.7%      64.1%    [0, 7, 41, 13, 3]
   3 SF-d14                       -109.33      29.55    -238.42      60.19        128      34.8%      46.9%    [5, 29, 30, 0, 0]
--------------------------------------------------
Finished match
Total Time: 00:51:12 (hours:minutes:seconds)

```
