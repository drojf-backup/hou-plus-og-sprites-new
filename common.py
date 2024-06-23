import os
from pathlib import Path
import pickle
import re
import graphics_identifier
import character_database

missing_character_key = "ERROR_MISSING_CHARACTER"


modSpritePathCharacterNameRegex = re.compile(
    r'"((?:sprite)|(?:portrait))/([a-zA-Z]*)')

effectCharacterNameRegex = re.compile(
    r'"(effect)/((:?hara)|(:?hnit)|(:?hoda)|(:?hoka)|(:?hton)|(:?hyos))')

effectEyeCharacterNameRegex = re.compile(
    r'"(effect)/eye_((:?kas)|(:?kei)|(:?me)|(:?re)|(:?sa))')


class CallData:
    def __init__(self, line, is_mod):
        self.line = line
        self.type = None  # type
        self.matching_key = None  # lookup_key
        self.debug_character = None
        self.path = graphics_identifier.get_graphics_on_line(line, is_mod)
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

                if mod_character == 'mo' and 'mo1_' in line:
                    mod_character = 'mo1'

                if mod_character == 'mo' and 'mo2_' in line:
                    mod_character = 'mo2'

                if mod_character == 'mo' and 'mo3_' in line:
                    mod_character = 'mo3'

                self.debug_character = mod_character

                # To cope with the character name in the modded game and OG game being different,
                # normalize the names
                #
                # Do this by mapping the modded character name to a normalized name, eg 'ri'(mod)->'rika'(normalized)
                # Then map the normalized name to the OG name, eg 'rika'(normalized)->'rika'(og)
                # The 'matching_key' is then set to the OG name, so we can cross check it against the earlier git commit of the og game
                if mod_character in character_database.mod_to_name:
                    self.matching_key = character_database.name_to_og[character_database.mod_to_name[mod_character]]
                else:
                    self.matching_key = f'{missing_character_key}: {mod_character}'
                    # raise Exception(f"No mod character {
                    #                 mod_character} in database for line {line}")


class ModToOGMatch:
    def __init__(self, og_calldata, og_path) -> None:
        self.og_calldata = og_calldata #type: CallData
        self.og_path = og_path #type: str

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

    # This is used to make sure all voices are covered
    # The final output can be trimmed of 'blank' voice sections later
    def acknowledge_voice(self, voice: str):
        if voice not in self.db:
            self.db[voice] = []

    def serialize(self, output_file: str):
        # TODO: This should really be done atomically, but since
        # this script will rarely be executed don't worry about it for now
        with open(output_file, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def deserialize(input_file: str) -> 'VoiceMatchDatabase':
        with open(input_file, 'rb') as f:
            return pickle.load(f)

voice_db_folder = 'voice_db'

def get_voice_db_path(mod_script_path: str) -> str:
    os.makedirs(voice_db_folder, exist_ok=True)
    return os.path.join(voice_db_folder, f'{Path(mod_script_path).stem}_voice_db.pickle')
