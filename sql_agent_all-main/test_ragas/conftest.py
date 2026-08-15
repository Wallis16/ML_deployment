import sys
from pathlib import Path

# So `import agent` / `from agent...` resolves regardless of where pytest is
# invoked from — this folder is meant to be runnable standalone.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
