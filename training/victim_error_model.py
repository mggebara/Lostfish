"""Victim-error predictor: does the victim (lc0 T1@200) blunder from this position? (learning plan step 2)

    python -m training.victim_error_model --data data/victim_errors/lc0-t1-n200.parquet --epochs 10

Input: 18 planes (own/opp pieces x6, castling x4, en passant, fifty-move, side-to-move marker) with the board
flipped so the victim (side to move) always plays "up". Targets from mining/victim_errors.py: blunder = loss >= 100
(BCE head) and log1p(max(loss, 0)) (Huber head). Split by game. Reports AUC against two cheap baselines that need no
training: the same-position depth-10 Stockfish loss (`baseline_loss`) and |cp_best|. Saves a TorchScript-free
state_dict + config to data/models/ and the validation predictions for analysis. PyTorch on MPS/CUDA/CPU.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import chess
import numpy as np
import pandas as pd
import torch
from torch import nn

PLANES = 18
BLUNDER_CP = 100


# --- encoding ------------------------------------------------------------------------------------


def encode(board: chess.Board) -> np.ndarray:
    """(18, 8, 8) uint8 planes from the side to move's point of view (board flipped for black)."""
    x = np.zeros((PLANES, 8, 8), dtype=np.uint8)
    us = board.turn
    flip = us == chess.BLACK
    for sq, piece in board.piece_map().items():
        r, f = chess.square_rank(sq), chess.square_file(sq)
        if flip:
            r = 7 - r
        plane = (0 if piece.color == us else 6) + piece.piece_type - 1
        x[plane, r, f] = 1
    them = not us
    x[12] = board.has_kingside_castling_rights(us)
    x[13] = board.has_queenside_castling_rights(us)
    x[14] = board.has_kingside_castling_rights(them)
    x[15] = board.has_queenside_castling_rights(them)
    if board.ep_square is not None:
        r, f = chess.square_rank(board.ep_square), chess.square_file(board.ep_square)
        x[16, 7 - r if flip else r, f] = 1
    x[17] = min(board.halfmove_clock, 100) * 255 // 100
    return x


def encode_fens(fens: list[str]) -> np.ndarray:
    out = np.zeros((len(fens), PLANES, 8, 8), dtype=np.uint8)
    for i, fen in enumerate(fens):
        out[i] = encode(chess.Board(fen))
    return out


# --- model ---------------------------------------------------------------------------------------


