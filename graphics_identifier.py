import re


MOD_CG_LIST = [
    'background/',
    r'black\b',
    'chapter/',
    'credits/',
    'effect/',
    r'filter_hanyu\b',
    'omake/',
    'portrait/',
    r'red\b',
    'scene/',
    'sprite/',
    'title/',
    r'transparent\b',
    r'white\b',
    r'windo_filter\b',
    r'windo_filter_adv\b',
    r'windo_filter_nvladv\b',
]

OG_CG_LIST = [
    'bg/',
    r'black\b',
    'chapter/',
    r'cinema_window\b',
    r'cinema_window_name\b',
    'credits/',
    'effect/',
    r'furiker_a\b',
    r'furiker_b\b',
    r'hanyuu_background\b',
    'img/',
    r'no_data\b',
    'omake/',
    'sprites/',
    'title/',
    r'white\b',
    r'windo_filter\b',
]

def partial_path_to_regex(filenamefolder_list) -> re.Pattern:
    item = '|'.join(filenamefolder_list)
    complete_regex = f'"((?:{item})[^"]*)"'
    return re.compile(complete_regex)

OG_CG_REGEX = partial_path_to_regex(OG_CG_LIST)  # type: re.Pattern
MOD_CG_REGEX = partial_path_to_regex(MOD_CG_LIST)  # type: re.Pattern

# returns None if no graphics found!
def get_graphics_path_on_line(line, is_mod) -> str:
    regex = OG_CG_REGEX
    if is_mod:
        regex = MOD_CG_REGEX

    all_matches = []
    for match in regex.finditer(line):
        if match:
            all_matches.append(match.group(1))

    return all_matches
