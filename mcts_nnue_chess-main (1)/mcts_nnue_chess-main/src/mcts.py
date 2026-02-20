from __future__ import annotations

import ctypes
import math
import os
import random
import sys
import time
from pathlib import Path

import chess

# ------------------------------------------------------------
# Robust, cross‑platform NNUE loader with graceful fallback
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
WEIGHTS_NAME = "nn-c3ca321c51c9.nnue"

_nnue = None  # ctypes handle


def _candidate_lib_paths() -> list[Path]:
    """
    Build candidate shared‑library paths.
    Order: env override → local names → common subfolders.
    """
    override = os.environ.get("NNUEPROBE_PATH")
    if override:
        return [Path(override)]

    sysname = sys.platform
    names: list[str]
    bins: list[Path]

    if sysname.startswith("win"):
        # Accept both names seen in repos
        names = ["nnueprobe.dll", "libnnueprobe.dll"]
        bins = [BASE_DIR, BASE_DIR / "bin", BASE_DIR / "lib", BASE_DIR.parent / "bin"]
    elif sysname == "darwin":
        names = ["libnnueprobe.dylib"]
        bins = [BASE_DIR, BASE_DIR / "lib"]
    else:
        names = ["libnnueprobe.so"]
        bins = [BASE_DIR, BASE_DIR / "lib", BASE_DIR / "build"]

    out: list[Path] = []
    for b in bins:
        for n in names:
            out.append(b / n)
    return out


def _load_nnue() -> None:
    """Try to load NNUE and initialize weights. On failure, leave _nnue=None."""
    global _nnue

    # Select loader per platform
    if sys.platform.startswith("win"):
        Loader = ctypes.WinDLL
    else:
        Loader = ctypes.CDLL

    for p in _candidate_lib_paths():
        if p.exists():
            try:
                # On Windows 3.8+, whitelist DLL directory
                if sys.platform.startswith("win") and hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(str(p.parent))

                lib = Loader(str(p))

                # Optional prototypes (be tolerant if symbols differ)
                try:
                    lib.nnue_init.argtypes = [ctypes.c_char_p]
                    lib.nnue_init.restype = ctypes.c_int
                except Exception:
                    pass
                try:
                    lib.nnue_evaluate_fen.argtypes = [ctypes.c_char_p]
                    lib.nnue_evaluate_fen.restype = ctypes.c_int
                except Exception:
                    pass

                # Load weights if function & file exist
                w = BASE_DIR / WEIGHTS_NAME
                if hasattr(lib, "nnue_init") and w.exists():
                    lib.nnue_init(str(w).encode("utf-8"))

                _nnue = lib
                return
            except OSError:
                # Try next candidate
                continue

    # If we reach here, NNUE could not be loaded
    _nnue = None


_load_nnue()

# Expose as old name used elsewhere
nnue = _nnue

# ------------------------------------------------------------
# Helper evaluation
# ------------------------------------------------------------
def _static_eval(state) -> int:
    """
    Return a static score. Prefer NNUE if available, else material eval.
    Positive is good for White; negative for Black.
    """
    if nnue is not None and hasattr(nnue, "nnue_evaluate_fen"):
        try:
            return int(nnue.nnue_evaluate_fen(state.board.fen().encode("utf-8")))
        except Exception:
            pass  # fall back if native call fails
    return get_material_score(state)


def randomPolicy(state):
    while not state.is_terminal():
        try:
            action = random.choice(state.generate_states())
        except IndexError:
            raise Exception("Non-terminal state has no possible actions: " + str(state))
        state = state.take_action(action)
    return state.getReward()


# NNUE (or fallback) evaluation
def nnue_policy(state, learner=None):
    # learned value first if a learner is provided
    if learner is not None:
        val = learner.get_value(state.board.fen())
        if val is not None:
            return val

    # terminal/draw cases
    if state.board.is_checkmate():
        return -10000
    elif state.board.is_stalemate():
        return 0
    elif state.board.can_claim_draw():
        return 0
    elif state.board.is_insufficient_material():
        return 0

    score = _static_eval(state)

    # On material imbalance, do a quiescence probe and take the better
    if get_material_score(state) != 0:
        q = quiescence(state, -10000, 10000)
        return max(score, q)

    return score


