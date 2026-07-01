# Calibration-Generator — Prusa XL fork

This is a fork of [prahjister/Calibration-Generator](https://github.com/prahjister/Calibration-Generator)
adapted for the **Prusa XL** (5 independent heads + non-trivial custom start gcode).
See "Prusa XL additions" below. All original credit and documentation follow.

## Prusa XL additions

### Auto mode (default) — just pick a tool

Check **Auto-generate Prusa XL start/end gcode** (on by default), pick the **Active Tool**
(`T0`–`T4`), fill in the normal inputs (temps, bed temp, nozzle diameter, dimensions), and generate.
The program builds **resolved, printer-ready** Prusa XL start gcode for you — **no more copying and
pasting start gcode.** It emits, for the selected head:

- steppers on + printer/gcode/feature checks (`M17`, `M862.3 P"XL"`, `M862.5`, `M862.6`)
- nozzle-diameter check for the tool (`M862.1 T<tool> P<nozzle>`)
- unused heaters turned off
- set bed + gentle probing temp → **home XY** → **pick the tool** → **home Z** → **mesh bed
  leveling (`G29`)**
- wait bed → heat to print temp → **prime/purge line**
- absolute-extrusion normalisation for the tower (`M82`, `G92 E0`)

Matching end gcode (cool down, lift, park, disable steppers) is generated too. Temperatures come
from **Starting Temp** / **Bed Temp**, nozzle from **Nozzle Diameter** — all the normal inputs.

The generator lives in `RetCalMain.py`: `prusa_xl_start_gcode()` / `prusa_xl_end_gcode()`. It mirrors
PrusaSlicer's stock XL "Machine Start G-code" flow but with every macro resolved. Tune it there if
your firmware/flow differs (e.g. probing temp, prime location).

### Manual mode — paste or preset (advanced)

Uncheck the Auto box to use the text boxes instead:

- **Start Gcode** box fully replaces the default start block; **End Gcode** box replaces the end.
- **Start-gcode preset** dropdown loads any `.gcode`/`.txt` file found under `presets/`
  (sub-folders scanned recursively; the dropdown shows the path).
- **Placeholders** substituted at generation time: `{tool}` → Active Tool index,
  `{hotend_temp}` → Starting Temp, `{bed_temp}` → Bed Temp. See
  `presets/Example - Prusa XL PLA.gcode`.

Manual mode expects **resolved** gcode — this tool is **not a slicer**. It does **not** evaluate
PrusaSlicer's macro language (`{if ...}{endif}`, `[first_layer_bed_temperature]`, `{initial_tool}`,
`=~`). A raw PrusaSlicer template (e.g. `presets/xl-start-gode examples/stock.gcode`) will **not**
run as-is; if a selected preset still contains such tokens, the generator warns and flags the
offending lines near the top of the saved `.gcode`. To get resolved gcode manually, slice a small
object in PrusaSlicer and copy the start block from the exported file. If your start gcode hardcodes
a head, set **Active Tool** to the same head.

Implementation note: the new controls are built at runtime in `RetCalMain.py`
(`add_prusa_controls`), so the auto-generated `RetCalui.py` stays untouched and safe to
regenerate from `RetCalui.ui` with `ui2py.bat`.

Run from source with a real Python that has PyQt5 (`pip install PyQt5`): `python RetCalMain.py`.

---

Original article

https://www.cnx-software.com/2019/09/05/how-to-easily-calibrate-retraction-in-3d-printers/

Updated article

https://www.cnx-software.com/2020/07/08/3d-printer-retraction-calibration-vol-ii-calibration-generator-program-release/

The code assumes that the following is setup & configure for running with your profile:

- Python3 (with pip) : https://www.python.org/downloads/
- pyinstaller : https://www.pyinstaller.org/
- pyuic5-tool : https://pypi.org/project/pyuic5-tool/
- pyqt5ac : https://pypi.org/project/pyqt5ac/

Run the commands in the following order to generate the EXE:

- ui2py.bat
- convertexe.bat

This will create an EXE in the .\dist\ folder 
