from __future__ import annotations

from pathlib import Path


def main() -> None:
    scorer_path = Path("app/risk/scorer.py")
    if not scorer_path.exists():
        raise FileNotFoundError(f"Missing scorer module: {scorer_path}")
    print("Compatibility wrappers already live in app/risk/scorer.py; no file changes applied.")


if __name__ == "__main__":
    main()
