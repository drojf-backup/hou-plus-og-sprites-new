import json
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

# User imports
import path_util


class ModToOGMatch:
    def __init__(self, og_calldata, og_path) -> None:
        self.og_calldata = og_calldata
        self.og_path = og_path


class CallData:
    def __init__(self, line, is_mod):
        self.line = line
        self.type = None  # type
        self.matching_key = None  # lookup_key
        self.debug_character = None
        self.path = get_graphics_on_line(line, is_mod)
        self.name = self.path.split('/')[-1]

        if self.path is None:
            raise Exception(
                f"Error (is_mod: {is_mod}): Couldn't get path from line {line}")

        if is_mod:
            # Assume the line is a graphics call. Look for a graphics path like "sprite/kei7_warai_" or "portrait/kameda1b_odoroki_" using regex
            match = modSpritePathCharacterNameRegex.search(line)
            if match:
                # Get the sprite type (containing folder), either 'sprite' or 'portrait'
                self.type = match.group(1)
                # Get the character name, like kei7 or kameda1b. The expression part is discarded.
                mod_character = match.group(2)
                self.debug_character = mod_character

                # To cope with the character name in the modded game and OG game being different,
                # normalize the names
                #
                # Do this by mapping the modded character name to a normalized name, eg 'ri'(mod)->'rika'(normalized)
                # Then map the normalized name to the OG name, eg 'rika'(normalized)->'rika'(og)
                # The 'matching_key' is then set to the OG name, so we can cross check it against the earlier git commit of the og game
                if mod_character in mod_to_name:
                    self.matching_key = name_to_og[mod_to_name[mod_character]]
                else:
                    raise Exception(f"No mod character {
                                    mod_character} in database for line {line}")

class Statistics:
    def __init__(self):
        self.match_ok = 0
        self.match_fail = 0
        self.count_statistics = {} #type: dict[str, dict[str, list[CallData]]]

    def total(self):
        return self.match_ok + self.match_fail

    def add_match(self, mod_call_data: CallData, og_match: ModToOGMatch):
        if og_match.og_calldata is None:
            og_name = Path(og_match.og_path).stem
        else:
            og_name = og_match.og_calldata.name

        print(f"{mod_call_data.path} -> {og_name}")

        if mod_call_data.path not in self.count_statistics:
            self.count_statistics[mod_call_data.path] = {}

        mod_dict = self.count_statistics[mod_call_data.path]

        if og_name not in mod_dict:
            mod_dict[og_name] = []

        mod_dict[og_name].append(og_match)

    # TODO:
    # Then load in another script and determine final mapping?
    # Also need to scan every possible graphics path in modded game to make sure all paths are covered
    def save_as_json(self, output_file_path):
        to_dump = {}

        for mod_path, og_results in self.count_statistics.items():
            to_dump[mod_path] = {}
            mod_path_dict = to_dump[mod_path]
            for og_path, og_list in og_results.items():
                mod_path_dict[og_path] = len(og_list)

        json_string = json.dumps(to_dump, sort_keys=True, indent=4)
        print(json_string)

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(json_string)



# assume outputLineAll is always a dummy (sometimes it's not, but this simplification should be OK)
outputLineAll = re.compile(r"OutputLineAll\([^;]*;")

outputLineRegex = re.compile(r"OutputLine\(\s*[^,]*,\s*\"(.*)\"\s*,")

ogSpritePathCharacterNameRegex = re.compile(r'"sprites/([^/]+)')

modSpritePathCharacterNameRegex = re.compile(
    r'"((?:sprite)|(?:portrait))/([a-zA-Z]*)')

modEffectPathRegex = re.compile(r'"effect/(\w*)')


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

ARA_SILHOUETTE = 'ara_silhouette'
NIT_SILHOUETTE = 'nit_silhouette'
ODA_SILHOUETTE = 'oda_silhouette'
OKA_SILHOUETTE = 'oka_silhouette'
TON_SILHOUETTE = 'ton_silhouette'
YOS_SILHOUETTE = 'yos_silhouette'

