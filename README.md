# SOLVD nonogram solver

- `nonobp.c`: the core solver in C. It uses line propagation plus guessing with backtracking and restarts.
  Build it with `gcc -O3 -march=native -o nonobp nonobp.c`.
- `psolve.py`: runs several `nonobp` copies in parallel with different settings, takes the first answer, checks it against every clue, and writes the answer as hex.
  Usage: `python3 psolve.py challenge.json answer.json`. It handles any number of boards of any size.
  Set `BIN` at the top of the file to the path of your `nonobp`.
- `main.py` + `common.py`: the 1-minute loop. It logs in to SOLVD, gets a challenge, solves it, submits, then mints through the `baw` CLI (Binance Agentic Wallet).
  The paths in these files are still from my computer (`/workspace/solvd/...`), so change them to match yours.

Benchmarks: one 112x112 tier-6 board in about 5-8 s; four 56x56 boards in about 1.4 s.
