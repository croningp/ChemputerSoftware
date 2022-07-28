# Command List for the Chemical Assembler (ChASM)
Command arguments for the Chemical Assembler "language".
Commands are of the format:
* {CMD} {ARGS}

All commands are capitalised and space separated.
See below for a full list of supported commands


## Pumps (CroninPumps)
**NOTE** The pump names are the names as defined in the XML definition of the platform.

* MOVE {src} {dest} {volume} {move_speed} {aspiration_speed} {dispense_speed}
  * {volume} can be a float or "all" in which case it moves the entire current volume
  * {move_speed} is the speed at which it moves material across the backbone. This argument is optional, if absent, it defaults to 50mL/min
  * {aspiration_speed} is the speed at which it aspirates from the source. This argument is optional, if absent, it defaults to {move_speed}. It will only be parsed as {aspiration_speed} if a move speed is given (argument is positional)
  * {dispense_speed} is the speed at which it aspirates from the source. This argument is optional, if absent, it defaults to {move_speed}. It will only be parsed as {aspiration_speed} if a move speed and aspiration speed is given (argument is positional)
* HOME {pump_name}
* SEPARATE {lower_phase_target} {upper_phase_target}
* PRIME {}


## Stirrer Plate (IKARET)
**NOTE** The parameter {name} refers to the node the device is attached to (e.g. reactor_reactor)

* START_STIR {name}
* START_HEAT {name}
* STOP_STIR {name}
* STOP_STIR {name}
* SET_TEMP {name} {temp}
* SET_STIR_RPM {name} {rpm}
* STIRRER_WAIT_FOR_TEMP {name}


## Rotavap (IKARV10)
**NOTE** The parameter {name} refers to the node representing the top flask of the roti (e.g. rotavap)

* START_HEATER_BATH {name}
* STOP_HEATER_BATH {name}
* START_ROTATION {name}
* STOP_ROTATION {name}
* LIFT_ARM_UP {name}
* LIFT_ARM_DOWN {name}
* RESET_ROTAVAP {name}
* SET_BATH_TEMP {name} {temp}
* SET_ROTATION {name} {rotation}
* RV_WAIT_FOR_TEMP {name}
* SET_INTERVAL {name} {interval}
