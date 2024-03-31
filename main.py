import os
import pathlib
import hashlib
import pickle
from pathlib import Path
import shutil
import re
import csv
import subprocess
from typing import List

# assume outputLineAll is always a dummy (sometimes it's not, but this simplification should be OK)
outputLineAll = re.compile(r"OutputLineAll\([^;]*;")

outputLineRegex = re.compile(r"OutputLine\(\s*[^,]*,\s*\"(.*)\"\s*,")

ogSpritePathCharacterNameRegex = re.compile(r'"sprites/([^/]+)')

modSpritePathCharacterNameRegex = re.compile(r'"((?:sprite)|(?:portrait))/([a-zA-Z]*)')

# unmodded_input_file = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Installer Test/HigurashiEp10_Data/StreamingAssets/Scripts/mehagashi.txt'
mod_script_dir = 'C:/drojf/large_projects/umineko/HIGURASHI_REPOS/10 hou-plus/Update/'
mod_script_file = 'mehagashi.txt'

modded_input_file = os.path.join(mod_script_dir, mod_script_file)

# def get_output_line_first_text(line):
#     match = outputLineRegex.search(line)
#     if match:
#         text = match.group(1)
#         text = text.replace('\\n', '')
#         if text:
#             return text

#     return None

RENA = 'rena'
KEIICHI = 'keiichi'
SHION = 'shion'
RIKA = 'rika'
HANYU = 'hanyu'
SATOKO = 'satoko'
MION = 'mion'
IRIE = 'irie'
MOB_CHARACTER = 'mob'
KAMEDA = 'kameda'


mod_to_name = {
    're': RENA,
    'si': SHION,
    'kei': KEIICHI,
    'ri': RIKA,
    'ha': HANYU,
    'sa': SATOKO,
    'me': MION,
    'iri': IRIE,
    'mo': MOB_CHARACTER,
    'kameda': KAMEDA
}

def get_vanilla_only(log_lines):

    diff_lines = []

    got_commit = False
    got_file_start = False

    for line in log_lines:
        if got_commit:
            # if start a new commit then finished vanilla commit
            if line.startswith('commit'):
                break

            if got_file_start:
                if line.startswith('@@'):
                    # Ignore for now
                    pass
                else:
                    diff_lines.append(line)

            if line.startswith('+++'):
                got_file_start = True

        if 'aa718717d64aaba84967048c02cc894ffce62fbc' in line:
            got_commit = True

    return diff_lines
            


def get_original_line(mod_script_dir, mod_script_file, line_no) -> List[str]:
    p = subprocess.run(["git", 'log', f'-L{line_no},+1:{mod_script_file}'], capture_output=True, text=True, shell=True, cwd=mod_script_dir)
    vanilla_lines = get_vanilla_only(p.stdout.splitlines())
    return vanilla_lines


def parse_line(mod_script_dir, mod_script_file, all_lines, line_index, line):
    if 'ModDrawCharacter' in line:
        match = modSpritePathCharacterNameRegex.search(line)
        if match:
            # 'sprite' or 'portrait'
            sprite_type = match.group(1)
            mod_character = match.group(2)
        else:
            raise Exception(f"No character found in line {line}")

        print(f"Line No: {line_index + 1} Type: {sprite_type} Char: {mod_character} Line: {line.strip()}")

        if mod_character not in mod_to_name:
            raise Exception(f"No mod character {mod_character} in database")

        original_lines = get_original_line(mod_script_dir, mod_script_file, line_index + 1)

        for line in original_lines:
            # determine what character is being displayed
            match = ogSpritePathCharacterNameRegex.search(line)
            if match:
                character = match.group(1)
                print(f'{character}: {line.strip()}')
            else:
                print(line)

        print('----------------------------------------')


with open(modded_input_file, encoding='utf-8') as f:
    all_lines = f.readlines()
    for line_index, line in enumerate(all_lines):
        parse_line(mod_script_dir, mod_script_file, all_lines, line_index, line)


