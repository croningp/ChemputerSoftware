# coding=utf-8
# !/usr/bin/env python
"""
:mod:"constants" -- Global constants file for easy maintenance
===================================

.. module:: constants
   :platform: Windows
   :synopsis: Global constants file for easy maintenance.
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2018 The Cronin Group, University of Glasgow

This file contains all constants used in the Chempiler project,
such as dictionary keys, device types, and so forth. Keeping them
all in one file makes future maintenance a lot easier and avoids duplicates.

For style guide used see http://xkcd.com/1513/
"""

# dictionary keys (in alphabetical order)
ADDRESS = "IP_address"
ASSOCIATED_FLASK = "associated_flask"
CHILLER = "chiller"
CLASS = "class"
COLLECTION_FLASK = "chemputer_collection_flask"
COLUMN = "chemputer_column"
CURRENT_VOLUME = "current_volume"
DEST = "dest_position"
FILTER = "chemputer_filter"
FLASK = "chemputer_flask"
INPUT = "input"
IO = "io"
MAX_VOLUME = "max_volume"
MODEL = "model"
NAME = "name"
NEXT = "next"
OBJECT = "obj"
OUTPUT = "output"
PARENT_FLASK = "parent_flask"
PORT = "port"
PUMP = "chemputer_pump"
ROTAVAP = "chemputer_rotavap"
RV = "rv"
SEPARATOR = "chemputer_separator"
SERIAL = "serial_device"
SOURCE = "source_position"
STIRRER = "stirrer"
VACUUM = "vacuum_pump"
VALVE = "chemputer_valve"
VOLUME = "volume"
WASTE = "chemputer_waste"

# numerical constants (in alphabetical order)
BACKBONE_PORT = 4
COLLECTION_PORT = 0
COOLING_THRESHOLD = 0.5  # degrees
DEFAULT_PUMP_SPEED = 50  # mL/min
EMPTY = 0
EQUILIBRATION_TIME = 1  # s
OP_POS = 1
SEPARATION_DEAD_VOLUME = 2.5
SEPARATION_DEFAULT_DRAW_SPEED = 35  # mL/min
SEPARATION_DEFAULT_PRIMING_VOLUME = 2  # mL
STRAIGHT_THROUGH = 0
VACUUM_PORT = 5
WASTE_PORT = 3

# network settings
UDP_HOST = ("192.168.255.255", 3000)

# devices (for setup)
PUMPS = [
    "chemputer_pump"
]

VALVES = [
    "chemputer_valve"
]

STIRRERS = [
    "IKA_ret_visc",
    "RZR2052",
    "usb_switch",
    "microstar"
]

ROTAVAPS = [
    "IKA_RV10"
]

VACUUM_PUMPS = [
    "CVC3000"
]

CHILLERS = [
    "CF41",
    "Huber"
]

SPECIAL_DEVICES = {
    "chemputer_filter",
    "chemputer_separator",
    "chemputer_rotavap",
    "chemputer_column"
}

# ChASM commands
WAIT = ["WAIT"]

PUMP_CMDS = [
    "MOVE",
    "HOME",
    "SEPARATE",
    "PRIME",
    "CLEAN",
    "SWITCH_VACUUM",
    "SWITCH_CARTRIDGE",
    "SWITCH_COLUMN"
]

STIR_CMDS = [
    "START_STIR",
    "START_HEAT",
    "STOP_HEAT",
    "STOP_STIR",
    "SET_TEMP",
    "SET_STIR_RPM",
    "STIRRER_WAIT_FOR_TEMP"
]

ROTAVAP_CMDS = [
    "START_HEATER_BATH",
    "STOP_HEATER_BATH",
    "START_ROTATION",
    "STOP_ROTATION",
    "LIFT_ARM_UP",
    "LIFT_ARM_DOWN",
    "RESET_ROTAVAP",
    "SET_BATH_TEMP",
    "SET_ROTATION",
    "RV_WAIT_FOR_TEMP",
    "SET_INTERVAL"
]

VACUUM_CMDS = [
    "INIT_VAC_PUMP",
    "GET_VAC_SP",
    "SET_VAC_SP",
    "START_VAC",
    "STOP_VAC",
    "VENT_VAC",
    "GET_VAC_STATUS",
    "GET_END_VAC_SP",
    "SET_END_VAC_SP",
    "GET_RUNTIME_SP",
    "SET_RUNTIME_SP",
    "SET_SPEED_SP"
]

CHILLER_CMDS = [
    "START_CHILLER",
    "STOP_CHILLER",
    "SET_CHILLER",
    "CHILLER_WAIT_FOR_TEMP",
    "RAMP_CHILLER",
    "SWITCH_CHILLER"
]

CAMERA_CMDS = [
    "SET_RECORDING_SPEED"
]

BREAKPOINT_CMD = "BREAKPOINT"

# Device Flags
STIR_FLAG = "STIRRER"
ROTAVAP_FLAG = "ROTAVAP"
PUMP_FLAG = "PUMPS"
VALVE_FLAG = "VALVES"
VAC_FLAG = "VACUUM"
CHILLER_FLAG = "CHILLER"

# Misc
PARALLEL = "P"
SEQUENTIAL = "S"
