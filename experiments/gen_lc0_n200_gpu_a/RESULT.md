# gen_lc0_n200_gpu_a — gauntlet result

- Started: 2026-10-26T06:06:14Z, finished: 2026-10-26T07:31:19Z, fastchess exit status: 0
- Config: `experiments/gen_lc0_n200_gpu_a/config.toml`; LostFish commit: `b9339bb`
- Games in games.pgn: 5000
- Problems in fastchess output: time losses 0, illegal moves 0, disconnects/crashes 0, warnings 0

## Command

```bash
/home/matthew/dev/LostFish/engines/fastchess -engine cmd=/home/matthew/dev/LostFish/scripts/lostfish name=LostFish-v2-tol0 args=--config\ configs/variants/v2_tol0.yaml nodes=20000 option.Steering=true option.Profile=_generic option.Hash=64 option.SyzygyPath=/home/matthew/dev/LostFish/tb/syzygy -engine cmd=/home/matthew/dev/LostFish/engines/lc0 name=lc0-t1-n200 nodes=200 option.WeightsFile=/home/matthew/dev/LostFish/engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz option.Threads=1 option.BackendOptions=max_batch=256 -each proto=uci -openings file=/home/matthew/dev/LostFish/experiments/openings/8moves_v3.pgn format=pgn order=random plies=16 -srand 20261026 -rounds 2500 -games 2 -repeat -concurrency 6 -ratinginterval 100 -tb /home/matthew/dev/LostFish/tb/syzygy -tbpieces 5 -pgnout file=/home/matthew/dev/LostFish/experiments/gen_lc0_n200_gpu_a/games.pgn notation=san nodes=true 
```

## fastchess final summary

```
Results of LostFish-v2-tol0 vs lc0-t1-n200 (20000 nodes - 200 nodes, 1t, 64MB - NULL, 8moves_v3.pgn):
Elo: 144.47 +/- 6.60, nElo: 235.84 +/- 9.63
LOS: 100.00 %, DrawRatio: 29.24 %, PairsRatio: 11.91
Games: 5000, Wins: 2281, Losses: 314, Draws: 2405, Points: 3483.5 (69.67 %)
Ptnml(0-2): [7, 130, 731, 1153, 479], WL/DD Ratio: 0.30
--------------------------------------------------
Finished match
Total Time: 01:25:05 (hours:minutes:seconds)
```
