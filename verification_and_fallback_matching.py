
from pathlib import Path
import re
import common
from common import VoiceMatchDatabase
import voice_util

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

def verify_one_script(mod_script_path: str, graphics_regexes: list[re.Pattern], existing_matches: VoiceMatchDatabase):
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
        'black' : 'black',
        'white' : 'white',
        'red' : 'red',
    }

    print("Unique failed matches not covered by fallback:")
    for mod_path, failed_matches in unique_unmatched.items():
        if mod_path not in fallback_matching:
            print(f" - {mod_path} ({len(failed_matches)} times)")




pattern = 'busstop01.txt'

# unmodded_input_file = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Installer Test/HigurashiEp10_Data/StreamingAssets/Scripts/mehagashi.txt'
mod_script_dir = 'D:/drojf/large_projects/umineko/HIGURASHI_REPOS/10 hou-plus/Update/'

modded_game_cg_dir = 'D:/games/steam/steamapps/common/Higurashi When They Cry Hou+ Modded/HigurashiEp10_Data/StreamingAssets/CG'

# Get a list of regexes which indicate a path is a graphics path
graphics_regexes = get_graphics_regexes(modded_game_cg_dir)

for modded_script_path in Path(mod_script_dir).glob(pattern):
    # Load the matches found by the main matching script
    db_path = common.get_voice_db_path(modded_script_path)
    existing_matches = VoiceMatchDatabase.deserialize(db_path)

    print(f"Loaded {len(existing_matches.db)} voice sections from [{db_path}]")

    verify_one_script(modded_script_path, graphics_regexes, existing_matches)