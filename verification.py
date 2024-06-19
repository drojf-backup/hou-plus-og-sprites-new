
from pathlib import Path
import re

class ExpectedGraphics:
    def __init__(self, line: str, path: str) -> None:
        self.line = line
        self.path = path

# Find double quoted strings, including ones with escaped double quotes
string_regex = re.compile(r'"(?P<data>((\\")|([^"]))*?)"')

def validate_one_script(mod_script_path: str):
    with open(mod_script_path, encoding='utf-8') as f:
        all_lines = f.readlines()

    for line in all_lines:
        for result in string_regex.finditer(line):
            # We don't care about leading/trailing for our purposess
            stripped_path = result.group('data').strip()
            print(stripped_path)

pattern = 'mehagashi.txt' #'*.txt'

# unmodded_input_file = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Installer Test/HigurashiEp10_Data/StreamingAssets/Scripts/mehagashi.txt'
mod_script_dir = 'D:/drojf/large_projects/umineko/HIGURASHI_REPOS/10 hou-plus/Update/'

# TODO: iterate over all top level mod files, use this to determine which paths are probably graphics or not

for modded_script_path in Path(mod_script_dir).glob(pattern):
    validate_one_script(modded_script_path)
