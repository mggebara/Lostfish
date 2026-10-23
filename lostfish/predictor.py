"""Victim-error predictor inference for steering (learning plan step 3).

Loads a checkpoint written by training/victim_error_model.py and scores positions with the victim to move:
`risk(boards)` = probability that the victim blunders (expected-score drop >= 0.10) from each position.
torch is imported lazily and only when `steer.predictor_path` is set, so the engine runs without torch otherwise.
CPU inference with one thread: a 2.5M-parameter net scores K=3 positions in a few milliseconds.
"""

from __future__ import annotations

from pathlib import Path

import chess
import numpy as np


class VictimErrorPredictor:
    def __init__(self, path: str | Path, *, device: str = "cpu") -> None:
        import torch

        from training.victim_error_model import VictimErrorNet, encode

        torch.set_num_threads(1)
        ckpt = torch.load(Path(path), map_location=device, weights_only=True)
        self._encode = encode
        self._torch = torch
        self._dev = torch.device(device)
        self.net = VictimErrorNet(int(ckpt["channels"]), int(ckpt["blocks"])).to(self._dev)
        self.net.load_state_dict(ckpt["state_dict"])
        self.net.eval()
        self.path = str(path)

    def risk(self, boards: list[chess.Board]) -> list[float]:
        """P(victim blunders) for each board (victim = side to move). Terminal positions score 0."""
        if not boards:
            return []
        x = np.stack([self._encode(b) for b in boards]).astype(np.float32)
        with self._torch.no_grad():
            out = self.net(self._torch.from_numpy(x).to(self._dev))
            p = self._torch.sigmoid(out[:, 0]).cpu().numpy()
        return [0.0 if b.is_game_over() else float(v) for b, v in zip(boards, p, strict=True)]
