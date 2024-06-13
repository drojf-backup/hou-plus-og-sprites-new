# hou-plus-og-sprites-new

## Folder/File format for mod DLL to read

Currently mod files are stored in a streamingassets subfolder like OGSprites or OGBackgrounds

The existing behavior will be kept (if a file exists within that folder with the correct name, it will be used), but add on:

- On startup, check if file called `mapping/default.json` exists, containing dictionary of `Mod CG -> OG CG`
- If it does, load that mapping file (image paths relative to `mapping/image` folder)
 - need to check if voice file name is unique enough, or need full path
- Also load all `mapping/script/*.json` files, one corresponding to each script file. These contain a dictionary of voice file name (string) to `(Mod CG->OG CG)` mapping
- Then when playing:
 - The game keeps track of a dictionary of `(Mod CG->OG CG)`
 - Each time a voice file is encountered, the the game will update the dictionary according to the corresponding `[scriptname].json` file in the `mapping/script` folder
 - If no such entry exists in dictionary, should use default mapping defined in `default.json`

To compress the number of sprite calls in the individual script `.json`, can delete entries which are identical to the `default.json` file.

However, don't try to optimize too much (eg if the same mapping occurs multiple times in one script), as it makes loading/saving more difficult

## Testing

### Save/Load Testing

Make sure to test loading and saving works correctly. I think save/load should take care of this but not sure.

For example, test the following:

- Default mapping says to display "A"
- Script mapping says to display "B"
- "B" is displayed
- Save game
- Load game
- TEST: Check that "B" is still displayed
