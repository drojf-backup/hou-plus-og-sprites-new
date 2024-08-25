
import json
import operator
from pathlib import Path
import re
import common
from common import VoiceMatchDatabase
import voice_util

PRINT_FAILED_MATCHES = False

def normalize_path(path: str) -> str:
    return str(path).replace('\\', '/').split('HigurashiEp10_Data/StreamingAssets/CG/')[-1]

# Outputs a dictionary, mapping 'last played voice' to another dict.
# The inner dict maps from mod path -> og path
def convert_database_to_dict(voice_database: VoiceMatchDatabase) -> dict[str, dict[str, str]]:
    ret = {}
    for voice, matches_after_voice in voice_database.db.items():
        # Convert None to the empty string as [null] is an invalid JSON key
        if voice is None:
            voice = ""
        else:
            voice = str(voice)

        matches_per_voice = {}

        for match in matches_after_voice:
            mod_path = normalize_path(match.mod_path)
            og_path = normalize_path(match.og_path)
            matches_per_voice[mod_path] = og_path

        ret[voice] = matches_per_voice

    return ret


class FallbackMatch:
    def __init__(self, fallback_match_path: str, source_description: str) -> None:
        self.fallback_match_path = fallback_match_path
        self.source_description = source_description

    def __str__(self) -> str:
        return f"path: {self.fallback_match_path} source: {self.source_description}"

class PerScriptFallback:
    def __init__(self, script_name: str, fallback_data: dict[str, FallbackMatch]) -> None:
        self.script_name = script_name
        self.fallback_data = fallback_data

class AllMatchData:
    def __init__(self):
        self.global_fallback = None #type: dict[str, FallbackMatch]
        # modded script name -> fallback dictionary
        self.per_script_fallbacks = {} #type: dict[str, list[PerScriptFallback]]
        # modded script name -> VoiceMatchDatabase object
        self.per_script_voice_database = {} #type: dict[str, VoiceMatchDatabase]

    def set_global_fallback(self, fallback: dict[str, FallbackMatch]):
        self.global_fallback = fallback

    def set_per_script_fallback(self, script_name: str, fallback: dict[str, FallbackMatch]):
        self.per_script_fallbacks[script_name] = fallback

    def set_voice_database(self, script_name: str, voice_database: VoiceMatchDatabase):
        self.per_script_voice_database[script_name] = voice_database


def get_fallback_dict_for_json(fallback: dict[str, FallbackMatch], save_source_info: bool):
    # Convert fallback matching to dict
    fallback_for_json = {}

    for ps3_path, info in fallback.items():
        info_dict = {"path": info.fallback_match_path}

        if save_source_info:
            info_dict["source"] = info.source_description

        fallback_for_json[ps3_path] = info_dict

    return {
        "fallback" : fallback_for_json
    }

def save_to_json(object, output_path: str):
    json_string = json.dumps(object, sort_keys=True, indent='\t')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json_string)

def get_match_data_as_plain_dict(match_data: AllMatchData, save_debug_info: bool):
    # Collect all script fallbacks into a dict
    script_fallback = {}
    for script_name, per_script_fallback in match_data.per_script_fallbacks.items():
        script_fallback[script_name] = get_fallback_dict_for_json(per_script_fallback, save_source_info=save_debug_info)

    all_voice_database = {}
    for script_path_object, voice_database in match_data.per_script_voice_database.items():
        all_voice_database[Path(script_path_object).stem] = convert_database_to_dict(voice_database)

    return {
        "comment_paths" : "Note: when looking up paths, paths starting with '<' like <SPECIAL_TEXT_EFFECT>  are special cases. And if a match is 'null' then it means this sprite was never matched.",
        "comment_lookup" : "To lookup, first check the voice database. Then check the script fallback. Then check the global fallback.",
        "global_fallback" : get_fallback_dict_for_json(match_data.global_fallback, save_source_info=save_debug_info),
        "script_fallback" : script_fallback,
        "voice_database" : all_voice_database,
    }


