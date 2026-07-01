# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\pythonstuff\retraction.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!

import sys
import os
import re
import glob
from PyQt5 import QtCore, QtGui, QtWidgets
from RetCalui import Ui_MainWindow
from decimal import Decimal


ui=None

# --- Prusa XL fork additions ---------------------------------------------
# Directory that holds per-head start-gcode presets. Lives next to the script
# (or next to the .exe when frozen by PyInstaller) so users can drop in their
# own Prusa XL start-gcode examples after cloning.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRESET_DIR = os.path.join(BASE_DIR, "presets")


def list_presets():
    """Return sorted preset file paths found under PRESET_DIR, recursively
    (so start-gcode examples can be organised in sub-folders)."""
    if not os.path.isdir(PRESET_DIR):
        return []
    files = glob.glob(os.path.join(PRESET_DIR, "**", "*.gcode"), recursive=True) + \
        glob.glob(os.path.join(PRESET_DIR, "**", "*.txt"), recursive=True)
    return sorted(files, key=lambda p: p.lower())


def read_preset(path):
    """Read a preset file's text, tolerating encoding issues."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# PrusaSlicer "Machine Start G-code" uses a macro language that only resolves at
# slice time ({if ...}{endif}, [first_layer_bed_temperature], {initial_tool},
# regex ternaries with =~, etc.). This tool is NOT a slicer, so such templates
# must not be fed to the printer verbatim. Detect leftover tokens after our own
# {tool}/{hotend_temp}/{bed_temp} substitution and warn the user.
_UNRESOLVED = re.compile(r"\{[^}\n]*\}|\[[a-zA-Z_]\w*(?:\[[0-9]+\])?\]|=~")


def find_unresolved(text):
    """Return up to 5 sample lines that still contain PrusaSlicer template
    tokens (i.e. gcode the printer cannot execute)."""
    bad = [ln.strip() for ln in text.splitlines() if _UNRESOLVED.search(ln)]
    return bad[:5]


PRUSA_XL_TOOLS = 5


def prusa_xl_start_gcode(tool, hotend, bed, nozzle, travel, dimx, dimy,
                         num_tools=PRUSA_XL_TOOLS):
    """Build resolved, printer-ready Prusa XL start gcode for a single active
    tool, from the normal inputs. Mirrors the flow of PrusaSlicer's stock XL
    "Machine Start G-code" (steppers, checks, home XY, pick tool, home Z, mesh
    bed leveling, heat, prime) but with all macros resolved -- no {if}/[vars].

    A gentle probing temperature is used for homing/MBL to avoid oozing onto the
    bed, then the nozzle is brought to the full print temperature before the
    prime line.
    """
    mbl = min(170, int(hotend))          # gentle probe/MBL temperature
    tspeed = max(1, int(travel * 60))    # mm/min
    # Prime line near the front-left corner, clear of the centred tower.
    px, py = 5.0, 5.0
    L = []
    a = L.append
    a("; Prusa XL start gcode (auto-generated from inputs)")
    a(f"; active tool T{tool}  nozzle {nozzle}  hotend {int(hotend)}C  bed {int(bed)}C")
    a("M17 ; enable steppers")
    a('M862.3 P "XL" ; printer model check')
    a("M862.5 P2 ; g-code level check")
    a('M862.6 P"Input shaper" ; FW feature check')
    a("G90 ; absolute coordinates")
    a("M83 ; relative extrusion (for priming)")
    a(f"M862.1 T{tool} P{nozzle} ; nozzle diameter check")
    a("; turn off unused heaters")
    for t in range(num_tools):
        if t != tool:
            a(f"M104 T{t} S0")
    a("M217 Z2 ; toolchange z-hop")
    a(f"M140 S{int(bed)} ; set bed temp")
    a(f"M104 T{tool} S{mbl} ; set nozzle probing temp")
    a("; home XY")
    a("G28 XY")
    a(f"G1 F{tspeed}")
    a(f"T{tool} S1 L0 D0 ; pick the active tool")
    a(f"M109 T{tool} S{mbl} ; wait for probing temp")
    a("M84 E ; relax extruder for accurate probing")
    a("G28 Z ; home Z with the active tool")
    a("G29 ; mesh bed leveling")
    a(f"M190 S{int(bed)} ; wait for bed temp")
    a(f"M104 T{tool} S{int(hotend)} ; set print temp")
    a(f"M109 T{tool} S{int(hotend)} ; wait for print temp")
    a("; prime / purge line at front-left")
    a("G1 Z5 F1200")
    a(f"G1 X{px} Y{py} F{tspeed}")
    a("G1 Z0.2 F720")
    a("G1 E9 F1000 ; prime nozzle")
    a(f"G1 X{px + 100:.1f} E8 F1000 ; purge line")
    a(f"G1 X{px + 120:.1f} E1 F1000 ; thin wipe")
    a("G1 Z2 F720")
    a("G92 E0 ; reset extruder")
    return "\n".join(L)


def prusa_xl_end_gcode(tool, dimx, dimy):
    """Build resolved Prusa XL end gcode: cool down, lift, park, disable."""
    L = []
    a = L.append
    a("; Prusa XL end gcode (auto-generated)")
    a("M104 S0 ; turn off hotend")
    a("M140 S0 ; turn off bed")
    a("M107 ; turn off fan")
    a("G91 ; relative")
    a("G1 Z10 F720 ; raise Z")
    a("G90 ; absolute")
    a(f"G1 X0 Y{int(dimy)} F3000 ; park / present the print")
    a("M84 ; disable steppers")
    return "\n".join(L)


def add_prusa_controls(ui, MainWindow):
    """Add the Prusa XL controls (tool selector, preset dropdown, end-gcode box)
    to the existing UI at runtime, so the generated RetCalui.py stays untouched
    and safe to regenerate from RetCalui.ui with pyuic5."""

    # Grow the fixed-size window to make room for the new bottom panel.
    MainWindow.setMinimumSize(QtCore.QSize(810, 900))
    MainWindow.setMaximumSize(QtCore.QSize(810, 900))
    MainWindow.resize(810, 900)

    cw = ui.centralwidget

    def _label(text, x, y, w, h):
        lbl = QtWidgets.QLabel(cw)
        lbl.setGeometry(QtCore.QRect(x, y, w, h))
        lbl.setText(text)
        lbl.show()
        return lbl

    # Relabel the existing custom-gcode box: it now fully replaces the default
    # start gcode instead of being appended to it.
    ui.label_21.setText("Start Gcode (manual mode only)")

    # Auto mode: generate Prusa XL start/end gcode from the inputs. Default ON,
    # so the user only has to pick a tool -- no pasting required.
    ui.autoStart = QtWidgets.QCheckBox("Auto-generate Prusa XL start/end gcode", cw)
    ui.autoStart.setGeometry(QtCore.QRect(20, 648, 300, 20))
    ui.autoStart.setChecked(True)
    ui.autoStart.show()

    # Active tool selector (T0..T4).
    _label("Prusa XL Active Tool", 20, 672, 200, 18)
    ui.toolSelect = QtWidgets.QComboBox(cw)
    ui.toolSelect.setGeometry(QtCore.QRect(20, 692, 120, 26))
    ui.toolSelect.addItems(["T0", "T1", "T2", "T3", "T4"])
    ui.toolSelect.show()

    # Start-gcode preset dropdown (manual mode; populated from ./presets).
    _label("Start-gcode preset", 150, 672, 165, 18)
    ui.presetSelect = QtWidgets.QComboBox(cw)
    ui.presetSelect.setGeometry(QtCore.QRect(150, 692, 165, 26))
    ui.presetSelect.show()

    # End-gcode box (manual mode; replaces the default end sequence).
    _label("End Gcode (manual mode only)", 20, 726, 280, 18)
    ui.customEndGcode = QtWidgets.QPlainTextEdit(cw)
    ui.customEndGcode.setGeometry(QtCore.QRect(20, 746, 295, 132))
    ui.customEndGcode.show()

    refresh_presets(ui)
    ui.presetSelect.currentIndexChanged.connect(lambda _idx: load_preset(ui))

    # Grey out the manual start/end widgets while auto mode is on.
    def _sync_auto(checked=None):
        manual = not ui.autoStart.isChecked()
        ui.presetSelect.setEnabled(manual)
        ui.customGcode.setEnabled(manual)
        ui.customEndGcode.setEnabled(manual)
        ui.label_21.setEnabled(manual)
    ui.autoStart.toggled.connect(_sync_auto)
    _sync_auto()


def refresh_presets(ui):
    """Populate the preset dropdown from PRESET_DIR."""
    ui.presetSelect.blockSignals(True)
    ui.presetSelect.clear()
    ui.presetSelect.addItem("-- select preset --", "")
    for path in list_presets():
        ui.presetSelect.addItem(os.path.relpath(path, PRESET_DIR), path)
    ui.presetSelect.blockSignals(False)


def load_preset(ui):
    """Load the selected preset file's text into the start-gcode box."""
    path = ui.presetSelect.currentData()
    if path:
        ui.customGcode.setPlainText(read_preset(path))
