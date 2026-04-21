"""
WFC (Wave Function Collapse) implemented as a CP-SAT constraint satisfaction problem.
Also includes a pure-Python WFC reference and random generation for comparison.
"""

import json
import time
import random
import math
from pathlib import Path
from typing import Optional

import numpy as np
from ortools.sat.python import cp_model


def load_tileset(path: str = "tileset.json") -> dict:
    with open(Path(__file__).parent / path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Random generation (baseline)
# ---------------------------------------------------------------------------

def generate_random(rows: int, cols: int, tileset: dict, seed: int = 0) -> np.ndarray:
    rng = random.Random(seed)
    n_tiles = len(tileset["tiles"])
    weights = tileset.get("weights", [1] * n_tiles)
    return np.array(
        [rng.choices(range(n_tiles), weights=weights)[0] for _ in range(rows * cols)]
    ).reshape(rows, cols)


# ---------------------------------------------------------------------------
# Pure WFC (AC-3 propagation + backtracking)
# ---------------------------------------------------------------------------

class PureWFC:
    def __init__(self, rows: int, cols: int, tileset: dict, seed: int = 0):
        self.rows = rows
        self.cols = cols
        n = len(tileset["tiles"])
        rules_raw = tileset["adjacency"]["rules"]
        self.rules = {int(k): v for k, v in rules_raw.items()}
        self.weights = tileset.get("weights", [1.0] * n)
        self.n_tiles = n
        self.rng = random.Random(seed)
        # domain[r][c] = set of possible tile ids
        self.domains = [[set(range(n)) for _ in range(cols)] for _ in range(rows)]
        self.backtracks = 0

    def _neighbors(self, r, c):
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                yield nr, nc

    def _entropy(self, r, c):
        d = self.domains[r][c]
        if len(d) <= 1:
            return -1
        w = [self.weights[t] for t in d]
        s = sum(w)
        return -sum((wi / s) * math.log(wi / s) for wi in w if wi > 0)

    def _propagate(self, r, c) -> bool:
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            for nr, nc in self._neighbors(cr, cc):
                before = len(self.domains[nr][nc])
                allowed = set()
                for t in self.domains[nr][nc]:
                    if any(self.rules[t2][t] for t2 in self.domains[cr][cc]):
                        allowed.add(t)
                self.domains[nr][nc] = allowed
                if not allowed:
                    return False
                if len(allowed) < before:
                    stack.append((nr, nc))
        return True

    def _pick_cell(self):
        best, best_e = None, float("inf")
        for r in range(self.rows):
            for c in range(self.cols):
                if len(self.domains[r][c]) > 1:
                    e = self._entropy(r, c)
                    if e < best_e:
                        best_e, best = e, (r, c)
        return best

    def solve(self) -> Optional[np.ndarray]:
        # iterative backtracking with domain snapshots
        stack = []  # (domains_snapshot, r, c, chosen_tile)

        while True:
            cell = self._pick_cell()
            if cell is None:
                # all collapsed
                grid = np.zeros((self.rows, self.cols), dtype=int)
                for r in range(self.rows):
                    for c in range(self.cols):
                        grid[r][c] = next(iter(self.domains[r][c]))
                return grid

            r, c = cell
            d = list(self.domains[r][c])
            w = [self.weights[t] for t in d]
            chosen = self.rng.choices(d, weights=w)[0]

            # save snapshot
            snap = [[set(self.domains[r2][c2]) for c2 in range(self.cols)] for r2 in range(self.rows)]
            stack.append((snap, r, c, chosen))

            self.domains[r][c] = {chosen}
            ok = self._propagate(r, c)

            while not ok:
                self.backtracks += 1
                if not stack:
                    return None
                snap, br, bc, bad_tile = stack.pop()
                self.domains = [[set(snap[r2][c2]) for c2 in range(self.cols)] for r2 in range(self.rows)]
                self.domains[br][bc].discard(bad_tile)
                if not self.domains[br][bc]:
                    continue
                ok = self._propagate(br, bc)


# ---------------------------------------------------------------------------
# CP-SAT WFC
# ---------------------------------------------------------------------------

class CPSATResult:
    def __init__(self, grid, solve_time, status, backtracks_hint=None):
        self.grid = grid
        self.solve_time = solve_time
        self.status = status
        self.backtracks_hint = backtracks_hint


def solve_cpsat(
    rows: int,
    cols: int,
    tileset: dict,
    seed: int = 0,
    add_connectivity: bool = False,
    min_floor_ratio: float = 0.25,
    timeout_s: float = 15.0,
    randomize: bool = True,
) -> CPSATResult:
    n_tiles = len(tileset["tiles"])
    rules_raw = tileset["adjacency"]["rules"]
    rules = {int(k): v for k, v in rules_raw.items()}
    weights = tileset.get("weights", [1.0] * n_tiles)

    model = cp_model.CpModel()

    # cell[r][c] in [0, n_tiles)
    cells = [[model.NewIntVar(0, n_tiles - 1, f"c_{r}_{c}") for c in range(cols)] for r in range(rows)]

    # adjacency constraints via AddAllowedAssignments (table constraint — efficient)
    allowed_pairs = [(a, b) for a in range(n_tiles) for b in range(n_tiles) if rules[a][b]]
    for r in range(rows):
        for c in range(cols):
            for nr, nc in [(r, c + 1), (r + 1, c)]:
                if nr < rows and nc < cols:
                    model.AddAllowedAssignments(
                        [cells[r][c], cells[nr][nc]], allowed_pairs
                    )

    # global constraint: minimum floor ratio
    floor_id = next(t["id"] for t in tileset["tiles"] if t["name"] == "floor")
    is_floor = []
    for r in range(rows):
        for c in range(cols):
            b = model.NewBoolVar(f"fl_{r}_{c}")
            model.Add(cells[r][c] == floor_id).OnlyEnforceIf(b)
            model.Add(cells[r][c] != floor_id).OnlyEnforceIf(b.Not())
            is_floor.append(b)
    model.Add(sum(is_floor) >= int(min_floor_ratio * rows * cols))

    # global constraint: maximum floor ratio (force variety)
    model.Add(sum(is_floor) <= int(0.65 * rows * cols))

    # objective: weighted tile preference + optional per-cell noise for variety
    int_weights = [int(w * 100) for w in weights]
    rng = random.Random(seed)
    tile_weight_vars = []
    for r in range(rows):
        for c in range(cols):
            w_var = model.NewIntVar(0, max(int_weights) + 50, f"w_{r}_{c}")
            if randomize:
                # per-cell random bonus breaks symmetry → diverse output
                noise = [int_weights[t] + rng.randint(-30, 30) for t in range(n_tiles)]
                noise = [max(0, v) for v in noise]
                model.AddElement(cells[r][c], noise, w_var)
            else:
                model.AddElement(cells[r][c], int_weights, w_var)
            tile_weight_vars.append(w_var)
    model.Maximize(sum(tile_weight_vars))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_s
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 1

    t0 = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - t0

    status_name = solver.StatusName(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        grid = np.array([
            [solver.Value(cells[r][c]) for c in range(cols)]
            for r in range(rows)
        ])
        return CPSATResult(grid, elapsed, status_name)
    return CPSATResult(None, elapsed, status_name)


# ---------------------------------------------------------------------------
# Unified runner
# ---------------------------------------------------------------------------

def run_all(rows=12, cols=12, seed=42, tileset_path="tileset.json") -> dict:
    tileset = load_tileset(tileset_path)

    results = {}

    # Random
    t0 = time.time()
    results["random"] = {
        "grid": generate_random(rows, cols, tileset, seed),
        "time": time.time() - t0,
        "backtracks": 0,
        "status": "done",
    }

    # Pure WFC
    t0 = time.time()
    wfc = PureWFC(rows, cols, tileset, seed)
    grid = wfc.solve()
    results["wfc"] = {
        "grid": grid,
        "time": time.time() - t0,
        "backtracks": wfc.backtracks,
        "status": "done" if grid is not None else "failed",
    }

    # CP-SAT: use smaller grid capped at 8x8 for reasonable solve time
    cpsat_rows, cpsat_cols = min(rows, 8), min(cols, 8)
    r = solve_cpsat(cpsat_rows, cpsat_cols, tileset, seed, min_floor_ratio=0.25, timeout_s=10.0)
    # pad to full size if needed for visual comparison
    if r.grid is not None and (cpsat_rows < rows or cpsat_cols < cols):
        full = np.zeros((rows, cols), dtype=int)
        full[:cpsat_rows, :cpsat_cols] = r.grid
        r.grid = full
    results["cpsat"] = {
        "grid": r.grid,
        "time": r.solve_time,
        "backtracks": None,
        "status": r.status,
        "note": f"solved {cpsat_rows}x{cpsat_cols}" if cpsat_rows < rows else None,
    }

    return results, tileset
