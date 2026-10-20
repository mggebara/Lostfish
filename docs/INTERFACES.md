# Module interfaces (contract for parallel work)

This file pins the signatures that modules depend on across ownership boundaries. If you need to
change one, change it here first and tell the coordinator. Everything below is Python 3.11,
type-hinted, `python-chess` types. **All centipawn values that leave `engines.py` are from the
`pov` colour's point of view** (LostFish's colour in play). Mate scores map to
`±(MATE_CP - plies)` with `MATE_CP = 32000`.

## lostfish/config.py

```python
def load_config(path: str | Path | None = None) -> Config
# Config is a dataclass tree mirroring configs/lostfish.yaml: .engines, .certify, .steer,
# .budgets[tc_class], .timeman, .profiles, .mining (optional). Unknown keys are kept in .extra.
# Relative paths (engine, syzygy, profiles dir) resolve against the repo root (parent of configs/).
```

## lostfish/engines.py

```python
MATE_CP = 32000

@dataclass
class PVLine:
    move: chess.Move                 # first move of this PV
    cp: int                          # centipawns from `pov`'s POV
    mate: int | None                 # signed mate distance in moves from `pov`, if any
    depth: int
    seldepth: int | None
    nodes: int
    pv: list[chess.Move]
    rank: int                        # 1-based MultiPV rank (1 = best)
    eval_by_depth: dict[int, int]    # depth -> cp (pov); filled only when trajectory=True, rank-1 only
    best_by_depth: dict[int, chess.Move]  # depth -> best move; same conditions

class Engine:
    def __init__(self, path: str, *, hash_mb: int = 64, threads: int = 1,
                 syzygy_path: str | None = None, name: str = "sf") -> None: ...
    def new_game(self) -> None: ...            # ucinewgame + isready
    def analyse(self, board: chess.Board, *, nodes: int | None = None, depth: int | None = None,
                multipv: int = 1, pov: chess.Color | None = None,
                trajectory: bool = False) -> list[PVLine]: ...
        # Exactly one of nodes/depth. Returns lines sorted by rank. pov defaults to board.turn.
        # If the position has no legal moves, returns [].
    def close(self) -> None: ...

class EnginePool:
    def __init__(self, path: str, n: int, **engine_kwargs) -> None: ...   # created once, persistent
    engines: list[Engine]
    def new_game(self) -> None: ...
    def close(self) -> None: ...
```

## lostfish/timeman.py

```python
@dataclass
class GoParams:            # parsed `go` line; None where absent
    wtime: int | None; btime: int | None; winc: int | None; binc: int | None
    movestogo: int | None; movetime: int | None; nodes: int | None; depth: int | None
    infinite: bool

@dataclass
class Budget:
    tc_class: str          # "bullet" | "blitz" | "rapid"
    certify_nodes: int
    eval_nodes: int
    k: int
    proxy_depth_cap: int
    soft_ms: int           # target wall time for the whole move
    hard_ms: int           # never exceed
    clock_fraction: float  # remaining/initial estimate, 0..1 (1.0 when unknown)

def classify_tc(base_ms: int, inc_ms: int) -> str
def plan(go: GoParams, color: chess.Color, cfg: Config, *, ply: int = 0) -> Budget
# `go nodes N` -> certify_nodes = N exactly (needed for equal-node gauntlets).
# `go depth D` -> certify_nodes derived from nps estimate; `go movetime` -> soft=hard=movetime - reserve.
```

## lostfish/profiles.py

```python
@dataclass
class WeakCluster:
    label: str
    centroid: list[float]        # in features.FEATURE_NAMES order (standardised units, see .scale)
    scale: list[float]           # per-feature std used for standardisation
    uplift: float                # cluster blunder rate / base blunder rate
    blunder_rate: float
    n: int

@dataclass
class Profile:
    name: str                    # lichess username, lowercase; "_generic" for the fallback
    version: int                 # schema version, 1
    built_at: str                # ISO date
    n_games: int
    n_positions: int
    rating: int | None
    proxy: str                   # "stockfish_depth"
    effective_depth: int         # argmax of depth_agreement
    depth_agreement: dict[int, float]   # depth -> top-1 agreement in [0,1]
    base_blunder_rate: float
    weak_clusters: list[WeakCluster]
    openings: list[dict]         # [{"eco":..., "name":..., "moves": "e4 e5 ...", "count": n, "score": 0..1}]
    notes: dict                  # free-form

def load_profile(name: str | None, cfg: Config) -> Profile      # never raises; falls back to _generic, then to a built-in default
def save_profile(profile: Profile, cfg: Config) -> Path
def parse_uci_opponent(value: str) -> tuple[str | None, int | None, str | None]
    # lichess-bot sends "<title|none> <rating|none> <computer|human> <name...>"; returns (name, rating, kind)
```

