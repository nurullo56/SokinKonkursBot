import os

SKIP = {"__pycache__", ".git", ".venv", "venv", ".idea", "node_modules"}
SKIP_FILES = {".pyc", ".pyo", ".pyd"}

def tree(path, prefix=""):
    entries = sorted(os.listdir(path))
    entries = [e for e in entries if e not in SKIP]
    for i, name in enumerate(entries):
        full = os.path.join(path, name)
        connector = "+-- " if i == len(entries) - 1 else "|-- "
        print(prefix + connector + name)
        if os.path.isdir(full):
            extension = "    " if i == len(entries) - 1 else "|   "
            tree(full, prefix + extension)

root = os.path.dirname(os.path.abspath(__file__))
print(os.path.basename(root) + "/")
tree(root)
