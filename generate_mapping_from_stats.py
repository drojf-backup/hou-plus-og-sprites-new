import json
from pathlib import Path


def load_and_combine_stats(stats_folder: str) -> dict[str, dict[str, int]]:
    glob_pattern = "*.json"

    combined_stats = {}

    for stats_path in Path(stats_folder).glob(glob_pattern):
        with open(stats_path, encoding='utf-8') as f:
            stats = json.load(f) #type: dict[str, dict[str, int]]

        for mod_name, og_matches in stats.items():
            if mod_name not in combined_stats:
                combined_stats[mod_name] = {}

            combined_og_count = combined_stats[mod_name]
            for og_name, og_count in og_matches.items():
                if og_name in combined_og_count:
                    combined_og_count[og_name] += og_count
                else:
                    combined_og_count[og_name] = og_count

    return combined_stats


stats_folder = 'stats'
stats_temp_folder = 'stats_temp'

for stats_file in Path(stats_temp_folder).glob('*.json'):
    print(f"Some stats files already exist at [{stats_file}]! Please copy these files into the [stats] folder if you want to use them stats files.")
    exit(-1)

combined_stats = load_and_combine_stats(stats_folder)

with open('combined_stats.json', 'w', encoding='utf-8') as f:
    json.dump(combined_stats, f, sort_keys=True, indent=4)