####################  Graphics Regexes ####################

def get_graphics_regexes(modded_game_cg_dir: str) -> list[re.Pattern]:
    if not Path(modded_game_cg_dir).exists():
        raise Exception("Modded game CG folder does not exist!")

    patterns = []
    for cg_top_level_path in Path(modded_game_cg_dir).glob('*'):
        if cg_top_level_path.is_dir():
            graphics_regex = f'^{cg_top_level_path.stem}/'
        else:
            graphics_regex = f'^{cg_top_level_path.stem}$'

        patterns.append(re.compile(graphics_regex))

    return patterns

####################  Verification ####################

class ExpectedGraphics:
    def __init__(self, line: str, path: str) -> None:
        self.line = line
        self.path = path

# Find double quoted strings, including ones with escaped double quotes
string_regex = re.compile(r'"(?P<data>((\\")|([^"]))*?)"')

def path_is_graphics(path: str, graphics_regexes: list[re.Pattern]):
    for r in graphics_regexes:
        if r.match(path):
            return True

    return False

class CheckResult:
    def __init__(self, detected, matched):
        self.detected = detected
        self.mapped = matched

# This checks whether a particular graphics is 'detected'. This avoids errors where the matching script
# doesn't even see a graphics path, so it will never match that graphics path against anything
def graphics_is_detected_and_mapped(last_voice: str, stripped_path: str, existing_matches: VoiceMatchDatabase, unique_unmatched: dict[str, list[VoiceMatchDatabase]]) -> CheckResult:
    # Check the voice exists in the database.
    # If not, perhaps voice not detected in matching script, or not inserted in database properly
    if last_voice not in existing_matches.db:
        print(f"Error (Missing Voice): voice [{last_voice}] is in [{existing_matches.script_name}] database")
        return CheckResult(False, False)

    graphics_in_voice_section = existing_matches.db[last_voice]

    # Now check the graphics was in that voice section
    for voice_match in graphics_in_voice_section:
        if voice_match.mod_path.strip() == stripped_path:
            has_mapping = False
            if voice_match.og_path and str(voice_match.og_path).strip():
                has_mapping = True
            else:
                if PRINT_FAILED_MATCHES:
                    print(f'No match for {voice_match.mod_path} | {voice_match.voice}')

                # Collect unmatched mod paths to display at the end
                if voice_match.mod_path not in unique_unmatched:
                    unique_unmatched[voice_match.mod_path] = []
                unique_unmatched[voice_match.mod_path].append(voice_match)

            return CheckResult(True, has_mapping)

    # If reached this point, graphics not found in that voice section.
    # Print all the graphics which were found for that voice section for debugging.
    print(f"Error (Graphics not found in voice section): In voice section [{last_voice}], the graphics [{stripped_path}] was not found. The following graphics were found instead:")
    for voice_match in graphics_in_voice_section:
        print(f" - {voice_match.mod_path}")

    return CheckResult(False, False)

