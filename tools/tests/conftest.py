import sys
from pathlib import Path

# The tools are standalone scripts, not a package; make them importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