class Block(nn.Module):
    def __init__(self, ch: int) -> None:
        super().__init__()
        self.c1 = nn.Conv2d(ch, ch, 3, padding=1, bias=False)
        self.b1 = nn.BatchNorm2d(ch)
        self.c2 = nn.Conv2d(ch, ch, 3, padding=1, bias=False)
        self.b2 = nn.BatchNorm2d(ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = torch.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        return torch.relu(x + y)


class VictimErrorNet(nn.Module):
    def __init__(self, ch: int = 64, blocks: int = 6, hidden: int = 256) -> None:
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(PLANES, ch, 3, padding=1, bias=False), nn.BatchNorm2d(ch), nn.ReLU()
        )
        self.body = nn.Sequential(*[Block(ch) for _ in range(blocks)])
        self.head = nn.Sequential(
            nn.Conv2d(ch, 8, 1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(8 * 64, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2),  # [blunder logit, log1p(loss)]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.body(self.stem(x)))


# --- metrics -------------------------------------------------------------------------------------


def auc(score: np.ndarray, label: np.ndarray) -> float:
    """ROC AUC by rank statistic (ties averaged)."""
    pos, neg = label.astype(bool), ~label.astype(bool)
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=np.float64)
    s = score[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


# --- training ------------------------------------------------------------------------------------


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def split_by_game(df: pd.DataFrame, val_frac: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    games = df["game_id"].unique()
    rng = np.random.default_rng(seed)
    rng.shuffle(games)
    n_val = max(1, int(len(games) * val_frac))
    val_games = set(games[:n_val])
    is_val = df["game_id"].isin(val_games).to_numpy()
    return np.flatnonzero(~is_val), np.flatnonzero(is_val)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="data/models")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--channels", type=int, default=64)
    ap.add_argument("--blocks", type=int, default=6)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-rows", type=int, default=0, help="subsample for smoke tests (0 = all)")
    ap.add_argument(
        "--min-pieces", type=int, default=7, help="drop tablebase-range positions (< this)"
    )
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    args = ap.parse_args(argv)

    df = pd.read_parquet(args.data)
    df = df[(df["pieces"] >= args.min_pieces) & df["best"].notna()].reset_index(drop=True)
    if args.max_rows and len(df) > args.max_rows:
        df = df.sample(args.max_rows, random_state=args.seed).reset_index(drop=True)
    tr, va = split_by_game(df, args.val_frac, args.seed)
    y_bl = (df["loss"].to_numpy() >= BLUNDER_CP).astype(np.float32)
    y_lg = np.log1p(np.clip(df["loss"].to_numpy(), 0, 3000)).astype(np.float32)
    _log(
        f"{len(df)} positions, {df['game_id'].nunique()} games; train {len(tr)} / val {len(va)}; "
        f"blunder rate {y_bl.mean():.3f}; device {args.device}"
    )
    t0 = time.monotonic()
    X = encode_fens(df["fen"].tolist())
    _log(f"encoded in {time.monotonic() - t0:.0f}s")

    dev = torch.device(args.device)
    Xt = torch.from_numpy(X)
    yb, yl = torch.from_numpy(y_bl), torch.from_numpy(y_lg)
    model = VictimErrorNet(args.channels, args.blocks).to(dev)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * (len(tr) // args.batch + 1)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=max(steps, 1))
    pos_w = torch.tensor([(1 - y_bl[tr].mean()) / max(y_bl[tr].mean(), 1e-3)], device=dev)
    bce = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    hub = nn.HuberLoss()

    def predict(idx: np.ndarray) -> np.ndarray:
        model.eval()
        outs = []
        with torch.no_grad():
            for i in range(0, len(idx), 2048):
                xb = Xt[idx[i : i + 2048]].to(dev).float()
                outs.append(model(xb).cpu().numpy())
        model.train()
        return np.concatenate(outs)

    base_bl, base_cp = df["baseline_loss"].to_numpy(), np.abs(df["cp_best"].to_numpy())
    _log(
        f"baselines (val AUC for blunder>={BLUNDER_CP}): depth-10 SF loss {auc(base_bl[va], y_bl[va]):.3f}, "
        f"|cp_best| {auc(base_cp[va], y_bl[va]):.3f}, chance 0.500; params {n_params / 1e6:.2f}M"
    )
    best = {"auc": -1.0}
    rng = np.random.default_rng(args.seed)
    for epoch in range(1, args.epochs + 1):
        perm = rng.permutation(tr)
        tot, nb = 0.0, 0
        for i in range(0, len(perm), args.batch):
            idx = perm[i : i + args.batch]
            xb = Xt[idx].to(dev).float()
            out = model(xb)
            loss = bce(out[:, 0], yb[idx].to(dev)) + hub(out[:, 1], yl[idx].to(dev))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            tot, nb = tot + float(loss.detach()), nb + 1
        p = predict(va)
        a = auc(p[:, 0], y_bl[va])
        rho = spearman(p[:, 1], y_lg[va])
        _log(
            f"epoch {epoch}: train loss {tot / max(nb, 1):.4f}  val AUC {a:.3f}  val spearman(log loss) {rho:.3f}"
        )
        if a > best["auc"]:
            best = {"auc": a, "spearman": rho, "epoch": epoch}
            out_dir = Path(args.out)
            out_dir.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "channels": args.channels,
                    "blocks": args.blocks,
                    "planes": PLANES,
                },
                out_dir / "victim_error_lc0-t1-n200.pt",
            )
            pd.DataFrame(
                {
                    "game_id": df["game_id"].to_numpy()[va],
                    "ply": df["ply"].to_numpy()[va],
                    "loss": df["loss"].to_numpy()[va],
                    "p_blunder": 1 / (1 + np.exp(-p[:, 0])),
                    "pred_log_loss": p[:, 1],
                    "baseline_loss": base_bl[va],
                }
            ).to_parquet(out_dir / "victim_error_val_preds.parquet", index=False)
    summary = {
        "data": args.data,
        "positions": len(df),
        "games": int(df["game_id"].nunique()),
        "blunder_rate": float(y_bl.mean()),
        "baseline_auc_depth10_loss": auc(base_bl[va], y_bl[va]),
        "baseline_auc_abs_cp": auc(base_cp[va], y_bl[va]),
        "best": best,
        "params": n_params,
        "epochs": args.epochs,
        "channels": args.channels,
        "blocks": args.blocks,
    }
    (Path(args.out) / "victim_error_summary.json").write_text(json.dumps(summary, indent=1))
    _log(
        f"best val AUC {best['auc']:.3f} (epoch {best.get('epoch')}); summary -> {args.out}/victim_error_summary.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
