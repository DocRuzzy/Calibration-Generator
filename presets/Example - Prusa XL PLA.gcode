; Example Prusa XL start gcode preset (PLA)
; -------------------------------------------------------------------------
; This file is loaded into the "Start Gcode (replaces default)" box when you
; pick it from the preset dropdown. It fully replaces the generator's default
; start block, so it must home, mesh-level, heat, prime and pick the tool.
;
; Placeholders substituted at generation time:
;   {tool}        -> selected head index (0..4), matches the "Active Tool" box
;   {hotend_temp} -> "Starting Temp" field
;   {bed_temp}    -> "Bed Temp" field
;
; NOTE: This is a minimal EXAMPLE. Replace it with your real, exported Prusa XL
; machine start gcode (e.g. from a PrusaSlicer-sliced .gcode file for the head
; you calibrate). Drop additional presets/*.gcode files here per head/material.
; -------------------------------------------------------------------------
M17                          ; enable steppers
M862.1 T{tool} P[0.4]        ; (informational) nozzle check for the selected tool
M104 T{tool} S{hotend_temp}  ; start heating the selected hotend
M140 S{bed_temp}             ; start heating the bed
T{tool} S1                   ; pick the selected tool
M190 S{bed_temp}             ; wait for bed
M109 T{tool} S{hotend_temp}  ; wait for the selected hotend
G28                          ; home all axes
G29                          ; mesh bed leveling
G90                          ; absolute XYZ
M83                          ; (Prusa default) relative extrusion
;
; Prime line near the front-left of the bed:
G1 Z5 F1200
G1 X10 Y10 F3000
G1 Z0.2 F720
G1 X100 E9 F1000            ; purge
G1 X120 E5 F1000            ; wipe