def verify_one_script(mod_script_path: str, graphics_regexes: list[re.Pattern], existing_matches: VoiceMatchDatabase, statistics: dict[str, list[str, int]]) -> tuple[list[str], dict[str, FallbackMatch]]:
    with open(mod_script_path, encoding='utf-8') as f:
        all_lines = f.readlines()

    detect_pass_count = 0
    detect_fail_count = 0

    mapping_pass_count = 0
    mapping_fail_count = 0

    last_voice = None

    unique_unmatched = {} #type: dict[str, list[VoiceMatchDatabase]]

    for raw_line in all_lines:
        # Delete comments before processing
        line = raw_line.split('//', maxsplit=1)[0]

        for result in string_regex.finditer(line):
            # Record the last seen voice
            voice_on_line = voice_util.get_voice_on_line(line)
            if voice_on_line:
                last_voice = voice_on_line

            # We don't care about leading/trailing for our purposess
            stripped_path = result.group('data').strip()
            is_graphics = path_is_graphics(stripped_path, graphics_regexes)
            if is_graphics:
                check_result = graphics_is_detected_and_mapped(last_voice, stripped_path, existing_matches, unique_unmatched)
                if check_result.detected:
                    detect_pass_count += 1
                else:
                    detect_fail_count += 1

                if check_result.mapped:
                    mapping_pass_count += 1
                else:
                    mapping_fail_count += 1

    total_count = detect_pass_count + detect_fail_count
    print(f"DETECTION: {detect_pass_count}/{total_count} Successful ({detect_fail_count} Failures)")
    total_count = mapping_pass_count + mapping_fail_count
    print(f"MAPPING: {mapping_pass_count}/{total_count} Successful ({mapping_fail_count} Failures)")

    print("Unique failed matches:")
    for mod_path, failed_matches in unique_unmatched.items():
        print(f" - {mod_path} ({len(failed_matches)} times)")

    # TODO: generate proper fallback matching?
    fallback_matching = {
        # Special Images
        'black' : 'black',
        'white' : 'white',
        'red' : 'red',

        # Effects
        'effect/left' : 'effect/left',
        'effect/up' : 'effect/up',
        'effect/right' : 'effect/right',
        'effect/mask1' : 'effect/1',
        'effect/mask2' : 'effect/2',
        'effect/mask4' : 'effect/4',
        'effect/bullet_1a' : 'effect/bullet_1a',
        'effect/bullet_1b' : 'effect/bullet_1b',
        'effect/bullet_1c' : 'effect/bullet_1c',
        'effect/bullet_1d' : 'effect/bullet_1d',
        'effect/maskaa' : 'effect/aa',
        'effect/aka1' : 'effect/aka1',
        'effect/furiker_a' : 'effect/f_a',
        'effect/furiker_b' : 'effect/f_b',
        'effect/furiker_c' : 'effect/f_c',

        # Sprites Busstop
        # 'sprite/hara1a_04_' : 'sprites/ara/ara_d7a', # Not needed due to improved matching
        'effect/oyasiro' : 'sprites/oya/oya_d5', # Our mod actually draws this 'effect' as a sprite using DrawBustshot(...) (outline of hanyuu/oyashiro)
        'portrait/hara1a_01_' : 'sprites/ara/ara_d1', # This has been modified in our mod so that the voices match better. In the unmodded game it is sprites/ton/ton_d4a instead
        'portrait/hmi2a_13_': 'sprites/mio/mio_d14',

        # Backgrounds Busstop
        # 'background/hina_bus_03' : 'bg/hina/bus_03', # Not needed due to improved matching # Note: this fails 21 times
        'background/damu2' : 'bg/mizube/y_damu2', # Not sure if right imaage, is greyscale
        'background/damu4' : 'bg/hina/damu1m', # Not sure if right imaage, is greyscale and looks different

        # Sprites Outbreak (outbreak01_1.txt)
        'sprite/keisen_shinken_' : 'sprites/keiiti/sifuku_b/kei_3b', # Kei holding bat in action pose - replaced with kei with bat in normal pose

        # Sprites Kamikashimashi (outbreak02_1.txt)
        'portrait/ha1_sakebi_' : 'sprites/hanyu/miko/han_7',
        'sprite/ta3_hatena_' : 'sprites/takano/tak_9',
        'sprite/sa8a_akuwarai_a1_' : 'sprites/satoko/sifuku/sa_waraia1',
        'sprite/une1a_03_' : 'sprites/une/une_14',
        'sprite/sa1a_odoroki_a1_' : 'sprites/satoko/sa_akirerua1',
        'sprite/re1a_kaii_a1_' : 'sprites/rena/re_kaiia1',
        'sprite/sa1a_akuwarai_a1_' : 'sprites/satoko/sa_akuwaraia1',
        'sprite/me1a_warai_a1_' : 'sprites/mion/me_waraia1',

        # Backgrounds Kamikashimashi (outbreak02_1.txt)
        'background/kamik_ke_ky1' : 'bg/keisatu/ke_ky1',

        # Effects Kamikashimashi (outbreak02_1.txt)
        'effect/v_hurricane' : '<USE_MOD_VERSION>', # No equivalent mask so just use mod's mask (OG game just draws efe/different_spiral_1a)
        'effect/eye_base_b' : '<USE_MOD_VERSION>',
        'effect/eye_base_r' : '<USE_MOD_VERSION>',
        'effect/eye_kas' : '<NEED_IMAGE_REPLACEMENT>', # TODO: need to replace eye images with OG versions! Copy from preivous chapter?

        # Sprites Mehagashi
        # TODO: This is a silhouette cutout of keiichi. I'm not if just reusing the same image
        # instead of a special silhouette will work, but lets see if it just works.
        'effect/kei' : 'sprites/keiiti/2021/main/kei_ikari1',

        # flow.txt (main menu?)
        'title/07th-mod' : '<USE_MOD_VERSION>', # 07th-mod logo doesn't change depending on OG mode
        'title/title3scroll' : '<USE_MOD_VERSION>', # This is gated in the script so you shouldn't see it when using OG sprites anyway
        'title/rik_alt' : 'title/rik_3f', # Rika sprite for title menu easter egg TODO: need to test this works properly

        # staffroom15 - unused sprites
        # The below are gated only for OG sprites so they won't be seen anyway
        # TODO: update hou plus script for OG mode
        'sprite/aks1_warai_' : '<USE_MOD_VERSION>',
        'sprite/iri1_warai_' : '<USE_MOD_VERSION>',
        'sprite/oisi1_2_' : '<USE_MOD_VERSION>',
        'sprite/ta1_warai_' : '<USE_MOD_VERSION>',
    }

    debug_output = []
    fallback_matches = {} # type: dict[str, FallbackMatch]

    for mod_path, failed_matches in unique_unmatched.items():
        match_path = None
        match_source_description = 'No Match'

        maybe_statistics_for_path = statistics.get(mod_path, None)

        if match_path is None:
            match_path = fallback_matching.get(mod_path, None)
            match_source_description = 'Manual Fallback List'

            if match_path == '<USE_MOD_VERSION>':
                match_path = mod_path
                match_source_description = 'Manual Fallback List (Use Modded Image)'

        if match_path is None:
            if maybe_statistics_for_path:
                match_path, _match_count = maybe_statistics_for_path[0]
                match_source_description = f'Popularity ({maybe_statistics_for_path})'

        if match_path is not None:
            fallback_matches[mod_path] = FallbackMatch(match_path, match_source_description)
        else:
            debug_output.append(f" - {mod_path} ({len(failed_matches)} times) | {maybe_statistics_for_path}")

    num_fallback_matches = len(debug_output)
    if num_fallback_matches > 0:
        print(f"Unique failed matches not covered by any fallback: {num_fallback_matches}")
        for line in debug_output:
            print(line)
    else:
        print("PASS: All matches covered by a fallback")

    return debug_output, fallback_matches

    # TODO: Use facial expression in filename to match sprites
    # TODO: For Busstop, map numbers to facial expression

    # TODO: save final mapping instead of just printing it out


