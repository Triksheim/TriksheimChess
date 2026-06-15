# TriksheimChess Py UCI

This folder contains the UCI adapter for TriksheimChess Py. Use it when you want
to load the Python engine in a UCI chess GUI.

## Requirements

- Python 3
Install the project dependencies from the project root:

```sh
cd path/to/TriksheimChessPy
python3 -m pip install -r requirements.txt
```

## Run As A UCI Engine

From the project root, use the launcher for your system.

On macOS/Linux:

```sh
./uci/triksheimchesspy-uci
```

On Windows:

```bat
uci\triksheimchesspy-uci.cmd
```

You can also run the adapter directly:

```sh
python3 uci/uci.py
```

Point your UCI chess GUI at the launcher for your system, or at `uci/uci.py` if
the GUI supports running Python scripts.

## Mode

The adapter always runs in `uci` mode. This mode is separate from the Python
app's difficulty settings.

## Supported Commands

- `uci`
- `isready`
- `ucinewgame`
- `position startpos moves ...`
- `position fen ... moves ...`
- `go depth N`
- `go movetime MS`
- `setoption name Multiprocessing value true`
- `stop`
- `quit`

The engine prints UCI `info` lines with depth, centipawn score, nodes, time, and
principal variation before returning `bestmove`.
