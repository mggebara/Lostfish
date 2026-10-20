"""Cheap, engine-free position features (PLAN.md §6 Phase 2).

`extract(board, pov)` returns a float32 vector in `FEATURE_NAMES` order. Signed features are from
`pov`'s point of view; `_us` / `_them` suffixes describe pov's own side and the other side
(`king_zone_attackers_us` = enemy pieces attacking *our* king zone, `hanging_us` = *our* hanging
pieces, ...). Symmetry: `extract(b, c) == extract(b.mirror(), not c)` exactly.

Mining builds opponent clusters with pov = the bot = the side to move, so to match a profile's
clusters call `extract(board, board.turn, ...)` on a position where the opponent is to move, with
evals from the opponent's point of view.
"""

from __future__ import annotations

import chess
import numpy as np

FEATURE_NAMES: list[str] = [
    "material_diff",  # pawn units (P1 N3 B3 R5 Q9), us - them
    "phase",  # 1 = all non-pawn material on the board, 0 = bare kings and pawns
    "locked_pawn_pairs",  # rams where neither pawn has a pawn capture
    "pawn_rams",  # head-on blocked pawn pairs
    "open_files",
    "half_open_files_us",  # no pawn of ours, at least one of theirs
    "half_open_files_them",
    "passed_pawns_us",
    "passed_pawns_them",
    "blockaded_passers_us",  # our passed pawns with an enemy piece on the stop square
    "blockaded_passers_them",
    "bishop_pair_us",
    "bishop_pair_them",
    "opposite_bishops",  # one bishop each, on opposite colours
    "imb_rook_vs_two_minors",  # +1 we have R vs their 2 minors, -1 reverse
    "imb_queen_vs_rook_minor",
    "imb_minor_vs_pawns",  # minor vs >= 2 pawns
    "imb_exchange_up",  # R vs minor
    "king_zone_attackers_us",  # enemy non-king pieces attacking our king + adjacent squares
    "king_zone_attackers_them",
    "king_shield_us",  # own pawns on the 2 ranks in front of the king, 3 files
    "king_shield_them",
    "mobility_diff",  # legal moves us - them (null-move flip for the side not to move)
    "hanging_us",  # our N/B/R/Q attacked and undefended
    "hanging_them",
    "checks_available_us",  # direct checking moves (discovered checks ignored)
    "checks_available_them",
    "castling_rights_us",
    "castling_rights_them",
    "depth_gap",  # eval_deep - eval_shallow in cp (each clipped to ±2000), 0 if unknown
    "in_check",  # +1 pov in check, -1 the other side in check
]
N_FEATURES = len(FEATURE_NAMES)
EVAL_CLIP = 2000

_SQ = chess.BB_SQUARES
_FILES = chess.BB_FILES
_PAWN_ATT = chess.BB_PAWN_ATTACKS
_KING_ATT = chess.BB_KING_ATTACKS
_KNIGHT_ATT = chess.BB_KNIGHT_ATTACKS
_DIAG_ATT, _DIAG_MASK = chess.BB_DIAG_ATTACKS, chess.BB_DIAG_MASKS
_RANK_ATT, _RANK_MASK = chess.BB_RANK_ATTACKS, chess.BB_RANK_MASKS
_FILE_ATT, _FILE_MASK = chess.BB_FILE_ATTACKS, chess.BB_FILE_MASKS
_BACKRANK = {chess.WHITE: chess.BB_RANK_1, chess.BLACK: chess.BB_RANK_8}


def _span(color: chess.Color, sq: int, ranks_ahead: int) -> int:
    """Squares on files f-1..f+1 that are 1..ranks_ahead ranks in front of `sq` for `color`."""
    f, r = chess.square_file(sq), chess.square_rank(sq)
    bb = 0
    step = 1 if color == chess.WHITE else -1
    for dr in range(1, ranks_ahead + 1):
        rr = r + step * dr
        if not 0 <= rr <= 7:
            break
        for ff in (f - 1, f, f + 1):
            if 0 <= ff <= 7:
                bb |= _SQ[chess.square(ff, rr)]
    return bb


