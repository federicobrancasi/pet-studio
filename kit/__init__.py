"""Pet Studio kit: tools for making videos, images and new moves with the VS Code pet.

Run commands from the repository root with ``python3 -m kit <command>``.
"""

from pathlib import Path

__version__ = '1.0.0'

class KitError(Exception):
	"""A problem the kit explains itself (bad name, missing file, invalid move...). The command
	line prints these as one ``error:`` line; any other exception shows its full traceback."""


class KitNotFoundError(KitError, FileNotFoundError):
	pass


KIT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = KIT_ROOT.parent
OUT_ROOT = REPO_ROOT / 'out'
MOVES_ROOT = REPO_ROOT / 'moves'
