"""Repeat the 1.0 stability suite; exits nonzero on the first failed cycle."""
from __future__ import annotations
import argparse
import subprocess
import sys
import time

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=10)
    args = parser.parse_args()
    started = time.monotonic()
    for cycle in range(1, args.cycles + 1):
        print(f"안정성 반복 {cycle}/{args.cycles}", flush=True)
        result = subprocess.run([sys.executable, "-m", "unittest", "tests.test_stability", "-q"])
        if result.returncode:
            return result.returncode
    print(f"안정성 검사 통과: {args.cycles}회, {time.monotonic()-started:.2f}초")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
