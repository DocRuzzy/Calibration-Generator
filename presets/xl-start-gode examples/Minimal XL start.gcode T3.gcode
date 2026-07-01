M201 X7000 Y7000 Z200 E2500 ; sets maximum accelerations, mm/sec^2
M203 X400 Y400 Z12 E100 ; sets maximum feedrates, mm / sec
M204 P4000 R1200 T5000 ; sets acceleration (P, T) and retract acceleration (R), mm/sec^2
M205 X8.00 Y8.00 Z2.00 E10.00 ; sets the jerk limits, mm/sec
M205 S0 T3 ; sets the minimum extruding and travel feed rate, mm/sec
;TYPE:Custom

M17 ; enable steppers
G90 ; use absolute coordinates
M83 ; extruder relative mode
; inform about nozzle diameter
M862.1 T3 P0.25

; turn off unused heaters
 M104 T0 S0 
 M104 T1 S0 
 M104 T2 S0 
 M104 T4 S0 

; Home XY
G28 XY
; try picking tools used in print
G1 F3000
; select tool that will be used to home & MBL
T3 S1 L0 D0
G28 Z
G0 Z5 F480 ; move away in Z
M107 ; turn off the fan
M84 E ; turn off E motor

M104 T3 S215

G92 E0 ; reset extruder position
G21 ; set units to millimeters
G90 ; use absolute coordinates
M82 ; use absolute distances for extrusion

G1 F3000
T3 S1 L0 D0
M109 S215 T3 ; set temperature and wait for it to be reached