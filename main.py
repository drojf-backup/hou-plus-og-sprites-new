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


class CallData:
    def __init__(self, line, is_mod):
        self.line = line
        self.type = None  # type
        self.matching_key = None  # lookup_key
        self.debug_character = None

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


# assume outputLineAll is always a dummy (sometimes it's not, but this simplification should be OK)
outputLineAll = re.compile(r"OutputLineAll\([^;]*;")

outputLineRegex = re.compile(r"OutputLine\(\s*[^,]*,\s*\"(.*)\"\s*,")

ogSpritePathCharacterNameRegex = re.compile(r'"sprites/([^/]+)')

modSpritePathCharacterNameRegex = re.compile(
    r'"((?:sprite)|(?:portrait))/([a-zA-Z]*)')

modEffectPathRegex = re.compile(r'"effect/(\w*)')

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

ARA_SILHOUETTE = 'ara_silhouette'
NIT_SILHOUETTE = 'nit_silhouette'
ODA_SILHOUETTE = 'oda_silhouette'
OKA_SILHOUETTE = 'oka_silhouette'
TON_SILHOUETTE = 'ton_silhouette'
YOS_SILHOUETTE = 'yos_silhouette'

KEI_SILHOUETTE = 'kei_silhouette'
OYASHIRO_SILHOUETTE = 'oyashiro_silhouette'


SHOULD_PROCESS_LIST = [
    '"bg/',
    '"chapter/',
    '"credits/',
    '"effect/',
    '"omake/',
    '"portrait/',
    '"scene/',
    '"sprite/',
    '"title/'
    '"red"',
    '"black"',
    '"filter_hanyu"',
    '"transparent"',
    '"white"',
    '"windo_filter"',
    '"windo_filter_adv"',
]


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
                       capture_output=True, text=True, shell=True, cwd=mod_script_dir)
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


def line_has_graphics(line):
    for string_start in SHOULD_PROCESS_LIST:
        if string_start in line:
            return True

    return False


def parse_line(mod_script_dir, mod_script_file, all_lines: List[str], line_index, line: str):
    """This function expects a modded script line as input, as well other arguments describing where the line is from"""
    print_data = ""

    # for now just ignore commented lines
    line = line.split('//', maxsplit=1)[0]

    # Only process lines which look like they touch graphics (by the file paths accessed, like "sprite/" or "background/")
    if not line_has_graphics(line):
        return

    # Convert the line into a CallData object
    mod = CallData(line, is_mod=True)
    print_data += (f"Line No: {line_index + 1} Type: {mod.type} Key: {
                   mod.matching_key} Character: {mod.debug_character} Line: {line.strip()}\n")

    # Now use git to extract matching lines from the original game
    og_lines, raw_git_log_output = get_original_lines(
        mod_script_dir, mod_script_file, line_index + 1)

    print_data += ">> Raw Git Log Output (vanilla -> mod) <<\n"
    for line in og_lines:
        print_data += line + "\n"
    # print_data += raw_git_log_output
    print_data += ">> END Git Log Output <<\n"

    og_call_data = [CallData(l, is_mod=False) for l in og_lines]

    for og in og_call_data:
        print_data += (
            f"- Type: {og.type} Matching Key: {og.matching_key} Line: {og.line.strip()}\n")

        if not og.line.startswith('+'):
            raise Exception(f"git output for {
                            og.line} does not start with a +")

    print_data += ("\n")

    # Now try to match lines using various methods
    matched_line = None

    # if len(og_lines) == 1:
    #     matched_line = og_lines[0]
    #     print(f"Matched as only one match: {matched_line}")

    if mod.matching_key:
        for og in og_call_data:
            if mod.matching_key in og.line:
                matched_line = og.line
                print_data += (f"Matched by matching key: {matched_line}\n")

    if matched_line is None:
        print_data += ("Failed to match line\n")

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


with open('debug_output.txt', 'w', encoding='utf-8') as out:
    with open(modded_input_file, encoding='utf-8') as f:
        all_lines = f.readlines()
        for line_index, line in enumerate(all_lines):
            out.write(line)
            print_data = parse_line(mod_script_dir, mod_script_file,
                                    all_lines, line_index, line)
            if print_data is not None:
                out.write(print_data)