# -------------------------------------------------------------------------

#Start Raft
#def raft (file,xpos,ypos,ps,eValueresult,lh):
#    return file,xpos,ypos




#Start Gcode
 
def gengcode ():
    global ui
    

    name = QtWidgets.QFileDialog.getSaveFileName(ui.centralwidget, 'Save Gcode', filter="(*.gcode)")
    if len(name[0])>0:
        
        file = open(name[0],'w')

#Start Gcode Retraction Distance
        srd = float(ui.startRetractiondistance.text())
        ird = float(ui.incrementRetractiondistance.text())
        
        file.write(f";Calibration Generator 1.3.1\n")
        file.write(f";\n")
        file.write(f";\n")
        file.write(f";Retraction Distance from the top looking down\n")
        file.write(f";\n")
        file.write(f";       {round(Decimal(srd+ird*11),2)}    {round(Decimal(srd+ird*10),2)}    {round(Decimal(srd+ird*9),2)}    {round(Decimal(srd+ird*8),2)}\n")
        file.write(f";		|		|		|		|\n")
        file.write(f";\n")
        file.write(f";{round(Decimal(srd+ird*12),2)}-                               -{round(Decimal(srd+ird*7),2)}\n")
        file.write(f";\n")
        file.write(f";\n")
        file.write(f";{round(Decimal(srd+ird*13),2)}-                               -{round(Decimal(srd+ird*6),2)}\n")
        file.write(f";\n")
        file.write(f";\n")
        file.write(f";{round(Decimal(srd+ird*14),2)}-                               -{round(Decimal(srd+ird*5),2)}\n")
        file.write(f";\n")
        file.write(f";\n")
        file.write(f";{round(Decimal(srd+ird*15),2)}-                               -{round(Decimal(srd+ird*4),2)}\n")
        file.write(f";\n")
        file.write(f";		|		|		|		|\n")
        file.write(f";       {round(Decimal(srd+ird*0),2)}    {round(Decimal(srd+ird*1),2)}    {round(Decimal(srd+ird*2),2)}    {round(Decimal(srd+ird*3),2)}\n")
        file.write(f";\n")
        file.write(f";\n")

        #Variables by Height


        srs = float(ui.startRetractionspeed.text())
        irs = float(ui.incrementRetractionspeed.text())
        tsh = float(ui.tempStarthotend.text())
        tih = float(ui.tempIncrementhotend.text())
        fs = float(ui.speedFan.text())
        fsi = float(ui.speedFanIncrement.text())
        lh = float(ui.layerHeight.text())
        ts = float(ui.speedTravel.text())
        lt = float(ui.layersTest.text())
        nt = float(ui.NumTests.text())


        file.write(f";Variables by Height\n")
        file.write(f";\n")
        file.write(f";Height         Retraction  Nozzle      Fan\n")
        file.write(f";               Speed       Temp        Speed\n")
        file.write(f";\n")

        cnt = int(nt-1)

        for loopx in range(int(nt)):
            file.write(f";{int(lt)} layers      {round(Decimal(srs+irs*cnt),2)}      {round(Decimal(tsh+tih*cnt),2)}      {round(Decimal(fs+fsi*cnt),2)}\n")
            cnt = cnt-1


