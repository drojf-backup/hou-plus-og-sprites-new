import re


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

def partial_path_to_regex(filenamefolder_list) -> re.Pattern:
    item = '|'.join(filenamefolder_list)
    complete_regex = f'"((?:{item})[^"]*)"'
    return re.compile(complete_regex)

OG_CG_REGEX = partial_path_to_regex(OG_CG_LIST)  # type: list[re.Pattern]
MOD_CG_REGEX = partial_path_to_regex(MOD_CG_LIST)  # type: list[re.Pattern]

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