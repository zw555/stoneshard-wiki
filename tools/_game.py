# -*- coding: utf-8 -*-
"""Locate the Stoneshard installation directory.

Resolution order:
  1. Environment variable STONESHARD_DIR (explicit override)
  2. A few common Steam library locations

The directory must contain both ``data.win`` and ``StoneShard.exe``.

Usage:
    from _game import game_dir, data_win, game_exe
"""
import os

DATA_WIN_NAME = "data.win"
EXE_NAME = "StoneShard.exe"

# Common install locations. Linux paths are for a Steam library mounted under /mnt.
_CANDIDATES = (
    r"E:\SteamLibrary\steamapps\common\Stoneshard",
    r"D:\SteamLibrary\steamapps\common\Stoneshard",
    r"C:\SteamLibrary\steamapps\common\Stoneshard",
    r"C:\Program Files (x86)\Steam\steamapps\common\Stoneshard",
    r"C:\Program Files\Steam\steamapps\common\Stoneshard",
    "/mnt/e/SteamLibrary/steamapps/common/Stoneshard",
    "/mnt/d/SteamLibrary/steamapps/common/Stoneshard",
)

_HELP = """
Cannot find the Stoneshard installation.

Point the STONESHARD_DIR environment variable at the folder that contains
data.win and StoneShard.exe, for example:

  Windows (cmd)        set STONESHARD_DIR=D:\\SteamLibrary\\steamapps\\common\\Stoneshard
  Windows (PowerShell) $env:STONESHARD_DIR="D:\\SteamLibrary\\steamapps\\common\\Stoneshard"
  Linux / macOS        export STONESHARD_DIR="$HOME/.steam/steam/steamapps/common/Stoneshard"

In the Steam client: right-click Stoneshard -> Manage -> Browse local files.
""".strip()


def _is_game_dir(path):
    return (os.path.isfile(os.path.join(path, DATA_WIN_NAME))
            and os.path.isfile(os.path.join(path, EXE_NAME)))


def game_dir():
    """Return the Stoneshard install directory, or exit with instructions."""
    env = os.environ.get("STONESHARD_DIR")
    if env:
        env = os.path.expanduser(env.strip().strip('"'))
        if _is_game_dir(env):
            return env
        raise SystemExit(
            "STONESHARD_DIR is set to %r but it does not contain %s and %s."
            % (env, DATA_WIN_NAME, EXE_NAME)
        )

    for cand in _CANDIDATES:
        if _is_game_dir(cand):
            return cand

    raise SystemExit(_HELP)


def data_win():
    return os.path.join(game_dir(), DATA_WIN_NAME)


def game_exe():
    return os.path.join(game_dir(), EXE_NAME)


if __name__ == "__main__":
    print(game_dir())