#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*14),2)}		{round(Decimal(tsh+tih*14),2)}		{round(Decimal(fs+fsi*14),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*13),2)}		{round(Decimal(tsh+tih*13),2)}		{round(Decimal(fs+fsi*13),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*12),2)}		{round(Decimal(tsh+tih*12),2)}		{round(Decimal(fs+fsi*12),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*11),2)}		{round(Decimal(tsh+tih*11),2)}		{round(Decimal(fs+fsi*11),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*10),2)}		{round(Decimal(tsh+tih*10),2)}		{round(Decimal(fs+fsi*10),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*9),2)}		{round(Decimal(tsh+tih*9),2)}		{round(Decimal(fs+fsi*9),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*8),2)}		{round(Decimal(tsh+tih*8),2)}		{round(Decimal(fs+fsi*8),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*7),2)}		{round(Decimal(tsh+tih*7),2)}		{round(Decimal(fs+fsi*7),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*6),2)}		{round(Decimal(tsh+tih*6),2)}		{round(Decimal(fs+fsi*6),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*5),2)}		{round(Decimal(tsh+tih*5),2)}		{round(Decimal(fs+fsi*5),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*4),2)}		{round(Decimal(tsh+tih*4),2)}		{round(Decimal(fs+fsi*4),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*3),2)}		{round(Decimal(tsh+tih*3),2)}		{round(Decimal(fs+fsi*3),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*2),2)}		{round(Decimal(tsh+tih*2),2)}		{round(Decimal(fs+fsi*2),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*1),2)}		{round(Decimal(tsh+tih*1),2)}		{round(Decimal(fs+fsi*1),2)}\n")
#        file.write(f";{int(lt)} layers		{round(Decimal(srs+irs*0),2)}		{round(Decimal(tsh+tih*0),2)}		{round(Decimal(fs+fsi*0),2)}\n")

        dx = float(ui.dimensionX.text())
        dy = float(ui.dimensionY.text())
        ps = float(ui.printSpeed.text())
        nd = float(ui.nozzleDiameter.text())
        fd = float(ui.filamentDiameter.text())
        em = float(ui.extrusionMultiplier.text())
        tb = float(ui.tempBed.text())

