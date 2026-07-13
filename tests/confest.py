# tests/conftest.py
import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
# Это позволит импортировать модули из src/
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))