class treeNode:
    def __init__(self, state, parent):
        self.state = state
        self.isTerminal = state.is_terminal()
        self.isFullyExpanded = self.isTerminal
        self.parent = parent
        self.numVisits = 0
        self.totalReward = 0
        self.children = {}


def get_material_score(state) -> int:
    # material score
    score = 0

    # relative piece values
    material = {
        'P': 100,  'N': 300,  'B': 350,  'R': 500,  'Q': 900,  'K': 1000,
        'p': -100, 'n': -300, 'b': -350, 'r': -500, 'q': -900, 'k': -1000,
    }

    for square in range(64):
        piece = state.board.piece_at(square)
        if piece is not None:
            score += material[str(piece)]
    return score


# Quiescence search using the same static evaluator
def quiescence(state, alpha, beta) -> int:
    stand_pat = _static_eval(state)

    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in state.board.legal_moves:
        if state.board.is_capture(move):
            state.board.push(chess.Move.from_uci(str(move)))
            score = -quiescence(state, -beta, -alpha)
            state.board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
    return alpha


class mcts:
    def __init__(self, timeLimit=None, iterationLimit=None, explorationConstant=1 / math.sqrt(2),
                 rolloutPolicy=nnue_policy):
        if timeLimit is not None and iterationLimit is not None:
            raise ValueError("Cannot have both a time limit and an iteration limit")
        if timeLimit is None and iterationLimit is None:
            raise ValueError("Must have either a time limit or an iteration limit")

        if timeLimit is not None:
            # time taken for each MCTS search in milliseconds
            self.timeLimit = timeLimit
            self.limitType = 'time'
        else:
            if iterationLimit < 1:
                raise ValueError("Iteration limit must be greater than one")
            self.searchLimit = iterationLimit
            self.limitType = 'iterations'
        self.explorationConstant = explorationConstant
        self.rollout = rolloutPolicy

    def search(self, initialState):
        self.root = treeNode(initialState, None)

        if self.limitType == 'time':
            timeLimit = time.time() + self.timeLimit / 1000.0
            while time.time() < timeLimit:
                self.executeRound()
        else:
            for _ in range(self.searchLimit):
                self.executeRound()

        bestChild = self.getBestChild(self.root, 0)
        return self.getAction(self.root, bestChild), -self.rollout(bestChild.state)

    def executeRound(self):
        node = self.selectNode(self.root)
        reward = self.rollout(node.state)
        self.backpropogate(node, reward)

    def selectNode(self, node):
        while not node.isTerminal:
            if node.isFullyExpanded:
                node = self.getBestChild(node, self.explorationConstant)
            else:
                return self.expand(node)
        return node

    def expand(self, node):
        actions = node.state.generate_states()
        for action in actions:
            if action not in node.children:
                newNode = treeNode(node.state.take_action(action), node)
                node.children[action] = newNode
                if len(actions) == len(node.children):
                    node.isFullyExpanded = True
                return newNode
        raise Exception("Should never reach here")

    def backpropogate(self, node, reward):
        turn = -1
        while node is not None:
            node.numVisits += 1
            node.totalReward += reward * turn
            node = node.parent
            turn *= -1

    def getBestChild(self, node, explorationValue):
        bestValue = float("-inf")
        bestNodes = []
        for child in node.children.values():
            nodeValue = (child.totalReward / child.numVisits) + explorationValue * math.sqrt(
                2 * math.log(node.numVisits) / child.numVisits)
            if nodeValue > bestValue:
                bestValue = nodeValue
                bestNodes = [child]
            elif nodeValue == bestValue:
                bestNodes.append(child)
        return random.choice(bestNodes)

    def getAction(self, root, bestChild):
        for action, node in root.children.items():
            if node is bestChild:
                return action
        # Should not happen
        return None
