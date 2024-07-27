
import operator
from pathlib import Path
import re
import common
from common import VoiceMatchDatabase
import voice_util

PRINT_FAILED_MATCHES = False

class FallbackMatch:
    def __init__(self, fallback_match_path: str, source_description: str) -> None:
        self.fallback_match_path = fallback_match_path
        self.source_description = source_description

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

def verify_one_script(mod_script_path: str, graphics_regexes: list[re.Pattern], existing_matches: VoiceMatchDatabase, statistics: dict[str, list[str, int]]):
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
        'sprite/hara1a_04_' : 'sprites/ara/ara_d7a',
        'effect/oyasiro' : 'sprites/oya/oya_d5', # Our mod actually draws this 'effect' as a sprite using DrawBustshot(...) (outline of hanyuu/oyashiro)
        'portrait/hara1a_01_' : 'sprites/ara/ara_d1', # This has been modified in our mod so that the voices match better. In the unmodded game it is sprites/ton/ton_d4a instead
        'portrait/hmi2a_13_': 'sprites/mio/mio_d14',

        # Backgrounds Busstop
        'background/hina_bus_03' : 'bg/hina/bus_03', # Note: this fails 21 times
        'background/damu2' : 'bg/mizube/y_damu2', # Not sure if right imaage, is greyscale
        'background/damu4' : 'bg/hina/damu1m', # Not sure if right imaage, is greyscale and looks different

        # Sprites Outbreak (outbreak01_1.txt)
        'sprite/keisen_shinken_' : 'sprites/keiiti/sifuku_b/kei_3b', # Kei holding bat in action pose - replaced with kei with bat in normal pose
        'effect/v_hurricane' : '<USE_MOD_VERSION>', # No equivalent mask so just use mod's mask (OG game just draws efe/different_spiral_1a)
        'effect/eye_base_b' : '<USE_MOD_VERSION>',
        'effect/eye_base_r' : '<USE_MOD_VERSION>',
        'effect/eye_kas' : '<NEED_IMAGE_REPLACEMENT>', # TODO: need to replace eye images with OG versions! Copy from preivous chapter?
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

        if match_path is None:
            if maybe_statistics_for_path:
                match_path, _match_count = maybe_statistics_for_path[0]
                match_source_description = f'Statistically most popular previous match ({maybe_statistics_for_path})'

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

pattern = 'busstop01.txt'
statistics_pattern = pattern #'*.txt' # Matching from other scripts will give more averaged results, but this may cause inconsistencies if one script uses one sprite and another uses other sprites

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

for modded_script_path in Path(mod_script_dir).glob(pattern):
    scanned_any_scripts = True

    # Load the matches found by the main matching script
    db_path = common.get_voice_db_path(modded_script_path)
    existing_matches = VoiceMatchDatabase.deserialize(db_path)

    print(f"Loaded {len(existing_matches.db)} voice sections from [{db_path}]")

    verify_one_script(modded_script_path, graphics_regexes, existing_matches, statistics)

if not scanned_any_scripts:
    raise Exception("No files were scanned. Are you sure pattern is correct?")
