# victim_error_v1 — can the victim's blunders be predicted from the board?

Data: `mining/victim_errors.py` over 2,443 games vs lc0 T1@200 (118,055 victim moves after filters: ≥7 pieces,
|cp_best| ≤ 1500), labels = Stockfish 100k nodes; blunder = drop in expected score ≥ 0.10 (1.6% of moves).
Protocol: one row per distinct FEN (89,512; deterministic engines replay identical games from shared openings,
24% exact duplicates), split by game 85/15, model = `training/victim_error_model.py` on MPS.

| Predictor | params | val AUC | top-1% blunder rate | top-5% | top-10% |
|---|---|---|---|---|---|
| ResNet 128ch × 8 blocks, 30 epochs | 2.52M | **0.692** | 9.1% (×5.7) | 5.1% (×3.2) | 4.2% (×2.7) |
| ResNet 64ch × 6 blocks, 30 epochs | 0.59M | 0.685 | 6.1% (×3.8) | 5.5% (×3.4) | 4.4% (×2.7) |
| abs(cp_best) (lopsidedness) | – | 0.554 | | | |
| depth-10 Stockfish's own loss on the position | – | 0.505 | | | |

Base blunder rate on validation 1.59%. Both nets were still improving at epoch 30. Leaky protocol (game split
without FEN dedupe) gave 0.670 overall / 0.725 on leaked rows / 0.651 on clean rows for the 12-epoch model —
the numbers above are from the clean protocol. Models: `data/models/{e30,c128b8}/` (gitignored).
