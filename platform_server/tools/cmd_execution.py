# coding=utf-8
# !/usr/bin/env python
"""
:mod:"cmd_execution" -- Command dispatcher and deep control layer for the Chemputer
===================================

.. module:: cmd_execution
   :platform: Windows, Unix
   :synopsis: Command dispatcher for the Chemputer.
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This module provides a class that takes possession of the physical resources via the various module executioners,
and carries out commands supplied as a list of "opcode" and arguments. This is the heart of the Chemputer control.

For style guide used see http://xkcd.com/1513/
"""

import threading
import math
import networkx as nx
import logging
import os
import sys
import inspect
import time

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

from tools.module_execution.pump_execution import PumpExecutioner
from tools.module_execution.stirrer_execution import StirrerExecutioner
from tools.module_execution.rotavap_execution import RotavapExecutioner
from tools.module_execution.vacuum_execution import VacuumExecutioner
from tools.module_execution.chiller_execution import ChillerExecutioner
from tools.module_execution.camera_execution import CameraExecutioner

from tools.constants import *


class Executioner(object):
    """
    Judge. Jury. Executioner.

    Args:
        graph (ChemOSGraph): Graph object representing the physical platform_server, populated with module objects
        simulation (bool): Whether or not this is a simulation
    """
    def __init__(self, graph, simulation=False):
        self.graph = graph
        self.simulation = simulation
        self.thread_pool = []
        self.logger = logging.getLogger("main_logger.executioner_logger")
        
        # Devices
        self.pumps = self.get_device_objects(PUMP_FLAG)
        self.valves = self.get_device_objects(VALVE_FLAG)
        self.rotavaps = self.get_device_objects(ROTAVAP_FLAG)
        self.stirrers = self.get_device_objects(STIR_FLAG)
        self.vacuum = self.get_device_objects(VAC_FLAG)
        self.chiller = self.get_device_objects(CHILLER_FLAG)

        # Executors
        self.pump_executor = PumpExecutioner(self.graph, self.pumps, self.valves, self.simulation)
        self.stirrer_executor = StirrerExecutioner(self.stirrers, self.simulation)
        self.rotavap_executor = RotavapExecutioner(self.rotavaps, self.simulation)
        self.vacuum_executor = VacuumExecutioner(self.vacuum, self.simulation)
        self.chiller_executor = ChillerExecutioner(self.graph, self.chiller, self.simulation)
        self.camera_executor = CameraExecutioner()

    def execute(self, cmd):
        """
        Executes the command, depending on the operation move that is passed

        Args:
            cmd (List): List of arguments for a command
        """
        if cmd[0] == SEQUENTIAL:
            self.join_parallel_operations()

        if cmd[OP_POS] in PUMP_CMDS:
            self.process_pump_cmd(cmd)
        elif cmd[OP_POS] in STIR_CMDS:
            self.process_stirring_cmd(cmd)
        elif cmd[OP_POS] in WAIT:
            self.process_waiting_cmd(cmd)
        elif cmd[OP_POS] in ROTAVAP_CMDS:
            self.process_rotavap_cmd(cmd)
        elif cmd[OP_POS] in VACUUM_CMDS:
            self.process_vacuum_cmds(cmd)
        elif cmd[OP_POS] in CHILLER_CMDS:
            self.process_chiller_cmds(cmd)
        elif cmd[OP_POS] in CAMERA_CMDS:
            self.process_camera_cmds(cmd)
        elif cmd[OP_POS] == BREAKPOINT_CMD:
            if input("Breakpoint reached. Type \"off\" to stop the sequence. Press Enter to continue") == "off":
                sys.exit()
        else:
            print("Invalid command {0}".format(cmd))

    def join_parallel_operations(self):
        """
        Joins all parallel execution threads before processing a sequential command
        """
        if not self.thread_pool:
            return

        for thread in self.thread_pool:
            thread.join()
        self.thread_pool = []
    
    def process_pump_cmd(self, cmd):
        """
        Processes a command that involves the pumps/valves
        Commands are [MOVE, HOME]

        Args:
            cmd (List): Command arguments
        """
        cmd_type = cmd[0]
        for op in PUMP_CMDS:
            if cmd[OP_POS] == op:
                if op == "MOVE":
                    source = cmd[2]
                    dest = cmd[3]
                    volume = cmd[4]
                    # move all case
                    if volume == "all":
                        volume = self.graph.node[source][CURRENT_VOLUME]
                    else:
                        volume = float(volume)
                    # I know this is somewhat clumsy, but until I come up with a cleverer idea it'll have to do
                    try:
                        move_speed = float(cmd[5])
                    except IndexError:
                        move_speed = DEFAULT_PUMP_SPEED
                    try:
                        aspiration_speed = float(cmd[6])
                    except IndexError:
                        aspiration_speed = move_speed
                    try:
                        dispense_speed = float(cmd[7])
                    except IndexError:
                        dispense_speed = move_speed
                    if source == dest:  # if the source and destination are the same
                        associated_valve = self.graph.predecessors(source)[0]  # this relies on the fact that a flask only has one predecessor
                        path = [source, associated_valve, dest]
                    else:
                        # self.graph is directed, so there are no direct paths between the flasks.
                        # To remedy that, nx.Graph(self.graph) returns a shallow copy in the form of an undirected graph.
                        # Hopefully this does not create too many issues.
                        try:
                            path = nx.shortest_path(nx.Graph(self.graph), source, dest)
                        except Exception:
                            self.logger.exception("Encountered an error during MOVE command.")
                            return

                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.move(path, volume, move_speed, aspiration_speed, dispense_speed)
                    elif cmd_type == PARALLEL:
                        move_thread = threading.Thread(target=self.pump_executor.move, args=(path, volume, move_speed, aspiration_speed, dispense_speed,))
                        self.thread_pool.append(move_thread)
                        move_thread.start()
                    break

                elif op == "HOME":
                    pump_name = cmd[2]
                    move_speed = cmd[3]
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.home(pump_name, move_speed)
                    elif cmd_type == PARALLEL:
                        home_thread = threading.Thread(target=self.pump_executor.move, args=(pump_name, move_speed,))
                        self.thread_pool.append(home_thread)
                        home_thread.start()
                    break

                elif op == "SEPARATE":
                    lower_phase_target = cmd[2]
                    upper_phase_target = cmd[3]
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.separate_phases(lower_phase_target, upper_phase_target)
                    elif cmd_type == PARALLEL:
                        separate_thread = threading.Thread(target=self.pump_executor.separate_phases, args=(lower_phase_target, upper_phase_target,))
                        self.thread_pool.append(separate_thread)
                        separate_thread.start()
                    break

                elif op == "PRIME":
                    aspiration_speed = cmd[2]
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.prime_tubes(aspiration_speed)
                    elif cmd_type == PARALLEL:
                        prime_thread = threading.Thread(target=self.pump_executor.prime_tubes, args=(aspiration_speed,))
                        self.thread_pool.append(prime_thread)
                        prime_thread.start()
                    break

                elif op == "CLEAN":
                    source = cmd[2]
                    volume = float(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.clean_all(source=source, volume=volume)
                    elif cmd_type == PARALLEL:
                        clean_thread = threading.Thread(target=self.pump_executor.clean_all, args=(source, volume,))
                        self.thread_pool.append(clean_thread)
                        clean_thread.start()
                    break

                elif op == "SWITCH_VACUUM":
                    flask = cmd[2]
                    destination = cmd[3]
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.switch_vacuum(flask, destination)
                    elif cmd_type == PARALLEL:
                        vacvalve_thread = threading.Thread(target=self.pump_executor.switch_vacuum, args=(flask, destination,))
                        self.thread_pool.append(vacvalve_thread)
                        vacvalve_thread.start()
                    break

                elif op == "SWITCH_CARTRIDGE":
                    flask = cmd[2]
                    cartridge = cmd[3]
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.switch_cartridge(flask, cartridge)
                    elif cmd_type == PARALLEL:
                        cartridge_thread = threading.Thread(target=self.pump_executor.switch_cartridge, args=(flask, cartridge,))
                        self.thread_pool.append(cartridge_thread)
                        cartridge_thread.start()
                    break

                elif op == "SWITCH_COLUMN":
                    column = cmd[2]
                    destination = cmd[3]
                    if cmd_type == SEQUENTIAL:
                        self.pump_executor.switch_column_fraction(column, destination)
                    elif cmd_type == PARALLEL:
                        column_thread = threading.Thread(target=self.pump_executor.switch_column_fraction, args=(column, destination,))
                        self.thread_pool.append(column_thread)
                        column_thread.start()
                    break

    def process_stirring_cmd(self, cmd):
        """
        Processes a command involving the stirrer plates
        Commands are [STIR, HEAT, SET_TEMP, SET_STIR_RPM]

        Args:
            cmd (List): Command arguments
        """
        cmd_type = cmd[0]
        stirrer_name = cmd[2]

        for op in STIR_CMDS:
            if cmd[OP_POS] == op:
                if op == "START_STIR":
                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.stir(stirrer_name)
                    elif cmd_type == PARALLEL:
                        stir_thread = threading.Thread(target=self.stirrer_executor.stir, args=(stirrer_name,))
                        self.thread_pool.append(stir_thread)
                        stir_thread.start()
                    break
                elif op == "START_HEAT":
                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.heat(stirrer_name)
                    elif cmd_type == PARALLEL:
                        heat_thread = threading.Thread(target=self.stirrer_executor.heat, args=(stirrer_name,))
                        self.thread_pool.append(heat_thread)
                        heat_thread.start()
                    break
                elif op == "STOP_STIR":
                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.stop_stir(stirrer_name)
                    elif cmd_type == PARALLEL:
                        stir_thread = threading.Thread(target=self.stirrer_executor.stop_stir, args=(stirrer_name,))
                        self.thread_pool.append(stir_thread)
                        stir_thread.start()
                    break
                elif op == "STOP_HEAT":
                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.stop_heat(stirrer_name)
                    elif cmd_type == PARALLEL:
                        stir_thread = threading.Thread(target=self.stirrer_executor.stop_heat, args=(stirrer_name,))
                        self.thread_pool.append(stir_thread)
                        stir_thread.start()
                    break
                elif op == "SET_TEMP":
                    temp = float(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.set_temp(stirrer_name, temp)
                    elif cmd_type == PARALLEL:
                        set_temp_thread = threading.Thread(target=self.stirrer_executor.set_temp, args=(stirrer_name, temp,))
                        self.thread_pool.append(set_temp_thread)
                        set_temp_thread.start()
                    break
                elif op == "SET_STIR_RPM":
                    stir_rate = int(cmd[3])

                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.set_stir_rate(stirrer_name, stir_rate)
                    elif cmd_type == PARALLEL:
                        set_stir_thread = threading.Thread(target=self.stirrer_executor.set_stir_rate, args=(stirrer_name, stir_rate,))
                        self.thread_pool.append(set_stir_thread)
                        set_stir_thread.start()
                    break
                elif op == "STIRRER_WAIT_FOR_TEMP":
                    if cmd_type == SEQUENTIAL:
                        self.stirrer_executor.wait_for_temp(stirrer_name)
                    elif cmd_type == PARALLEL:
                        stirrer_wait_thread = threading.Thread(target=self.stirrer_executor.wait_for_temp, args=(stirrer_name,))
                        self.thread_pool.append(stirrer_wait_thread)
                        stirrer_wait_thread.start()
                    break

    def process_rotavap_cmd(self, cmd):
        """
        Processes a command involving the rotavap

        Commands are [START_HEATER, STOP_HEATER, START_ROTATION, STOP_ROTATION, LIFT_UP, LIFT_DOWN, RESET, SET_BATH_TEMP, SET_ROTATION]

        Args:
            cmd (List): Command arguments
        """
        cmd_type = cmd[0]
        rotavap = cmd[2]

        for op in ROTAVAP_CMDS:
            if cmd[OP_POS] in op:
                if op == "START_HEATER_BATH":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.start_heater(rotavap)
                    elif cmd_type == PARALLEL:
                        heater_thread = threading.Thread(target=self.rotavap_executor.start_heater, args=(rotavap,))
                        self.thread_pool.append(heater_thread)
                        heater_thread.start()
                    break
                elif op == "STOP_HEATER_BATH":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.stop_heater(rotavap)
                    elif cmd_type == PARALLEL:
                        heater_thread = threading.Thread(target=self.rotavap_executor.stop_heater, args=(rotavap,))
                        self.thread_pool.append(heater_thread)
                        heater_thread.start()
                    break
                elif op == "START_ROTATION":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.start_rotation(rotavap)
                    elif cmd_type == PARALLEL:
                        rot_thread = threading.Thread(target=self.rotavap_executor.start_rotation, args=(rotavap,))
                        self.thread_pool.append(rot_thread)
                        rot_thread.start()
                    break
                elif op == "STOP_ROTATION":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.stop_rotation(rotavap)
                    elif cmd_type == PARALLEL:
                        rot_thread = threading.Thread(target=self.rotavap_executor.stop_rotation, args=(rotavap,))
                        self.thread_pool.append(rot_thread)
                        rot_thread.start()
                    break
                elif op == "LIFT_ARM_UP":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.lift_up(rotavap)
                    elif cmd_type == PARALLEL:
                        lift_thread = threading.Thread(target=self.rotavap_executor.lift_up, args=(rotavap,))
                        self.thread_pool.append(lift_thread)
                        lift_thread.start()
                    break
                elif op == "LIFT_ARM_DOWN":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.lift_down(rotavap)
                    elif cmd_type == PARALLEL:
                        lift_thread = threading.Thread(target=self.rotavap_executor.lift_down, args=(rotavap,))
                        self.thread_pool.append(lift_thread)
                        lift_thread.start()
                    break
                elif op == "RESET_ROTAVAP":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.reset(rotavap)
                    elif cmd_type == PARALLEL:
                        reset_thread = threading.Thread(target=self.rotavap_executor.reset, args=(rotavap,))
                        self.thread_pool.append(reset_thread)
                        reset_thread.start()
                    break
                elif op == "SET_BATH_TEMP":
                    temp = float(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.set_temp(rotavap, temp)
                    elif cmd_type == PARALLEL:
                        temp_thread = threading.Thread(target=self.rotavap_executor.set_temp, args=(rotavap, temp,))
                        self.thread_pool.append(temp_thread)
                        temp_thread.start()
                    break
                elif op == "SET_ROTATION":
                    rot_speed = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.set_rotation(rotavap, rot_speed)
                    elif cmd_type == PARALLEL:
                        speed_thread = threading.Thread(target=self.rotavap_executor.set_rotation, args=(rotavap, rot_speed,))
                        self.thread_pool.append(speed_thread)
                        speed_thread.start()
                    break
                elif op == "RV_WAIT_FOR_TEMP":
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.wait_for_temp(rotavap)
                    elif cmd_type == PARALLEL:
                        temp_wait_thread = threading.Thread(target=self.rotavap_executor.wait_for_temp, args=(rotavap,))
                        self.thread_pool.append(temp_wait_thread)
                        temp_wait_thread.start()
                    break

                elif op == "SET_INTERVAL":
                    interval = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.rotavap_executor.set_interval(rotavap, interval)
                    elif cmd_type == PARALLEL:
                        interval_thread = threading.Thread(target=self.rotavap_executor.set_interval, args=(rotavap, interval,))
                        self.thread_pool.append(interval_thread)
                        interval_thread.start()
                    break

    def process_vacuum_cmds(self, cmd):
        """
        Processes a command involving the Vacuum pump

        Commands are: [INIT, GET_VAC_SP, SET_VAC_SP, START_VAC, STOP_VAC, VENT, GET_STATUS, GET_END_VAC_SP, SET_END_VAC_SP, GET_RUNTIME_SP, SET_RUNTIME_SP]

        Args:
            cmd (List): List of commands
        """
        cmd_type = cmd[0]
        vacuum = cmd[2]

        for op in VACUUM_CMDS:
            if cmd[OP_POS] in op:
                if op == "INIT_VAC_PUMP":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.initialise(vacuum)
                    elif cmd_type == PARALLEL:
                        init_thread = threading.Thread(target=self.vacuum_executor.initialise, args=(vacuum,))
                        self.thread_pool.append(init_thread)
                        init_thread.start()
                    break
                elif op == "GET_VAC_SP":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.get_vacuum_set_point(vacuum)
                    elif cmd_type == PARALLEL:
                        vac_thread = threading.Thread(target=self.vacuum_executor.get_vacuum_set_point, args=(vacuum,))
                        self.thread_pool.append(vac_thread)
                        vac_thread.start()
                    break
                elif op == "SET_VAC_SP":
                    set_val = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.set_vacuum_set_point(vacuum, set_val)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.vacuum_executor.set_vacuum_set_point, args=(vacuum, set_val,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                elif op == "START_VAC":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.start_vacuum(vacuum)
                    elif cmd_type == PARALLEL:
                        start_thread = threading.Thread(target=self.vacuum_executor.start_vacuum, args=(vacuum,))
                        self.thread_pool.append(start_thread)
                        start_thread.start()
                    break
                elif op == "STOP_VAC":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.stop_vacuum(vacuum)
                    elif cmd_type == PARALLEL:
                        stop_thread = threading.Thread(target=self.vacuum_executor.stop_vacuum, args=(vacuum,))
                        self.thread_pool.append(stop_thread)
                        stop_thread.start()
                    break
                elif op == "VENT_VAC":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.vent_vacuum(vacuum)
                    elif cmd_type == PARALLEL:
                        vent_thread = threading.Thread(target=self.vacuum_executor.vent_vacuum, args=(vacuum,))
                        self.thread_pool.append(vent_thread)
                        vent_thread.start()
                    break
                elif op == "GET_VAC_STATUS":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.get_status(vacuum)
                    elif cmd_type == PARALLEL:
                        status_thread = threading.Thread(target=self.vacuum_executor.get_status, args=(vacuum,))
                        self.thread_pool.append(status_thread)
                        status_thread.start()
                    break
                elif op == "GET_END_VAC_SP":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.get_end_vacuum_set_point(vacuum)
                    elif cmd_type == PARALLEL:
                        get_thread = threading.Thread(target=self.vacuum_executor.get_end_vacuum_set_point, args=(vacuum,))
                        self.thread_pool.append(get_thread)
                        get_thread.start()
                    break
                elif op == "SET_END_VAC_SP":
                    set_val = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.set_end_vacuum_set_point(vacuum, set_val)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.vacuum_executor.set_end_vacuum_set_point, args=(vacuum, set_val,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                elif op == "GET_RUNTIME_SP":
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.get_runtime_set_point(vacuum)
                    elif cmd_type == PARALLEL:
                        get_thread = threading.Thread(target=self.vacuum_executor.get_runtime_set_point, args=(vacuum,))
                        self.thread_pool.append(get_thread)
                        get_thread.start()
                    break
                elif op == "SET_RUNTIME_SP":
                    set_val = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.set_runtime_set_point(vacuum, set_val)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.vacuum_executor.set_runtime_set_point, args=(vacuum, set_val,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                elif op == "SET_SPEED_SP":
                    set_val = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.vacuum_executor.set_speed_set_point(vacuum, set_val)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.vacuum_executor.set_speed_set_point, args=(vacuum, set_val,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                    
    def process_chiller_cmds(self, cmd):
        """
        Processes a command involving the recirculation chiller

        Commands are: [START_CHILLER, STOP_CHILLER, SET_CHILLER, RAMP_CHILLER]

        Args:
            cmd (List): List of commands
        """
        cmd_type = cmd[0]
        chiller = cmd[2]

        for op in CHILLER_CMDS:
            if cmd[OP_POS] in op:
                if op == "START_CHILLER":
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.start_chiller(chiller)
                    elif cmd_type == PARALLEL:
                        init_thread = threading.Thread(target=self.chiller_executor.start_chiller, args=(chiller,))
                        self.thread_pool.append(init_thread)
                        init_thread.start()
                    break
                elif op == "STOP_CHILLER":
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.stop_chiller(chiller)
                    elif cmd_type == PARALLEL:
                        vac_thread = threading.Thread(target=self.chiller_executor.stop_chiller, args=(chiller,))
                        self.thread_pool.append(vac_thread)
                        vac_thread.start()
                    break
                elif op == "SET_CHILLER":
                    set_val = float(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.set_temp(chiller, set_val)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.chiller_executor.set_temp, args=(chiller, set_val,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                elif op == "CHILLER_WAIT_FOR_TEMP":
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.wait_for_temp(chiller)
                    elif cmd_type == PARALLEL:
                        chiller_wait_thread = threading.Thread(target=self.chiller_executor.wait_for_temp, args=(chiller,))
                        self.thread_pool.append(chiller_wait_thread)
                        chiller_wait_thread.start()
                    break
                elif op == "RAMP_CHILLER":
                    ramp_duration = int(cmd[3])
                    temp = float(cmd[4])
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.ramp_chiller(chiller, ramp_duration, temp)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.chiller_executor.ramp_chiller, args=(chiller, ramp_duration, temp,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                elif op == "SWITCH_CHILLER":
                    state = cmd[3]
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.switch_vessel(chiller, state)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.chiller_executor.switch_vessel, args=(chiller, state,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break
                elif op == "SET_COOLING_POWER":
                    cooling_power = int(cmd[3])
                    if cmd_type == SEQUENTIAL:
                        self.chiller_executor.cooling_power(chiller, cooling_power)
                    elif cmd_type == PARALLEL:
                        set_thread = threading.Thread(target=self.chiller_executor.cooling_power, args=(chiller, cooling_power,))
                        self.thread_pool.append(set_thread)
                        set_thread.start()
                    break

    def process_camera_cmds(self, cmd):
        """
        Processes a command involving the camera

        Commands are: [SET_RECORDING_SPEED]

        Args:
            cmd (List): List of commands
        """
        for op in CAMERA_CMDS:
            if cmd[OP_POS] in op:
                if op == "SET_RECORDING_SPEED":
                    recording_speed = cmd[2]
                    try:
                        recording_speed = int(recording_speed)
                    except TypeError:
                        self.logger.exception("ERROR! Recording speed {0} is not supported!".format(recording_speed))
                    self.camera_executor.change_recording_speed(recording_speed)

    def process_waiting_cmd(self, cmd):
        """
        Processes a command for waiting on the platform_server

        Args:
            cmd (List): Command arguments
        """
        if len(cmd) > 3:
            raise Exception("Too many arguments for wait command")
        self.logger.info("Waiting for {0} seconds...".format(cmd[-1:][0]))
        if cmd[0] == SEQUENTIAL:
            self.wait_with_feedback(int(cmd[-1:][0]))
            self.logger.info("Waiting done.")
        elif cmd[0] == PARALLEL:
            wait_thread = threading.Thread(target=self.wait_with_feedback, args=(int(cmd[-1:][0]),))
            self.thread_pool.append(wait_thread)
            wait_thread.start()

    def get_device_objects(self, flag):
        """
        Goes through the graph, grabbing the objects that held in the nodes depending on the passed flag

        Args:
            flag (str): Flag identifying what objects to retrieve (Pumps, Valves, Stirrer, Rotavap, etc.)

        Returns:
            device_dict (Dict): Dictionary containing the name of the device and its associated object

        Raises:
            Exception: No objects found
        """
        device_dict = {}

        # Gets the pumps
        if flag == PUMP_FLAG:
            for each_node in self.graph.nodes():
                if self.graph.node[each_node][CLASS] == PUMP:
                    pump_object = self.graph.node[each_node][OBJECT]
                    device_dict[pump_object.name] = pump_object

            return device_dict

        # Gets the valves
        if flag == VALVE_FLAG:
            for each_node in self.graph.nodes():
                if self.graph.node[each_node][CLASS] == VALVE:
                    valve_object = self.graph.node[each_node][OBJECT]
                    device_dict[valve_object.name] = valve_object

            return device_dict

        # Gets the rotavap
        if flag == ROTAVAP_FLAG:
            for each_node in self.graph.nodes():
                for key, value in self.graph.node[each_node].items():
                    if key in ROTAVAPS:
                        device_dict[each_node] = value  # TODO really need to add a name attribute to serial devices

            return device_dict

        # Gets the vacuum pump
        if flag == VAC_FLAG:
            for each_node in self.graph.nodes():
                for key, value in self.graph.node[each_node].items():
                    if key in VACUUM_PUMPS:
                        device_dict[each_node] = value

            return device_dict

        # Gets the stirrer plates
        if flag == STIR_FLAG:
            for each_node in self.graph.nodes():
                for key, value in self.graph.node[each_node].items():
                    if key in STIRRERS:
                        device_dict[each_node] = value

            return device_dict

        # Gets the chillers
        if flag == CHILLER_FLAG:
            for each_node in self.graph.nodes():
                for key, value in self.graph.node[each_node].items():
                    if key in CHILLERS:
                        device_dict[each_node] = value

            return device_dict
        
        raise Exception("No objects of the desired type could be found.")

    def wait_with_feedback(self, wait_time):
        """
        Waits for a desired time and prints the wait progress.

        Args:
            wait_time (int): Time to wait in seconds
        """
        if self.simulation:
            self.logger.info("WAIT - Waiting for {0}".format(wait_time))

        else:
            start_time = time.time()
            end_time = start_time + wait_time
            end_time = time.localtime(end_time)
            end_time_pretty_print = time.strftime("%Y-%m-%d %H:%M:%S", end_time)
            self.logger.info("Waiting will be done at approximately {1}".format(wait_time, end_time_pretty_print))
            percent_done = 0
            while round(time.time() - start_time) < wait_time:
                if math.floor(100 * (time.time() - start_time) / wait_time) > percent_done:
                    percent_done = math.floor(100 * (time.time() - start_time) / wait_time)
                    self.logger.info(
                        "Waiting to {0}% done. Approximately {1} h, {2} min, {3} sec remaining.".format(
                            percent_done,
                            str(math.floor((start_time + wait_time - time.time()) / 3600)),
                            str(math.floor((start_time + wait_time - time.time() - (
                                math.floor((start_time + wait_time - time.time()) / 3600) * 3600)) / 60)),
                            str(
                                round(
                                    start_time + wait_time - time.time() - (
                                        (math.floor((start_time + wait_time - time.time() - (
                                            math.floor((start_time + wait_time - time.time()) / 3600) * 3600)) / 60) * 60) +
                                        (math.floor((start_time + wait_time - time.time()) / 3600) * 3600)
                                    )
                                )
                            )
                        )
                    )
