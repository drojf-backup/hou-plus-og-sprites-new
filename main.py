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

missing_character_key = "ERROR_MISSING_CHARACTER"

class GlobalResult:
    def __init__(self) -> None:
        self.missing_char_detected = False


class ModToOGMatch:
    def __init__(self, og_calldata, og_path) -> None:
        self.og_calldata = og_calldata #type: CallData
        self.og_path = og_path #type: str


class CallData:
    def __init__(self, line, is_mod):
        self.line = line
        self.type = None  # type
        self.matching_key = None  # lookup_key
        self.debug_character = None
        self.path = get_graphics_on_line(line, is_mod)
        self.name = self.path.split('/')[-1]
        self.debug_og_call_data = None
        self.is_sprite = self.path.startswith('sprite/') or self.path.startswith('portrait/')

        if self.path is None:
            raise Exception(
                f"Error (is_mod: {is_mod}): Couldn't get path from line {line}")

        if is_mod:
            # Assume the line is a graphics call. Look for a graphics path like "sprite/kei7_warai_" or "portrait/kameda1b_odoroki_" using regex
            match = modSpritePathCharacterNameRegex.search(line)
            if not match:
                match = effectCharacterNameRegex.search(line)
            if not match:
                match = effectEyeCharacterNameRegex.search(line)

            if match:
                # Get the sprite type (containing folder), either 'sprite' or 'portrait'
                self.type = match.group(1)
                # Get the character name, like kei7 or kameda1b. The expression part is discarded.
                mod_character = match.group(2)

                # Special case for mob characters kumi1 and kumi2, whose names don't follow the usual convention
                # Eg. kumi1_01_0.png and kumi2_01_0.png are different people who appear at the same time
                if mod_character == 'kumi' and 'kumi1_' in line:
                    mod_character = 'kumi1'

                if mod_character == 'kumi' and 'kumi2_' in line:
                    mod_character = 'kumi2'

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
                    self.matching_key = f'{missing_character_key}: {mod_character}'
                    # raise Exception(f"No mod character {
                    #                 mod_character} in database for line {line}")

class VoiceBasedMatch:
    def __init__(self, voice: str, mod_calldata: CallData, og_match: ModToOGMatch):
        self.voice = voice # 'None' means no voice has been played yet
        self.mod_path = mod_calldata.path # Cannot be None

        self.og_path = None # 'None' means no match for this item
        if og_match is not None:
            if og_match.og_calldata is not None:
                self.og_path = og_match.og_calldata.path
            else:
                self.og_path = og_match.og_path

        self.debug_mod_calldata = mod_calldata
        self.debug_og_match = og_match