#Custom Gcode
        tool = int(ui.toolSelect.currentIndex())   # 0..4 -> active Prusa XL head

        # Auto mode (default): generate resolved Prusa XL start/end gcode from the
        # inputs -- the user only picks a tool. Manual mode: use the text boxes.
        if ui.autoStart.isChecked():
            sgcode = prusa_xl_start_gcode(tool, tsh, tb, nd, ts, dx, dy)
            egcode = prusa_xl_end_gcode(tool, dx, dy)
        else:
            sgcode = str(ui.customGcode.toPlainText())
            egcode = str(ui.customEndGcode.toPlainText())

        # Substitute placeholders inside custom start/end gcode so PrusaSlicer-style
        # templates receive the real values selected in the UI. Uses str.replace
        # (not .format) so stray { } in pasted gcode never raise. (No-op for
        # auto-generated gcode, which already contains resolved values.)
        def fill(text):
            return (text.replace("{tool}", str(tool))
                        .replace("{hotend_temp}", str(int(tsh)))
                        .replace("{bed_temp}", str(int(tb))))

        # Guard: a PrusaSlicer "Machine Start G-code" template (with {if}/[vars]/=~)
        # cannot run on the printer as-is. Flag any leftover tokens after fill().
        unresolved = find_unresolved(fill(sgcode)) + find_unresolved(fill(egcode))
        if unresolved:
            file.write(f";\n")
            file.write(f";!!! WARNING: start/end gcode contains UNRESOLVED PrusaSlicer template tokens.\n")
            file.write(f";!!! This gcode will likely FAIL on the printer. Use resolved machine gcode\n")
            file.write(f";!!! (copy the start block from a sliced .gcode) or the {{tool}}/{{hotend_temp}}/{{bed_temp}} placeholders.\n")
            for ln in unresolved:
                file.write(f";!!!   {ln}\n")
            file.write(f";\n")

        file.write(f";\n")
        file.write(f";\n")
        file.write(f";All inputs\n")
        file.write(f";\n")
        file.write(f";Dimension X 					{int(dx)}\n")
        file.write(f";Dimension Y 					{int(dy)}\n")
        file.write(f";Starting Retraction Distance	{srd}\n")
        file.write(f";Increment Retraction 			{ird}\n")
        file.write(f";Start Retraction Speed 		{srs}\n")
        file.write(f";Retraction Speed Increment 	{irs}\n")
        file.write(f";Print Speed 					{ps}\n")
        file.write(f";Starting Temp 					{int(tsh)}\n")
        file.write(f";Increment Temp 				{int(tih)}\n")
        file.write(f";Bed Temp 						{int(tb)}\n")
        file.write(f";Fan Speed 						{int(fs)}\n")
        file.write(f";Fan Speed Increment 			{int(fsi)}\n")
        file.write(f";Nozzle Diameter 				{nd}\n")
        file.write(f";Layer Height 					{lh}\n")
        file.write(f";Filament Diameter 				{fd}\n")
        file.write(f";Extrusion Multiplier 			{em}\n")
        file.write(f";Layers Per Test                {lt}\n")
        file.write(f";Number of Tests                {nt}\n")
        file.write(f";\n")
        file.write(f";\n")


