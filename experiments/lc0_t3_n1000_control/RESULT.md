# lc0_t3_n1000_control — gauntlet result

- Started: 2026-10-26T10:25:53Z, finished: 2026-10-26T11:00:10Z, fastchess exit status: 0
- Config: `experiments/lc0_t3_n1000_control/config.toml`; LostFish commit: `805f95b`
- Games in games.pgn: 400
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=_generic option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t3-n1000 nodes=1000 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t3-512x15x16h-distill-swa-2767500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261025 -rounds 200 -games 2 -repeat -concurrency 4 -ratinginterval 20 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/lc0_t3_n1000_control/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tol0 vs lc0-t3-n1000 (20000 nodes - 1000 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: -133.95 +/- 19.00, nElo: -264.87 +/- 34.05
LOS: 0.00 %, DrawRatio: 37.00 %, PairsRatio: 0.02
Games: 400, Wins: 10, Losses: 157, Draws: 233, Points: 126.5 (31.62 %)
Ptnml(0-2): [25, 99, 74, 2, 0], WL/DD Ratio: 0.12
--------------------------------------------------
Finished match
Total Time: 00:34:17 (hours:minutes:seconds)
```