class VoiceMatchDatabase:
    def __init__(self, script_name: str):
        # Name of the script this voice based match database was extracted from
        self.script_name = script_name
        # List of all voice based matches (in this file)
        # self.all_voices = [] #type: list[VoiceBasedMatch]
        # Mapping of voice -> list of associated matches for that voice
        self.db = {} #type: dict[str, list[VoiceBasedMatch]]

    def set(self, match: VoiceBasedMatch):
        # if self.try_get(match.voice, match.mod_path):
        #     print(f"ERROR: [{match.voice}-{match.mod_path}] already exists in DB. Not adding")
        #     return

        if match.voice not in self.db:
            self.db[match.voice] = []

        match_array = self.db[match.voice]

        # Check if entry already exists - if so, overwrite it and return
        for i in range(len(match_array)):
            previous_match = match_array[i]
            if previous_match.mod_path == match.mod_path:
                match_array[i] = match
                return

        # Otherwise add a new entry
        match_array.append(match)

    def try_get(self, voice: str, mod_path: str) -> VoiceBasedMatch:
        if voice not in self.db:
            return None

        matches_for_voice = self.db[voice]
        for match in matches_for_voice:
            if match.mod_path == mod_path:
                return match

    def serialize(self, output_file: str):
        # TODO: This should really be done atomically, but since
        # this script will rarely be executed don't worry about it for now
        with open(output_file, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def deserialize(input_file: str) -> 'VoiceMatchDatabase':
        with open(input_file, 'rb') as f:
            return pickle.load(f)


class Statistics:
    def __init__(self):
        self.match_ok = 0
        self.match_fail = 0
        self.count_statistics = {} #type: dict[str, dict[str, list[CallData]]]
        self.missing_character_details = [] #type: list[str]
        # Keep track of mod bg path -> dict[og path, ogmatch?] guesses
        self.bg_guesses = {} #type: dict[str, dict[str, list[CallData]]]
        # Keep track of mod sprite path -> list[og path] guesses
        self.sprite_guesses = {} #type: dict[str, dict[str, list[CallData]]]

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
    def save_as_json(self, output_file_path, output_missing_characters_path, global_result: GlobalResult):
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

        missing_chars_path = Path(output_missing_characters_path)
        if missing_chars_path.exists():
            missing_chars_path.unlink()

        if self.missing_character_details:
            global_result.missing_char_detected = True

            summary = {}
            for (key, debug_out) in self.missing_character_details:
                summary[key] = debug_out

            with open(missing_chars_path, 'w', encoding='utf-8') as f:
                for key, value in summary.items():
                    f.write(f"Missing key: {key}\n")
                    f.write(f"{value}\n")

                f.write('\n\n\n----------------------------------------------------\n\n\n')
                for (key, debug_out) in self.missing_character_details:
                    f.writelines(debug_out)

        # Save bg and sprite guesses
        bg_guess_path = Path(output_file_path).with_suffix('.bg.txt')
        sprite_guess_path = Path(output_file_path).with_suffix('.sprite.txt')
        Statistics.save_matches(bg_guess_path, self.bg_guesses)
        Statistics.save_matches(sprite_guess_path, self.sprite_guesses)

    def add_missing_character(self, mod_matching_key_with_error: str, missing_character_line: str, og_lines: list[str]):
        out_string = f'{mod_matching_key_with_error}: {missing_character_line.strip()}\n'
        for line in og_lines:
            out_string += f'\t{line.strip()}\n'

        self.missing_character_details.append((mod_matching_key_with_error, out_string))

    def record_guesses(self, mod: CallData, og_calls: list[CallData]):
        if mod.is_sprite:
            for og_call in og_calls:
                if og_call.path.startswith('sprites/') or og_call.path.startswith('effect/'):
                    Statistics.add_guess(self.sprite_guesses, mod, og_call)
        else:
            for og_call in og_calls:
                if og_call.path.startswith('bg/') or og_call.path.startswith('effect/'):
                    Statistics.add_guess(self.bg_guesses, mod, og_call)

    @staticmethod
    def add_guess(guesses: dict[str, dict[str, list[CallData]]], mod: CallData, call: CallData):
        if mod.path not in guesses:
            guesses[mod.path] = {}

        mod_call_dict = guesses[mod.path] #type: dict[str, list[CallData]]

        if call.path not in mod_call_dict:
            mod_call_dict[call.path] = []

        mod_call_dict[call.path].append(call)

    @staticmethod
    def save_matches(out_file: str, guesses: dict[str, dict[str, list[CallData]]]):
        with open(out_file, 'w', encoding='utf-8') as f:
            for mod_path, og_guesses in guesses.items():
                og_guess_paths = ','.join(og_guesses.keys())
                f.write(f'{mod_path}: [{og_guess_paths}]\n')


# assume outputLineAll is always a dummy (sometimes it's not, but this simplification should be OK)
outputLineAll = re.compile(r"OutputLineAll\([^;]*;")

outputLineRegex = re.compile(r"OutputLine\(\s*[^,]*,\s*\"(.*)\"\s*,")

ogSpritePathCharacterNameRegex = re.compile(r'"sprites/([^/]+)')

modSpritePathCharacterNameRegex = re.compile(
    r'"((?:sprite)|(?:portrait))/([a-zA-Z]*)')

effectCharacterNameRegex = re.compile(
    r'"(effect)/((:?hara)|(:?hnit)|(:?hoda)|(:?hoka)|(:?hton)|(:?hyos))')

effectEyeCharacterNameRegex = re.compile(
    r'"(effect)/eye_((:?kas)|(:?kei)|(:?me)|(:?re)|(:?sa))')


modEffectPathRegex = re.compile(r'"effect/(\w*)')

voicePathRegex = re.compile(r'^\s*ModPlayVoiceLS\([^,]+,[^,]+,\s*"\s*([^"]+)\s*"')

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
OKONOGI = 'okonogi'
OISHI = 'oishi'
TAKANO = 'takano'
TETU = 'tetu'
MURA = 'mura'
UNE = 'une'
TAMURA = 'tamura'
KUMI_1 = 'kumi1'
KUMI_2 = 'kumi2'

# Only used in staffroom15?
SATOSHI = 'satoshi'
TOMITAKE = 'tomitake'
KASAI = 'kasai'
AKASAKA = 'akasaka'

# Silhouettes - should these be handled differently?
MION_SILHOUETTE = 'mion_silhouette'
RIKA_SILHOUETTE = 'rika_silhouette'
TON_SILHOUETTE = 'ton_silhouette'
ARA_SILHOUETTE = 'ara_silhouette'
YOS_SILHOUETTE = 'yos_silhouette'
OKA_SILHOUETTE = 'oka_silhouette'
HOS_SILHOUETTE = 'hos_silhouette'
ODA_SILHOUETTE = 'oda_silhouette'
HOT_SILHOUETTE = 'hot_silhouette'
NIT_SILHOUETTE = 'nit_silhouette'

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
    # renasen is rena with hatchet, but just mapping to RENA should generally be OK
    'renasen': RENA,
    'si': SHION,
    'kei': KEIICHI,
    # keisen is rena with hatchet, but just mapping to RENA should generally be OK
    'keisen': KEIICHI,
    'ri': RIKA,
    'ha': HANYU,
    'sa': SATOKO,
    'me': MION,
    'iri': IRIE,
    'mo': MOB_CHARACTER,
    'kameda': KAMEDA,
    'oko': OKONOGI,
    'oisi': OISHI,
    'ta': TAKANO,
    'tetu': TETU,
    'mura': MURA,
    'une': UNE,
    'tamura': TAMURA,
    # Special case - mob characters with similar name
    'kumi1': KUMI_1,
    'kumi2': KUMI_2,

    # Only used in staffroom15?
    'sato': SATOSHI,
    'tomi': TOMITAKE,
    'kasa': KASAI,
    'kas': KASAI,
    'aks': AKASAKA,


    # Silhouettes - should these be handled differently?
    'hmi': MION_SILHOUETTE,
    'hri': RIKA_SILHOUETTE,
    'hton':TON_SILHOUETTE,
    'hara': ARA_SILHOUETTE,
    'hyos': YOS_SILHOUETTE,
    'hoka': OKA_SILHOUETTE,
    'hhos': HOS_SILHOUETTE,
    'hoda': ODA_SILHOUETTE,
    'hhot': HOT_SILHOUETTE,
    'hnit': NIT_SILHOUETTE,
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

# TODO: check other chars (eg mo2, mo3, mo4) if they appear in og script
# or rather, scan OG script for all used sprites, not just mod script

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
    'kam': KAMEDA,
    'okonogi': OKONOGI,
    'oisi': OISHI,
    'takano': TAKANO,
    'tetu': TETU,
    'mo1': MURA,
    'une': UNE,
    'tam': TAMURA,
    # Special case - mob characters with similar name
    'mo6': KUMI_1,
    'mo5': KUMI_2,

    # Only used in staffroom15?
    'sato': SATOSHI,
    'tomi': TOMITAKE,
    'kasa': KASAI,
    'aks': AKASAKA,

    # Silhouettes - should these be handled differently?
    'mio': MION_SILHOUETTE,
    'rik': RIKA_SILHOUETTE,
    'ton': TON_SILHOUETTE,
    'ara': ARA_SILHOUETTE,
    'yos': YOS_SILHOUETTE,
    'oka': OKA_SILHOUETTE,
    'hos': HOS_SILHOUETTE,
    'oda': ODA_SILHOUETTE,
    'hod': HOT_SILHOUETTE,
    'nit': NIT_SILHOUETTE,
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

def get_voice_on_line(line) -> str:
    match = voicePathRegex.search(line)
    if match:
        return match.group(1)

    return None

def line_has_graphics(line, is_mod):
    if get_graphics_on_line(line, is_mod) is None:
        return False
    else:
        return True

bg_match_pairs_regex_str = [
    ('_mati', '/mati'), # city (machi)
    ('cit_', '/mati'), # mod has 'cit' (city), but OG does not and uses 'mati' (machi/town) instead
    ('_sinryou', '/sinryoujo/'), # hospital
    ('_shikenkan', '/shikenkan'), # shikenkan (test tube) There is only one image of test-tubes
    ('/susuki', '/kusa'), # susuki (Miscanthus sinensis (a species of grass)) vs kusa (grass)
    ('effect/kamik_inf_1', 'bg/etc/inf_1'), # Image of earth changing to red tint (lower number is less red)
    ('effect/kamik_inf_2', 'bg/etc/inf_2'),
    ('effect/kamik_inf_3', 'bg/etc/inf_3'),
    ('effect/kamik_inf_4', 'bg/etc/inf_4'),
    ('effect/kamik_inf_5', 'bg/etc/inf_5'),
    ('ryoutei', 'sonozaki/ryoutei'), # ryoutei - under the sonozaki folder, it's the dining area?
    ('background/hi([^a-zA-Z]|$)', 'bg/mura/hi'), # hi (hinamizawa)
    ('background/hi([^a-zA-Z]|$)', 'bg/mura/m_hi'), # hi (hinamizawa)
    ('kamik_sono_', 'sonozakigumi/sono_') # sonozaki building?
]

bg_match_pairs = [ (re.compile(p[0]), re.compile(p[1])) for p in bg_match_pairs_regex_str ] # type: list[tuple[re.Pattern, re.Pattern]]

sprite_match_pairs = []

def match_by_keyword(mod: CallData, og_call_data: list[CallData]):
    match_pairs = sprite_match_pairs if mod.is_sprite else bg_match_pairs

    # Check for outbreak variants
    # Mod has specific images for 'outb' (outbreak), but OG does not and just uses the normal versions of the image
    mod_filestem = Path(mod.path).stem
    if mod_filestem.startswith('outb_'):
        expected_og_stem = mod_filestem.replace('outb_', '')
        for og in og_call_data:
            og_filestem = Path(og.path).stem
            if expected_og_stem == og_filestem:
                return ModToOGMatch(og, None)

    # Iterate though possible match pairs
    for mod_key, og_key in match_pairs:
        # Check the mod path contains the key, if not give up
        if mod_key.search(mod.path):
            # Now test all og lines which git returned
            for og in og_call_data:
                # Check og line contains key, if not give up
                if og_key.search(og.path):
                    return ModToOGMatch(og, None)

    return None

def parse_line(mod_script_dir, mod_script_file, all_lines: List[str], line_index, line: str, statistics: Statistics, og_bg_lc_name_to_path: dict[str, str], manual_name_matching: dict[str, str], last_voice: str, voice_match_database: VoiceMatchDatabase):
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

    # Skip this line if the image's mod path already exists in database
    # and it has a match
    memozied_match = voice_match_database.try_get(last_voice, mod.path)
    if memozied_match is not None:
        if memozied_match.og_path is not None:
            return

    # Now use git to extract matching lines from the original game
    og_lines, raw_git_log_output = get_original_lines(
        mod_script_dir, mod_script_file, line_index + 1)

    if mod.matching_key is not None and missing_character_key in mod.matching_key:
        statistics.add_missing_character(mod.matching_key, line, og_lines)
        return

    print_data += ">> Raw Git Log Output (vanilla -> mod) <<\n"
    for l in og_lines:
        print_data += l + "\n"
    # print_data += raw_git_log_output
    print_data += ">> END Git Log Output <<\n"

    og_call_data = [] #type: list[CallData]
    for l in og_lines:
        # Ignore lines which don't have graphics
        if line_has_graphics(l, is_mod=False):
            og_call_data.append(CallData(l, is_mod=False))
    mod.debug_og_call_data = og_call_data

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

    # scene folder are special CGs, so dont' try to match them
    if mod_to_og_match is None:
        if mod.path.startswith('scene/'):
            mod_to_og_match = ModToOGMatch(None, 'SPECIAL_SCENE')

    if mod_to_og_match is None:
        if mod.matching_key:
            # First try to do exact match if the path contains a matching folder
            if mod_to_og_match is None:
                for og in og_call_data:
                    if f'/{mod.matching_key}/' in og.line:
                        mod_to_og_match = ModToOGMatch(og, None)
                        print_data += (f"Matched by matching key (exact folder): {mod_to_og_match}\n")
                        # TODO: insert break here?

            # Then just match anywhere in the string
            if mod_to_og_match is None:
                for og in og_call_data:
                    if mod.matching_key in og.line:
                        mod_to_og_match = ModToOGMatch(og, None)
                        print_data += (f"Matched by matching key (anywhere in string): {mod_to_og_match}\n")
                        # TODO: insert break here?

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

    # Try matching by match keywords
    if mod_to_og_match is None:
        keyword_match = match_by_keyword(mod, og_call_data)
        if keyword_match:
            mod_to_og_match = keyword_match

    if mod_to_og_match is None:
        print_data += ("Failed to match line\n")
        print(f"Failed to match '{mod.name}' line: {line.strip()}")
        statistics.match_fail += 1

        # Record what possible matches there could be for analysis
        statistics.record_guesses(mod, og_call_data)
    else:
        statistics.match_ok += 1
        statistics.add_match(mod, mod_to_og_match)

    voice_match_database.set(VoiceBasedMatch(last_voice, mod, mod_to_og_match))

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

def scan_one_script(mod_script_dir: str, mod_script_path: str, debug_output_file, global_result: GlobalResult, output_folder: str):
    os.makedirs(output_folder, exist_ok=True)
    out_filename = Path(mod_script_path).stem
    voice_db_path = os.path.join(output_folder, f'{out_filename}_voice_db.pickle')

    if Path(voice_db_path).exists():
        voice_match_database = VoiceMatchDatabase.deserialize(voice_db_path)
    else:
        voice_match_database = VoiceMatchDatabase(mod_script_path)

    stats = Statistics()

    with open(mod_script_path, encoding='utf-8') as f:
        all_lines = f.readlines()

    # Check every line in the modded input script for corresponding og graphics
    last_voice = None
    for line_index, line in enumerate(all_lines):
        if max_lines != None and line_index > max_lines:
            break

        voice_on_line = get_voice_on_line(line)
        if voice_on_line:
            last_voice = voice_on_line

        print_data = parse_line(mod_script_dir, mod_script_path,
                                all_lines, line_index, line, stats, og_bg_lc_name_to_path, manual_name_matching, last_voice, voice_match_database)

        # Print output for debbuging, only if enabled
        if debug_output_file is not None:
            debug_output_file.write(line)
            if print_data is not None:
                debug_output_file.write(print_data)



    # Write the output statistcs .json
    # print(f"{stats.match_ok}/{stats.total()} Failed: {stats.match_fail}")
    # print(stats.count_statistics)
    json_out_path = os.path.join(output_folder, f'{out_filename}.json')
    missing_chars_path = os.path.join(output_folder, f'{out_filename}_missing_chars.txt')

    voice_match_database.serialize(voice_db_path)

    stats.save_as_json(json_out_path, missing_chars_path, global_result)


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


# Modify to only test a subset of the files/each file
max_lines = None
pattern = '*.txt'

# Build a mapping from filename -> path for unmodded CGs, except sprites
unmodded_cg = 'D:/games/steam/steamapps/common/Higurashi When They Cry Hou+ Unmodded/HigurashiEp10_Data/StreamingAssets/CG'

if not os.path.exists(unmodded_cg):
    raise Exception(f"Unmodded CG path doesn't exist: {unmodded_cg}")

og_bg_lc_name_to_path = path_util.lc_name_to_path(
    unmodded_cg, exclude=['sprites/'])


# unmodded_input_file = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Installer Test/HigurashiEp10_Data/StreamingAssets/Scripts/mehagashi.txt'
mod_script_dir = 'D:/drojf/large_projects/umineko/HIGURASHI_REPOS/10 hou-plus/Update/'

output_folder = 'stats_temp'

# TODO: add global stats across all items? only write out once all items processed
global_result = GlobalResult()

for modded_script_path in Path(mod_script_dir).glob(pattern):
    scan_one_script(mod_script_dir, modded_script_path, debug_output_file=None, global_result=global_result, output_folder=output_folder)

if global_result.missing_char_detected:
    print("<<<<<<<<<<< WARNING: one or more missing from the mod_to_name or og_to_name table, please update or matching will be incomplete! >>>>>>>>>>>>>>")

#################################################################
#### Now run 'generate_mapping_from_stats' script after this ####
#################################################################