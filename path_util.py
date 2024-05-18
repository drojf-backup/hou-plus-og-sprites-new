
from pathlib import Path


def should_exclude(path: Path, exclude: list[str]):
    path = path.replace('\\', '/')

    if exclude is None:
        return False

    for ex in exclude:
        if ex in path:
            return True

    return False


def lc_name_to_path(path: str, filetypes='*.*', exclude=None) -> dict[str, str]:
    exclude = [ex.replace('\\', '/') for ex in exclude]

    lc_name_to_path = {}
    for path in Path(path).rglob(filetypes):
        if should_exclude(str(path), exclude):
            # print(f"Skipping path {path}")
            continue

        lc_name = path.stem.lower()
        lc_name_to_path[lc_name] = path

    return lc_name_to_path


# unmodded_cg = 'C:/Program Files (x86)/Steam/steamapps/common/Higurashi When They Cry Hou+ Unmodded/HigurashiEp10_Data/StreamingAssets/CG'

# lc_name_to_path = lc_name_to_path(unmodded_cg, exclude=['sprites/'])

# # print(lc_name_to_path)
