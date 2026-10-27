"""mining.bot_registry bio classification (no network)."""

from __future__ import annotations

from mining.bot_registry import bot_row, classify, markdown


def test_classify_finds_lc0_nets_and_nodes() -> None:
    c = classify("Runs Lc0 0.31 with the BT4 net (BT4-1024x15x32h) at 800 nodes/move on a 3060.")
    assert c["engines"] == ["lc0"] and c["replicable"]
    assert "BT4" in c["nets"] and any(n.startswith("800") for n in c["nodes"])
    c = classify("Maia 1900 (maia-1900, 1 node) via lichess-bot")
    assert c["engines"] == ["maia"] and c["replicable"] and "maia-1900" in c["nets"]


def test_custom_and_stockfish_bots_are_not_replicable() -> None:
    assert classify("Stockfish 17 at depth 12, lichess-bot")["replicable"] is False
    c = classify("My own engine written in Rust, inspired by Leela")
    assert "custom" in c["engines"] and c["replicable"] is False
    assert classify("")["engines"] == [] and classify("")["replicable"] is False


def test_markdown_lists_replicable_bots_by_blitz_rating() -> None:
    users = [
        {
            "id": "a",
            "username": "A",
            "title": "BOT",
            "perfs": {"blitz": {"rating": 2000, "games": 10}},
        },
        {
            "id": "b",
            "username": "B",
            "title": "BOT",
            "perfs": {"blitz": {"rating": 2500, "games": 5}},
        },
        {"id": "c", "username": "C", "title": "BOT", "perfs": {}},
    ]
    rows = [
        bot_row(users[0], "Lc0 T1 at 200 nodes", "2026-10-26"),
        bot_row(users[1], "Maia-1100 | pipes", "2026-10-26"),
        bot_row(users[2], "Stockfish 17", "2026-10-26"),
    ]
    md = markdown(rows)
    body = md.split("|---|")[-1]
    assert body.index("| B |") < body.index("| A |") and "| C |" not in md
    assert "Maia-1100 / pipes" in md and "3 online bots seen, 2 replicable" in md