# TODO generate match statistics across all scripts to hint to developer what the manual mapping should be
# Use 'stats' folder?
# statistics = path -> match statistics (ignoring lastVoice)
# Should probably have used python's built in statistics, but I forgot to
def collect_statistics_from_db(existing_matches: VoiceMatchDatabase, statistics: dict[str, dict[str, int]]):
    for _, voiceMatches in existing_matches.db.items():
        for match in voiceMatches:
            if match.mod_path is None:
                continue

            if match.og_path is None:
                continue

            mod_path = str(match.mod_path).lower()
            og_path = str(match.og_path).lower()

            # Create new dict for mod path -> dictionary of count per each og_path
            if mod_path not in statistics:
                statistics[mod_path] = {}

            count_dict_for_mod_path = statistics[mod_path]

            # Increment the number of times og_path was seen
            if og_path not in count_dict_for_mod_path:
                count_dict_for_mod_path[og_path] = 0

            count_dict_for_mod_path[og_path] += 1


def collect_statistics(mod_script_dir: str, pattern: str) -> dict[str, dict[str, int]]:
    statistics = {} # dict[str, dict[str, int]]

    for modded_script_path in Path(mod_script_dir).glob(pattern):
        db_path = common.get_voice_db_path(modded_script_path)
        existing_matches = VoiceMatchDatabase.deserialize(db_path)
        collect_statistics_from_db(existing_matches, statistics)

    return statistics