# Generate E Value  https://3dprinting.stackexchange.com/questions/10171/how-is-e-value-calculated-in-slic3r 

        def eValue ( extrusionLength ):

            diameterNozzle = float(ui.nozzleDiameter.text())
            heightLayer = float(ui.layerHeight.text())
            diameterFilament = float(ui.filamentDiameter.text())
            multiplierExtrusion = float(ui.extrusionMultiplier.text())

            area = (diameterNozzle - heightLayer) * heightLayer + 3.14159 * (heightLayer/2)**2
            eValueresult = (area * extrusionLength * 4)/(3.14159 * diameterFilament**2/multiplierExtrusion*1.25)
            return eValueresult


#start Gcode
        # Custom start gcode fully REPLACES the old hardcoded start block. The
        # user's Prusa XL start gcode is expected to home, run MBL, heat, prime,
        # and pick the tool itself. If no custom start gcode is provided, fall
        # back to a minimal single-tool start so the tool still works standalone.
        file.write(f";Start Gcode (custom, replaces default)\n")
        if sgcode.strip():
            file.write(fill(sgcode) + "\n")
        else:
            file.write(f"M140 S{int(tb)}\n")
            file.write(f"M190 S{int(tb)}\n")
            file.write(f"T{tool}\n")
            file.write(f"M104 S{int(tsh)}\n")
            file.write(f"M109 S{int(tsh)}\n")
            file.write(f"G28\n")

        # Normalise machine state for the tower regardless of what the custom
        # gcode left behind: select the chosen head, absolute XYZ, absolute
        # extrusion (the raft below relies on M82), reset the extruder origin.
        file.write(f"T{tool}\n")
        file.write(f"G90\n")
        file.write(f"M82\n")
        file.write(f"G92 E0\n")

        file.write(f";\n")
        file.write(f";\n")

        xpos = dx/2-30
        ypos = dy/2-30
        zpos = lh
        epos = 0
    


