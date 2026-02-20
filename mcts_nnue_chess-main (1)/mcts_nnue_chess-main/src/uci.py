# UCI protocol implementation (patched for robust time handling)
# from a0lite by Dietrich Kappe (adapted)
#
# Changes:
#  - Parse `go` with wtime/btime/winc/binc/movestogo/movetime in any order
#  - Convert everything to milliseconds for MCTS(timeLimit=...)
#  - Keep stdout UCI-clean (no board diagrams on stdout)
#  - Handle stop/ponderhit/setoption gracefully
#  - Safer parsing of `position` and input lines

import sys
import chess
from mcts import mcts as MCTS

# Tunables
MIN_TIME_MS = 100             # never search less than this per move
DEFAULT_MOVES_TO_GO = 30      # if GUI doesn't provide movestogo
MAX_PCT_PER_MOVE = 5          # cap per-move spend vs remaining clock

def send(msg: str) -> None:
    sys.stdout.write(msg + "\\n")
    sys.stdout.flush()

def _debug(msg: str) -> None:
    # Write any debug to stderr so stdout stays UCI-clean
    sys.stderr.write(msg + "\\n")
    sys.stderr.flush()

def process_position(tokens):
    board = chess.Board()
    # tokens like: ['position', 'startpos', 'moves', 'e2e4', ...]
    # or:         ['position', 'fen', <6-part fen>, 'moves', ...]
    if len(tokens) >= 2 and tokens[1] == 'startpos':
        idx = 2
    elif len(tokens) >= 8 and tokens[1] == 'fen':
        fen = " ".join(tokens[2:8])
        board = chess.Board(fen=fen)
        idx = 8
    else:
        idx = 1  # unknown; keep default startpos

    if idx < len(tokens) and tokens[idx] == 'moves':
        for mv in tokens[idx+1:]:
            board.push_uci(mv)

    # deal with cutechess bug where a drawn position is passed in
    if board.can_claim_draw():
        board.clear_stack()

    return board

def _parse_go_args(args):
    """Return a dict of UCI go parameters. Accepts any order/subset."""
    p = {}
    i = 0
    n = len(args)
    def get_int(j):
        if j < n:
            try:
                return int(args[j])
            except ValueError:
                return None
        return None

    while i < n:
        k = args[i]; i += 1
        if k in ('wtime','btime','winc','binc','movestogo','movetime','depth','nodes'):
            v = get_int(i); i += 1
            if v is not None:
                p[k] = v
        elif k in ('infinite','ponder'):
            p[k] = True
        else:
            # ignore unknown token
            continue
    return p

def _choose_movetime_ms(p, white_to_move: bool) -> int:
    """Convert UCI go params to a single movetime (ms)."""
    # explicit movetime wins
    if 'movetime' in p:
        return max(MIN_TIME_MS, int(p['movetime']))

    rem = p.get('wtime' if white_to_move else 'btime', 0)  # ms
    inc = p.get('winc' if white_to_move else 'binc', 0)    # ms
    mtg = max(1, p.get('movestogo', DEFAULT_MOVES_TO_GO))

    # Simple manager: slice of remaining + part of increment
    budget = rem // mtg + inc // 2

    # Cap at a percentage of remaining time, clamp to minimum
    cap = (rem * MAX_PCT_PER_MOVE) // 100 if rem else budget
    return max(MIN_TIME_MS, min(budget, cap))

def uci_loop(state):
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        tokens = line.split()
        cmd = tokens[0]

        if cmd == "uci":
            send('id name MCTS NNUE Chess')
            send('id author Code Monkey King')
            send('uciok')

        elif cmd == "quit":
            return

        elif cmd == "isready":
            send("readyok")

        elif cmd == "ucinewgame":
            state.board = chess.Board()

        elif cmd == "position":
            state.board = process_position(tokens)

        elif cmd == "setoption":
            # No options supported yet
            continue

        elif cmd in ("stop", "ponderhit"):
            # Our searches are short and non-pondering; ignore gracefully
            continue

        elif cmd == "go":
            params = _parse_go_args(tokens[1:])
            ms = _choose_movetime_ms(params, state.board.turn)

            # If depth/nodes provided without any time, we still set a small time
            if 'depth' in params and 'movetime' not in params and ('wtime' not in params and 'btime' not in params):
                ms = max(ms, 200)

            engine = MCTS(timeLimit=int(ms))
            result = engine.search(state)

            # Some implementations return (best_move, score), others a move only
            if isinstance(result, tuple):
                best_move, score = result
            else:
                best_move, score = result, 0

            try:
                iscore = int(score)
            except Exception:
                iscore = 0

            send(f'info score cp {iscore}')
            send(f'bestmove {best_move}')

        else:
            # be robust to unknown commands
            continue
