import os

EXTENSIONS = {".py", ".yml", ".yaml", ".json", ".txt", ".conf", ".toml", ".md", ".dockerignore", ".gitignore", ".gitattributes"}
EXTRA_FILES = {"Dockerfile"}
SKIP_DIRS  = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
SKIP_FILES = {"collect_code.py", "project_code.txt", "all_code.txt", "bot_out.txt", "bot_err.txt", "update_server.py", "check_logs.py"}

ROOT   = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "project_code.txt")

# Avval papka strukturasini chizamiz
def build_tree(root):
    tree = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        level = os.path.relpath(dirpath, root).count(os.sep)
        indent = "    " * level
        folder = os.path.basename(dirpath)
        if level == 0:
            tree.append(f"{folder}/")
        else:
            tree.append(f"{indent}├── {folder}/")
        sub = "    " * (level + 1)
        for fname in sorted(filenames):
            if fname in SKIP_FILES:
                continue
            tree.append(f"{sub}├── {fname}")
    return "\n".join(tree)

lines = []
lines.append("LOYIHA STRUKTURASI")
lines.append("=" * 60)
lines.append(build_tree(ROOT))
lines.append("\n\n" + "=" * 60)
lines.append("FAYLLAR MAZMUNI")
lines.append("=" * 60)

file_count = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
    for filename in sorted(filenames):
        if filename in SKIP_FILES:
            continue
        ext = os.path.splitext(filename)[1]
        if ext not in EXTENSIONS and filename not in EXTRA_FILES:
            continue
        filepath = os.path.join(dirpath, filename)
        rel = os.path.relpath(filepath, ROOT)
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            content = f"[O'qib bo'lmadi: {e}]"
        lines.append(f"\n{'=' * 60}")
        lines.append(f"FILE: {rel}")
        lines.append("=" * 60)
        lines.append(content)
        file_count += 1

with open(OUTPUT, "w", encoding="utf-8") as out:
    out.write("\n".join(lines))

size = os.path.getsize(OUTPUT)
print(f"Tayyor! {file_count} ta fayl -> project_code.txt ({size:,} bayt)")