#Start Movement        
        file.write(f";Start Movement\n")
        file.write(f";\n")
        file.write(f"G1 Z2\n")
        file.write(f"G1 F{int(ts)*60} X{xpos} Y{ypos} Z{zpos}\n")
        file.write(f";\n")
        eValueresult = eValue(60)

#Overextruding Raft
        evalueincrease = eValueresult*1.25
        eValueresult = evalueincrease


        remx = xpos
        remy = ypos

        file.write(f";Layer 1\n")

    #Horizontal

        for loopx in range(30):
            file.write(f"G1 F{int(ps*60/2)} X{xpos+60} Y{ypos} E{round(Decimal(eValueresult),5)}\n")
            xpos = xpos + 60
            eValueresult = eValueresult + evalueincrease
            file.write(f"G0 F{int(ts)*60} X{xpos} Y{ypos+1}\n")
            ypos = ypos + 1
            file.write(f"G1 F{int(ps*60/2)} X{xpos-60} Y{ypos} E{round(Decimal(eValueresult),5)}\n")
            xpos = xpos - 60
            eValueresult = eValueresult + evalueincrease
            file.write(f"G0 F{int(ts)*60} X{xpos} Y{ypos+1}\n")
            ypos = ypos + 1

    #Bring back to raft origin

        file.write(f"G0 F{int(ts)*60} X{xpos} Y{ypos} Z{round(Decimal(lh*3),2)}\n")
        file.write(f"G0 F{int(ts)*60} X{remx} Y{remy} Z{lh+lh}\n")
        xpos = remx
        ypos = remy

        file.write(f";Layer 2\n")

    #Vertical

        for loopx in range(30):
            file.write(f"G1 F{int(ps*60/2)} X{xpos} Y{ypos+60} E{round(Decimal(eValueresult),5)}\n")
            ypos = ypos + 60
            eValueresult = eValueresult + evalueincrease
            file.write(f"G0 F{int(ts)*60} X{xpos+1} Y{ypos}\n")
            xpos = xpos + 1
            file.write(f"G1 F{int(ps*60/2)} X{xpos} Y{ypos-60} E{round(Decimal(eValueresult),5)}\n")
            ypos = ypos - 60
            eValueresult = eValueresult + evalueincrease
            file.write(f"G0 F{int(ts)*60} X{xpos+1} Y{ypos}\n")
            xpos = xpos + 1    

    #Bring back to Calibration Starting Position

        file.write(f"G0 F{int(ts)*60} X{remx+5} Y{remy+5} Z{round(Decimal(lh*3),2)}\n")

    #Relative Movements

        file.write(f"M83\n")
        file.write(f"G91\n")

    #Start Calibration

        eValueresult = eValue(10)
        corenermarker = eValue(1)

        loopbigcount = 0
        loopsmallcount = 0

        layer = 3

        cnt = int(nt)
        lt = lt - 1

        for loopbig in range(int(cnt)):

    #set Fan every 15 layers
            file.write(f"M106 S{(round(Decimal((fs+fsi*loopbigcount)) * 255 / 100,0))  }\n")
            file.write(f"M104 S{round(Decimal(tsh+tih*loopbigcount),0)}\n")

            file.write(f";Layer {layer}\n")

            #Layer Marker Bottom Left
            file.write(f"G1 F{int(ps*60)} X-2 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y-2 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} X2 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y2 E{round(Decimal(corenermarker),5)}\n")


            #Begin 

            #Bottom
            file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*0),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*0),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*1),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*1),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*2),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*2),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*3),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*3),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")

            #Layer Marker Bottom Right
            file.write(f"G1 F{int(ps*60)} X1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y-1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} X-1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y1 E{round(Decimal(corenermarker),5)}\n")

            #Right
            file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*4),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*4),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*5),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*5),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*6),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*6),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*7),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*7),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")

            #Layer Marker Top Right
            file.write(f"G1 F{int(ps*60)} X1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} X-1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y-1 E{round(Decimal(corenermarker),5)}\n")

            #Top
            file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*8),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*8),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*9),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*9),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*10),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*10),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*11),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} Y10\n")
            file.write(f"G0 F{int(ts)*60} Y-10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*11),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")

            #Layer Marker Top Left
            file.write(f"G1 F{int(ps*60)} X-1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} X1 E{round(Decimal(corenermarker),5)}\n")
            file.write(f"G1 F{int(ps*60)} Y-1 E{round(Decimal(corenermarker),5)}\n")

            #Left
            file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*12),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*12),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*13),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*13),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*14),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*14),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
            file.write(f"G1 E{round(Decimal(srd+ird*15),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G0 F{int(ts)*60} X-10\n")
            file.write(f"G0 F{int(ts)*60} X10\n")
            file.write(f"G1 E{round(Decimal(srd+ird*15),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
            file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")

            #Zup layer height

            file.write(f"G1 Z{lh}\n")
                 
#           loopbigcount = loopbigcount +1
            layer = layer + 1


            for loopsmall in range(int(lt)):

                file.write(f";Layer {layer}\n")
            #Bottom
                file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*0),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*0),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*1),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*1),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*2),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*2),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*3),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*3),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X10 E{round(Decimal(eValueresult),5)}\n")

            #Right
                file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*4),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*4),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*5),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*5),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*6),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*6),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*7),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*7),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y10 E{round(Decimal(eValueresult),5)}\n")

                #Top
                file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*8),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*8),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*9),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*9),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*10),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*10),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*11),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} Y10\n")
                file.write(f"G0 F{int(ts)*60} Y-10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*11),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} X-10 E{round(Decimal(eValueresult),5)}\n")

            #Left
                file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*12),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*12),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*13),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*13),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*14),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*14),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")
                file.write(f"G1 E{round(Decimal(srd+ird*15),2) * -1} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G0 F{int(ts)*60} X-10\n")
                file.write(f"G0 F{int(ts)*60} X10\n")
                file.write(f"G1 E{round(Decimal(srd+ird*15),2)} F{round(Decimal((srs+irs*loopbigcount) * 60),2)}\n")
                file.write(f"G1 F{int(ps*60)} Y-10 E{round(Decimal(eValueresult),5)}\n")

                file.write(f"G1 Z{lh}\n")
                layer = layer + 1

            loopbigcount = loopbigcount +1


    #End Game

    #Raise 5mm and switch back to absolute positioning before any end sequence
        file.write(f"G1 Z5\n")
        file.write(f"G90\n")

    # Custom end gcode fully REPLACES the default end sequence (e.g. Prusa XL
    # tool park). Falls back to a minimal safe shutdown if none is provided.
        if egcode.strip():
            file.write(fill(egcode) + "\n")
        else:
            file.write(f"M104 S0\n")   # hotend off
            file.write(f"M140 S0\n")   # bed off
            file.write(f"M107\n")      # fan off
            file.write(f"M84\n")       # steppers off




        file.close()

        # Surface the template-token warning in the GUI too (guarded so headless
        # / dialog-less runs never block).
        if unresolved:
            try:
                QtWidgets.QMessageBox.warning(
                    ui.centralwidget, "Unresolved start/end gcode",
                    "The start/end gcode still contains PrusaSlicer template tokens "
                    "(e.g. {if ...}, [first_layer_bed_temperature], {initial_tool}).\n\n"
                    "This is a slicer template, not printer-ready gcode, and will likely "
                    "FAIL on the printer.\n\nUse resolved machine gcode (copy the start "
                    "block from a sliced .gcode) or the {tool}/{hotend_temp}/{bed_temp} "
                    "placeholders.\n\nThe file was still saved, with the offending lines "
                    "flagged near the top.")
            except Exception:
                pass



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    add_prusa_controls(ui, MainWindow)
    ui.genGcode.clicked.connect(gengcode)
    MainWindow.show()
    sys.exit(app.exec_())