_FRONT_SPAN = {c: [_span(c, s, 7) for s in chess.SQUARES] for c in chess.COLORS}
_SHIELD = {c: [_span(c, s, 2) for s in chess.SQUARES] for c in chess.COLORS}


def _scan(bb: int):
    while bb:
        lsb = bb & -bb
        yield lsb.bit_length() - 1
        bb ^= lsb


def _sign(cond_pos: bool, cond_neg: bool) -> float:
    return 1.0 if cond_pos else (-1.0 if cond_neg else 0.0)


def extract(
    board: chess.Board,
    pov: chess.Color,
    *,
    eval_deep: int | None = None,
    eval_shallow: int | None = None,
) -> np.ndarray:
    """Feature vector (float32, len(FEATURE_NAMES)). Pure: `board` is not modified."""
    us, them = pov, not pov
    occ = board.occupied
    co = board.occupied_co
    pawns, knights, bishops = board.pawns, board.knights, board.bishops
    rooks, queens, kings = board.rooks, board.queens, board.kings
    minors = knights | bishops
    pc = {c: (pawns & co[c]) for c in chess.COLORS}

    def counts(c: chess.Color) -> tuple[int, int, int, int]:
        m = co[c]
        return (
            (pawns & m).bit_count(),
            (minors & m).bit_count(),
            (rooks & m).bit_count(),
            (queens & m).bit_count(),
        )

    pu, mu, ru, qu = counts(us)
    pt, mt, rt, qt = counts(them)
    material = (pu - pt) + 3 * (mu - mt) + 5 * (ru - rt) + 9 * (qu - qt)
    phase = min(1.0, ((mu + mt) + 2 * (ru + rt) + 4 * (qu + qt)) / 24.0)

    # pawn structure -------------------------------------------------------------------------
    wp, bp = pc[chess.WHITE], pc[chess.BLACK]
    rams_bb = wp & (bp >> 8)
    rams = rams_bb.bit_count()
    locked = 0
    for sq in _scan(rams_bb):
        if not (_PAWN_ATT[chess.WHITE][sq] & bp) and not (_PAWN_ATT[chess.BLACK][sq + 8] & wp):
            locked += 1
    open_files = half_us = half_them = 0
    for fm in _FILES:
        has_us, has_them = pc[us] & fm, pc[them] & fm
        if not has_us and not has_them:
            open_files += 1
        elif not has_us:
            half_us += 1
        elif not has_them:
            half_them += 1

    def passers(c: chess.Color) -> tuple[int, int]:
        enemy_pawns, enemy, span = pc[not c], co[not c], _FRONT_SPAN[c]
        step = 8 if c == chess.WHITE else -8
        n = blocked = 0
        for sq in _scan(pc[c]):
            if not (span[sq] & enemy_pawns):
                n += 1
                if enemy & _SQ[sq + step]:
                    blocked += 1
        return n, blocked

    passed_us, block_us = passers(us)
    passed_them, block_them = passers(them)

    # bishops / imbalances -------------------------------------------------------------------
    def bishop_info(c: chess.Color) -> tuple[bool, int, int]:
        b = bishops & co[c]
        light, dark = b & chess.BB_LIGHT_SQUARES, b & chess.BB_DARK_SQUARES
        return bool(light and dark), b.bit_count(), (1 if light else 0)

    pair_us, nb_us, light_us = bishop_info(us)
    pair_them, nb_them, light_them = bishop_info(them)
    opp_bishops = float(nb_us == 1 and nb_them == 1 and light_us != light_them)
    dp, dm, dr, dq = pu - pt, mu - mt, ru - rt, qu - qt
    imb_r2m = _sign(dq == 0 and dr == 1 and dm == -2, dq == 0 and dr == -1 and dm == 2)
    imb_qrm = _sign(dq == 1 and dr == -1 and dm == -1, dq == -1 and dr == 1 and dm == 1)
    imb_m3p = _sign(
        dq == 0 and dr == 0 and dm == 1 and dp <= -2, dq == 0 and dr == 0 and dm == -1 and dp >= 2
    )
    imb_exch = _sign(dq == 0 and dr == 1 and dm == -1, dq == 0 and dr == -1 and dm == 1)

    # attacks --------------------------------------------------------------------------------
    qr, qb = queens | rooks, queens | bishops
    non_king = occ & ~kings

    def attackers(c: chess.Color, sq: int) -> int:
        return (
            (_KNIGHT_ATT[sq] & knights)
            | (_RANK_ATT[sq][_RANK_MASK[sq] & occ] & qr)
            | (_FILE_ATT[sq][_FILE_MASK[sq] & occ] & qr)
            | (_DIAG_ATT[sq][_DIAG_MASK[sq] & occ] & qb)
            | (_PAWN_ATT[not c][sq] & pawns)
            | (_KING_ATT[sq] & kings)
        ) & co[c]

    ksq = {c: board.king(c) for c in chess.COLORS}

    def king_zone(c: chess.Color) -> tuple[int, int]:
        k = ksq[c]
        if k is None:
            return 0, 0
        att = 0
        for sq in _scan(_KING_ATT[k] | _SQ[k]):
            att |= attackers(not c, sq)
        return (att & non_king).bit_count(), (_SHIELD[c][k] & pc[c]).bit_count()

    kz_us, shield_us = king_zone(us)
    kz_them, shield_them = king_zone(them)

    def hanging(c: chess.Color) -> int:
        n = 0
        for sq in _scan(co[c] & (minors | qr)):
            if attackers(not c, sq) and not attackers(c, sq):
                n += 1
        return n

    hang_us, hang_them = hanging(us), hanging(them)

    # mobility and checks: one legal-move generation per side --------------------------------
    stm = board.turn
    moves_stm = list(board.generate_legal_moves())
    flipped = board.copy(stack=False)
    flipped.turn = not stm
    flipped.ep_square = None
    moves_other = list(flipped.generate_legal_moves())

    def direct_checks(c: chess.Color, moves: list[chess.Move]) -> int:
        k = ksq[not c]
        if k is None or not moves:
            return 0
        diag = _DIAG_ATT[k][_DIAG_MASK[k] & occ]
        ortho = _RANK_ATT[k][_RANK_MASK[k] & occ] | _FILE_ATT[k][_FILE_MASK[k] & occ]
        by_type = (0, _PAWN_ATT[not c][k], _KNIGHT_ATT[k], diag, ortho, diag | ortho, 0)
        n = 0
        for m in moves:
            pt_ = m.promotion or board.piece_type_at(m.from_square) or 0
            if by_type[pt_] & _SQ[m.to_square]:
                n += 1
        return n

    moves_by = {stm: moves_stm, not stm: moves_other}
    mobility = len(moves_by[us]) - len(moves_by[them])
    checks_us = direct_checks(us, moves_by[us])
    checks_them = direct_checks(them, moves_by[them])

    rights = board.clean_castling_rights()
    castle_us = (rights & _BACKRANK[us]).bit_count()
    castle_them = (rights & _BACKRANK[them]).bit_count()

    if eval_deep is not None and eval_shallow is not None:
        gap = max(-EVAL_CLIP, min(EVAL_CLIP, eval_deep)) - max(
            -EVAL_CLIP, min(EVAL_CLIP, eval_shallow)
        )
    else:
        gap = 0
    in_check = (1.0 if stm == us else -1.0) if board.is_check() else 0.0

    return np.array(
        [
            material, phase, locked, rams, open_files, half_us, half_them,
            passed_us, passed_them, block_us, block_them, float(pair_us), float(pair_them),
            opp_bishops, imb_r2m, imb_qrm, imb_m3p, imb_exch, kz_us, kz_them,
            shield_us, shield_them, mobility, hang_us, hang_them, checks_us, checks_them,
            castle_us, castle_them, gap, in_check,
        ],
        dtype=np.float32,
    )  # fmt: skip


def feature_index(name: str) -> int:
    return FEATURE_NAMES.index(name)