## lostfish/features.py

```python
FEATURE_NAMES: list[str]    # fixed order; ~20-30 cheap features (see PLAN.md §6 Phase 2 list)
def extract(board: chess.Board, pov: chess.Color, *, eval_deep: int | None = None,
            eval_shallow: int | None = None) -> np.ndarray     # float32, len(FEATURE_NAMES); depth_gap feature = eval_deep - eval_shallow (0 if unknown)
```

## lostfish/certify.py

```python
@dataclass
class Candidate:
    move: chess.Move; cp: int; rank: int; pv: list[chess.Move]
@dataclass
class Certified:
    best: Candidate; candidates: list[Candidate]; tolerance_cp: int; eval_by_depth: dict[int, int]

def tolerance_policy(best_cp: int, eval_by_depth: dict[int, int], clock_fraction: float, cfg: Config) -> int
def certify(lines: list[PVLine], tolerance_cp: int) -> Certified              # pure; candidates = lines within tolerance of best, always includes best
def certify_position(engine: Engine, board: chess.Board, pov: chess.Color, budget: Budget, cfg: Config) -> Certified
```

## lostfish/opponent.py

```python
class OpponentModel(Protocol):
    def predict_reply(self, board: chess.Board, *, top_n: int = 2) -> list[tuple[chess.Move, float]]  # weights sum to 1

class StockfishDepthProxy:
    def __init__(self, engine: Engine, depth: int) -> None: ...
```

## lostfish/steer.py

```python
@dataclass
class Scored:
    candidate: Candidate
    expected_eval: int                      # Σ w_i · eval_after_reply_i  (pov)
    weakness: float                         # profile uplift match of the position after our move
    score: float                            # expected_eval + lambda * weakness_cp
    replies: list[tuple[chess.Move, float, int]]   # (reply, weight, eval_after)

def pick(board: chess.Board, certified: Certified, profile: Profile, opponent: OpponentModel,
         evaluator: Engine, budget: Budget, cfg: Config) -> tuple[chess.Move, list[Scored]]
# Never returns a move outside certified.candidates. On any exception returns certified.best.move.
```

## Player protocol (what uci.py drives)

```python
class Player(Protocol):
    def new_game(self) -> None: ...
    def set_opponent(self, name: str | None, rating: int | None) -> None: ...
    def choose(self, board: chess.Board, budget: Budget) -> tuple[chess.Move, dict]: ...
        # dict is the telemetry record body (candidates, chosen, reason, timings); uci.py adds fen/ts/elapsed.
        # Must return a legal move; if the board has no legal moves, uci.py never calls choose().
    def close(self) -> None: ...

# lostfish/passthrough.py (agent A): class PassthroughPlayer(cfg)  -> Stockfish best move at budget.certify_nodes
# lostfish/play.py        (agent C): class SteeringPlayer(cfg)     -> certify -> proxy -> exploit search -> steer.pick
# uci.py constructs PassthroughPlayer when option Steering=false, SteeringPlayer when true (import lazily;
# if lostfish.play is missing or fails to import, fall back to PassthroughPlayer and print `info string`).
```

## lostfish/telemetry.py

```python
def log_move(record: dict, path: str | Path = "logs/moves.jsonl") -> None   # one JSON line, append
# record keys: ts, fen, opponent, tc_class, budget, candidates [{move,cp,rank,score?}], chosen, reason, elapsed_ms
```

## Ownership (parallel session)

| Area | Owner | Files |
| --- | --- | --- |
| Phase 0 engine | agent A | `lostfish/{config,engines,timeman,telemetry,passthrough,uci}.py`, `scripts/{lostfish,run_gauntlet.sh,run_lichess_bot.sh}`, `experiments/smoke/`, `tests/test_{uci,engines,timeman,config}.py` |
| Mining + profiles | agent B | `mining/*`, `lostfish/{features,profiles}.py`, `profiles/`, `tests/test_{features,profiles,mining_*}.py` |
| Steering | agent C | `lostfish/{certify,opponent,steer,play}.py`, `tests/test_{certify,steer,opponent}.py` |

Shared files: `configs/lostfish.yaml` (append your own top-level section only), `pyproject.toml`
(do not add dependencies without asking). Do not run `git add`/`git commit`; the coordinator commits.