def collect_sorted_statistics(mod_script_dir: str, pattern: str) -> dict[str, list[str, int]]:
    unsorted_statistics = collect_statistics(mod_script_dir, pattern)

    sorted_statistics = {}

    for mod_path, og_path_counts in unsorted_statistics.items():
        sorted_statistics[mod_path] = sorted(og_path_counts.items(), key=operator.itemgetter(1), reverse=True)

    return sorted_statistics

all_match_data = AllMatchData()

output_folder = Path('mod_usable_files')

pattern = '*.txt'
statistics_pattern = '*.txt' #'*.txt' # Matching from other scripts will give more averaged results, but this may cause inconsistencies if one script uses one sprite and another uses other sprites

# unmodded_input_file = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Installer Test/HigurashiEp10_Data/StreamingAssets/Scripts/mehagashi.txt'
mod_script_dir = 'D:/drojf/large_projects/umineko/HIGURASHI_REPOS/10 hou-plus/Update/'

modded_game_cg_dir = 'D:/games/steam/steamapps/common/Higurashi When They Cry Hou+ Modded/HigurashiEp10_Data/StreamingAssets/CG'

# Get a list of regexes which indicate a path is a graphics path
graphics_regexes = get_graphics_regexes(modded_game_cg_dir)

scanned_any_scripts = False

# Firstly, collect statistics from all chapters
statistics = collect_sorted_statistics(mod_script_dir, statistics_pattern)

# TODO: save to file?
# for mod_path, og_paths in statistics.items():
#     print(f'{mod_path}: {og_paths}')

output_per_chapter = []

merged_fallback_matches = {} # dict[str, FallbackMatch]

for modded_script_path in Path(mod_script_dir).glob(pattern):
    scanned_any_scripts = True

    # Load the matches found by the main matching script
    db_path = common.get_voice_db_path(modded_script_path)
    existing_matches = VoiceMatchDatabase.deserialize(db_path)

    all_match_data.set_voice_database(modded_script_path, existing_matches)

    print(f"Loaded {len(existing_matches.db)} voice sections from [{db_path}]")

    debug_output, fallback_match_for_chapter = verify_one_script(modded_script_path, graphics_regexes, existing_matches, statistics)

    # Save the per-chapter fallback to the output path
    all_match_data.set_per_script_fallback(modded_script_path.stem, fallback_match_for_chapter)

    merged_fallback_matches |= fallback_match_for_chapter

    output_per_chapter.append((Path(modded_script_path).stem, debug_output))

print("\n------------ Summary per script ------------")
for script_name, debug_output_list in output_per_chapter:
    if debug_output_list:
        print(f"{script_name} - Missing items for :")
        for line in debug_output_list:
            print(line)
    else:
        print(f"{script_name} - PASS")


if not scanned_any_scripts:
    raise Exception("No files were scanned. Are you sure pattern is correct?")

# TODO: add a fallback based purely on statistics over all know matchings.
# The below only records fallbacks which were actually used, rather than all possible matchings.
# This is to be used if a new sprite call is added, to avoid having to re-do the matching just for that one sprite call.# Save the merged fallback matching to .json file
save_debug_info = True

all_match_data.set_global_fallback(merged_fallback_matches)

save_to_json(get_match_data_as_plain_dict(all_match_data, save_debug_info), output_folder.joinpath('mapping.json'))