KEI_SILHOUETTE = 'kei_silhouette'
OYASHIRO_SILHOUETTE = 'oyashiro_silhouette'

def partial_path_to_regex(filenamefolder_list) -> re.Pattern:
    item = '|'.join(filenamefolder_list)
    complete_regex = f'"((?:{item})[^"]*)"'
    return re.compile(complete_regex)

MOD_CG_LIST = [
    'background/',
    'black',
    'chapter/',
    'credits/',
    'effect/',
    'filter_hanyu',
    'omake/',
    'portrait/',
    'red',
    'scene/',
    'sprite/',
    'title/',
    'transparent',
    'white',
    'windo_filter',
    'windo_filter_adv',
    'windo_filter_nvladv',
]

OG_CG_LIST = [
    'bg/',
    'black',
    'chapter/',
    'cinema_window',
    'cinema_window_name',
    'credits/',
    'effect/',
    'furiker_a',
    'furiker_b',
    'hanyuu_background',
    'img/',
    'no_data',
    'omake/',
    'sprites/',
    'title/',
    'white',
    'windo_filter',
]

OG_CG_REGEX = partial_path_to_regex(OG_CG_LIST)  # type: List[re.Pattern]
MOD_CG_REGEX = partial_path_to_regex(MOD_CG_LIST)  # type: List[re.Pattern]


# for item in OG_TO_REGEX:
#     complete_regex = f'"({item}[^"]*)"'
#     print(complete_regex)
#     OG_SHOULD_PROCESS_REGEX.append(
#         re.compile(complete_regex)
#     )

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
    'kameda': KAMEDA,
}

mod_effect_to_name = {
    'hara': ARA_SILHOUETTE,
    'hnit':  NIT_SILHOUETTE,
    'hoda': ODA_SILHOUETTE,
    'hoka': OKA_SILHOUETTE,
    'hton':  TON_SILHOUETTE,
    'hyos': YOS_SILHOUETTE,
    'kei': KEI_SILHOUETTE,
    'oyasiro': OYASHIRO_SILHOUETTE,
}

og_to_name = {
    'rena': RENA,
    'sion': SHION,
    'keiiti': KEIICHI,
    'rika': RIKA,
    'hanyu': HANYU,
    'satoko': SATOKO,
    'mion': MION,
    'irie': IRIE,
    'mob': MOB_CHARACTER,
    'kameda': KAMEDA
    # 'nit':
}


def reverse_dict(d: dict[str, str]) -> dict[str, str]:
    reversed = {}

    for key, value in d.items():
        reversed[value] = key

    return reversed


name_to_og = reverse_dict(og_to_name)


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


def get_original_lines(mod_script_dir, mod_script_file, line_no) -> (List[str], str):
    p = subprocess.run(["git", 'log', f'-L{line_no},+1:{mod_script_file}'],
                       capture_output=True, encoding="utf-8", shell=True, cwd=mod_script_dir, check=True)
    raw_output = p.stdout
    vanilla_lines = get_vanilla_only(raw_output.splitlines())
    return vanilla_lines, raw_output


# def get_sprite_info():
#     # TODO: add drawscene etc. here
#     is_draw_call = 'ModDrawCharacter' in line or 'DrawBustshot' in line
#     if not is_draw_call:
#         return None, None


#     match = modSpritePathCharacterNameRegex.search(line)
#     if match:
#         # 'sprite' or 'portrait'
#         sprite_type = match.group(1)
#         mod_character = match.group(2)

#         print(f"Line No: {line_index + 1} Type: {sprite_type} Char: {mod_character} Line: {line.strip()}")

#         if mod_character not in mod_to_name:
#             raise Exception(f"No mod character {mod_character} in database")

#         return sprite_type, mod_character


#     effect_match = modEffectPathRegex.search(line)
#     if effect_match:
#         effect_identifier = effect_match.group(1)

#         if effect_identifier not in mod_effect_to_name:
#             raise Exception(f"Mod Effect {effect_identifier} not found in effect database")

