import json
from pathlib import Path

class StatsMerger:
    pass


glob_pattern = "*.json"

for stats_path in Path("stats").glob(glob_pattern):
    with open(stats_path, encoding='utf-8') as f:
        stats = json.load(f)

    print(stats)
