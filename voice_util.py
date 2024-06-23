import re


voicePathRegex = re.compile(r'^\s*ModPlayVoiceLS\([^,]+,[^,]+,\s*"\s*([^"]+)\s*"')
def get_voice_on_line(line) -> str:
    match = voicePathRegex.search(line)
    if match:
        return match.group(1)

    return None