#         return 'effect', effect_identifier


#     return None, None


# returns None if no graphics found!
def get_graphics_on_line(line, is_mod) -> str:
    regex = OG_CG_REGEX
    if is_mod:
        regex = MOD_CG_REGEX

    match = regex.search(line)
    if match:
        return match.group(1)

    return None


def line_has_graphics(line, is_mod):
    if get_graphics_on_line(line, is_mod) is None:
        return False
    else:
        return True


def parse_line(mod_script_dir, mod_script_file, all_lines: List[str], line_index, line: str, statistics: Statistics, og_bg_lc_name_to_path: dict[str, str], manual_name_matching: dict[str, str]):
    """This function expects a modded script line as input, as well other arguments describing where the line is from"""
    print_data = ""

    # for now just ignore commented lines
    line = line.split('//', maxsplit=1)[0]

    # Only process lines which look like they touch graphics (by the file paths accessed, like "sprite/" or "background/")
    if not line_has_graphics(line, is_mod=True):
        return

    # Convert the line into a CallData object
    mod = CallData(line, is_mod=True)
    print_data += (f"Line No: {line_index + 1} Type: {mod.type} Key: {
                   mod.matching_key} Character: {mod.debug_character} Line: {line.strip()}\n")

    # Now use git to extract matching lines from the original game
    og_lines, raw_git_log_output = get_original_lines(
        mod_script_dir, mod_script_file, line_index + 1)

    print_data += ">> Raw Git Log Output (vanilla -> mod) <<\n"
    for l in og_lines:
        print_data += l + "\n"
    # print_data += raw_git_log_output
    print_data += ">> END Git Log Output <<\n"

    og_call_data = []
    for l in og_lines:
        # Ignore lines which don't have graphics
        if line_has_graphics(l, is_mod=False):
            og_call_data.append(CallData(l, is_mod=False))

    if len(og_call_data) == 0:
        msg = f'>> No OG graphics for {line}\n'

        if len(og_lines) > 0:
            msg += 'OG lines were:\n'
            for l in og_lines:
                msg += f"{l}\n"

        # print(msg)
        print_data += msg
        return print_data

    # og_call_data = [CallData(l, is_mod=False) for l in og_lines]

    for og in og_call_data:
        print_data += (
            f"- Type: {og.type} Matching Key: {og.matching_key} Line: {og.line.strip()}\n")

        if not og.line.startswith('+'):
            raise Exception(f"git output for {
                            og.line} does not start with a +")

    print_data += ("\n")

    # Now try to match lines using various methods
    mod_to_og_match = None

    # if len(og_lines) == 1:
    #     matched_line = og_lines[0]
    #     print(f"Matched as only one match: {matched_line}")

    if mod.matching_key:
        for og in og_call_data:
            if mod.matching_key in og.line:
                mod_to_og_match = ModToOGMatch(og, None)
                print_data += (f"Matched by matching key: {mod_to_og_match}\n")

    # Try matching by same name match
    if mod_to_og_match is None:
        for og in og_call_data:
            if og.name == mod.name:
                print(f"Matched by name in git log '{
                      og.name}': {mod.path} -> {og.path}")
                mod_to_og_match = ModToOGMatch(og, None)
                break

    # Try matching by manual matches
    # Eg 'oki_pool2' : 'pool2' which comes from the files:
    #  "background/oki_pool2" -> "bg/2021_add/pool2"
    if mod_to_og_match is None:
        if mod.name in manual_name_matching:
            expected_og_name = manual_name_matching[mod.name]
            for og in og_call_data:
                if og.name == expected_og_name:
                    mod_to_og_match = ModToOGMatch(og, None)
                    msg = f"Matched by manual name match '{mod.name}' -> '{expected_og_name}' {mod_to_og_match}\n"
                    print(msg)
                    print_data += msg
                    break

    # Try matching by same name in OG files
    if mod_to_og_match is None:
        if mod.name in og_bg_lc_name_to_path:
            og_path = og_bg_lc_name_to_path[mod.name]
            print(f"Matched by name in og files '{
                  mod.name}': {mod.path} -> {og_path}")
            mod_to_og_match = ModToOGMatch(None, og_path)

    if mod_to_og_match is None:
        print_data += ("Failed to match line\n")
        print(f"Failed to match '{mod.name}' line: {line.strip()}")
        statistics.match_fail += 1
    else:
        statistics.match_ok += 1
        statistics.add_match(mod, mod_to_og_match)

    print_data += ('----------------------------------------\n')

    # if 'ModDrawCharacter' in line or 'DrawBustshot' in line:
    #     match = modSpritePathCharacterNameRegex.search(line)
    #     if match:
    #         # 'sprite' or 'portrait'
    #         sprite_type = match.group(1)
    #         mod_character = match.group(2)
    #     else:
    #         raise Exception(f"No character found in line {line}")

    #     print(f"Line No: {line_index + 1} Type: {sprite_type} Char: {mod_character} Line: {line.strip()}")

    #     if mod_character not in mod_to_name:
    #         raise Exception(f"No mod character {mod_character} in database")

    #     original_lines = get_original_line(mod_script_dir, mod_script_file, line_index + 1)

    #     for line in original_lines:
    #         # determine what character is being displayed
    #         match = ogSpritePathCharacterNameRegex.search(line)
    #         if match:
    #             character = match.group(1)
    #             print(f'{character}: {line.strip()}')

    #             # if character not in og_to_name:
    #             #     raise Exception(f"No og character {character} in database")
    #         else:
    #             print(line)
    # else:
    #     effect_match = modEffectPathRegex.search(line)

    return print_data

def scan_one_script(mod_script_dir: str, mod_script_path: str, debug_output_file):
    with open(mod_script_path, encoding='utf-8') as f:
        all_lines = f.readlines()

    # Check every line in the modded input script for corresponding og graphics
    for line_index, line in enumerate(all_lines):
        if max_lines != None and line_index > max_lines:
            break

        print_data = parse_line(mod_script_dir, mod_script_path,
                                all_lines, line_index, line, stats, og_bg_lc_name_to_path, manual_name_matching)

        # Print output for debbuging, only if enabled
        if debug_output_file is not None:
            debug_output_file.write(line)
            if print_data is not None:
                debug_output_file.write(print_data)


    # Write the output statistcs .json
    # print(f"{stats.match_ok}/{stats.total()} Failed: {stats.match_fail}")
    # print(stats.count_statistics)
    out_filename = Path(mod_script_path).stem
    os.makedirs('stats', exist_ok=True)
    stats.save_as_json(f'stats/{out_filename}.json')



# with open('debug_output.txt', 'w', encoding='utf-8') as debug_output:

manual_name_matching = {
    'oki_pool1' : 'pool1',
    'oki_pool2' : 'pool2',
    'oki_pool3' : 'pool3',
    # 'chika_shisetsu': 'ko1',
    # Effect images...should these be handled differently?
    'hara': 'ara_d4',
    'hton': 'ton_d5a',
}

stats = Statistics()

max_lines = None

# Build a mapping from filename -> path for unmodded CGs, except sprites
unmodded_cg = 'D:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Unmodded/HigurashiEp10_Data/StreamingAssets/CG'

if not os.path.exists(unmodded_cg):
    raise Exception(f"Unmodded CG path doesn't exist: {unmodded_cg}")

og_bg_lc_name_to_path = path_util.lc_name_to_path(
    unmodded_cg, exclude=['sprites/'])


# unmodded_input_file = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Installer Test/HigurashiEp10_Data/StreamingAssets/Scripts/mehagashi.txt'
mod_script_dir = 'D:/drojf/large_projects/umineko/HIGURASHI_REPOS/10 hou-plus/Update/'

for modded_script_path in Path(mod_script_dir).glob('*.txt'):
    scan_one_script(mod_script_dir, modded_script_path, debug_output_file=None)


