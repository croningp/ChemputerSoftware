# coding=utf-8
# !/usr/bin/env python
"""
:mod:"pump_execution" -- Mid-level wrapper class around :mod:"Chemputer_Device_API"
===================================

.. module:: pump_execution
   :platform: Windows, Unix
   :synopsis: Mid-level wrapper around pump and valve control, provides real-live useful methods
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This class provides all real-life applications of pumps and valves within the Chemputer rig, most notably
the path finding algorithm and the moving of material based on that. It also has some compound operations like
phase separation that are needed to operate the Chemputer rig.

For style guide used see http://xkcd.com/1513/
"""

import inspect
import logging
import os
import sys
from time import sleep

import networkx as nx

# To get references to Chemputer pump and valve objects
HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, "..', '.."))

from modules.pv_api.Chemputer_Device_API import ChemputerPump, ChemputerValve
from sims.hardware_sim import SimChemputerPump, SimChemputerValve
from tools.constants import *


class PumpExecutioner(object):

    """
    Executes the Pump movements around the platform_server
    .. note:: Ignore the style faux pas of the simulation statements on a single line, it's better than taking up two
        lines for something that will rarely be used!
    """
    def __init__(self, graph, pumps, valves, simulation):
        """
        Initialiser for the PumpExecutioner class.
        :param DiGraph graph: Graph representing the platform
        :param dict pumps: Dictionary contianing the pump names and their related objects
        :param dict valves: Dictionary containing the valve namaes and their related objects
        :param bool simulation: Whether or not this is a simulation
        """
        self.graph = graph  # For determining the correct pumps attached to the valves
        self.pumps = pumps
        self.valves = valves
        self.simulation = simulation
        self.logger = logging.getLogger("main_logger.pump_executioner_logger")

    def get_current_node_volume(self, node):
        """
        Checks whether the node in question is a special device (filter, separator, rotavap, ...). If so, returns volume
        of the associated flask, else returns node volume. I realise this helper is written in a verbose way, but this
        is done on purpose for future proofing (maybe there will be other cases that are not as straightforward as the
        ones currently implemented!).

        Args:
            node: (str) Name of the node to check

        Returns:
            current_node_volume: (float) Current volume of the node.
        """
        if self.graph.node[node][CLASS] == FILTER:
            associated_flask = self.graph.node[node][ASSOCIATED_FLASK]
            current_node_volume = self.graph.node[associated_flask][CURRENT_VOLUME]
        elif self.graph.node[node][CLASS] == SEPARATOR:
            associated_flask = self.graph.node[node][ASSOCIATED_FLASK]
            current_node_volume = self.graph.node[associated_flask][CURRENT_VOLUME]
        elif self.graph.node[node][CLASS] == ROTAVAP:
            associated_flask = self.graph.node[node][ASSOCIATED_FLASK]
            current_node_volume = self.graph.node[associated_flask][CURRENT_VOLUME]
        else:
            current_node_volume = self.graph.node[node][CURRENT_VOLUME]

        return current_node_volume

    def get_maximum_node_volume(self, node):
        """
        Checks whether the node in question is a special device (filter, separator, rotavap, ...). If so, returns
        maximum volume of the associated flask, else returns node volume. I realise this helper is written in a verbose
        way, but this is done on purpose for future proofing (maybe there will be other cases that are not as
        straightforward as the ones currently implemented!).

        Args:
            node: (str) Name of the node to check

        Returns:
            maximum_node_volume: (float) Maximum volume of the node.
        """
        if self.graph.node[node][CLASS] == FILTER:
            associated_flask = self.graph.node[node][ASSOCIATED_FLASK]
            maximum_node_volume = self.graph.node[associated_flask][MAX_VOLUME]
        elif self.graph.node[node][CLASS] == SEPARATOR:
            associated_flask = self.graph.node[node][ASSOCIATED_FLASK]
            maximum_node_volume = self.graph.node[associated_flask][MAX_VOLUME]
        elif self.graph.node[node][CLASS] == ROTAVAP:
            associated_flask = self.graph.node[node][ASSOCIATED_FLASK]
            maximum_node_volume = self.graph.node[associated_flask][MAX_VOLUME]
        else:
            maximum_node_volume = self.graph.node[node][MAX_VOLUME]

        return maximum_node_volume

    def update_node_volumes(self, source, target, volume):
        """
        Checks whether either source or target node is a special device (filter, separator, rotavap, ...). If so,
        updates the volumes of the associated flask as appropriate. Else, updates the node directly.

        Args:
            source: (str) Name of the source node
            target: (str) Name of the target node
            volume: (float) Volume moved
        """
        # deal with source node first
        if (self.graph.node[source][CURRENT_VOLUME] - volume) < 0:  # can't be emptier than empty
            self.graph.node[source][CURRENT_VOLUME] = 0
        else:
            self.graph.node[source][CURRENT_VOLUME] -= volume

        if self.graph.node[source].get(PARENT_FLASK, None) is not None:  # if the source is a "bottom" of something
            parent_flask = self.graph.node[source][PARENT_FLASK]
            self.graph.node[parent_flask][CURRENT_VOLUME] = self.graph.node[source][CURRENT_VOLUME]

        elif self.graph.node[source].get(ASSOCIATED_FLASK, None) is not None:  # if the source is a "top" of something
            associated_flask = self.graph.node[source][ASSOCIATED_FLASK]
            self.graph.node[associated_flask][CURRENT_VOLUME] = self.graph.node[source][CURRENT_VOLUME]

        # then deal with target node
        self.graph.node[target][CURRENT_VOLUME] += volume
        if self.graph.node[target].get(PARENT_FLASK, None) is not None:  # if the target is a "bottom" of something
            parent_flask = self.graph.node[target][PARENT_FLASK]
            self.graph.node[parent_flask][CURRENT_VOLUME] += volume

        elif self.graph.node[target].get(ASSOCIATED_FLASK, None) is not None:  # if the target is a "top" of something
            associated_flask = self.graph.node[target][ASSOCIATED_FLASK]
            self.graph.node[associated_flask][CURRENT_VOLUME] += volume

    def is_valid_obj(self, flag, obj):
        """
        Determines if the the passed object is either a ChemputerPump or ChemputerValve, depending on the passed flag

        Args:
            flag (str): Type of object to check for
            obj (Object): Object to compare

        Returns:
            valid (bool): The object is of the expected type

        Raises:
            Exception: The object is not of the expected type
        """
        if self.simulation:
            if flag == PUMP:
                if isinstance(obj, SimChemputerPump):
                    return True
            elif flag == VALVE:
                if isinstance(obj, SimChemputerValve):
                    return True
            raise Exception("Object is not what it\'s supposed to be!\nOffending object: {0}\nExpected Type: {1}\n".format(obj, "Simulated Pump/Valve"))

        if flag == PUMP:
            if isinstance(obj, ChemputerPump):
                return True
        elif flag == VALVE:
            if isinstance(obj, ChemputerValve):
                return True
        raise Exception("Object is not what it\'s supposed to be!\nOffending Object: {0}\nExpected Type: {1}\n".format(obj, flag))

    def home(self, pump, speed):
        """
        Moves the target pump into the home position

        Args:
            pump (str): Name of the pump to home
            speed (int): Speed to move in milliliters per minute
        """
        pump_object = self.pumps[pump]
        pump_object.move_to_home(speed)

    def move(self, path, volume, move_speed, aspiration_speed=None, dispense_speed=None):
        """
        Performs the movement around the platform_server
        Uses either a single valve or multiple valves
        :param list path: List containing the path from the source to the destination and all valves in between
        :param float volume: Total volume to move in mL
        :param float move_speed: speed in mL/min for the moving along
        :param float aspiration_speed: speed in mL/min for the initial aspiration. Defaults to move_speed
        :param float dispense_speed: speed in mL/min for the final dispensing. Defaults to move_speed
        """
        # default speed settings
        if not aspiration_speed:
            aspiration_speed = move_speed
        if not dispense_speed:
            dispense_speed = move_speed

        # get source, destination and valves involved
        source = path[0]
        dest = path[len(path)-1]
        valves_in_path = path[1:-1]

        source_volume = self.get_current_node_volume(source)
        target_volume = self.get_current_node_volume(dest)
        target_max_volume = self.get_maximum_node_volume(dest)

        if volume > source_volume:
            self.logger.warning("Warning! MOVE instruction withdraws more ({0}mL) than the current volume ({1}mL)!".format(volume, source_volume))
        if volume > (target_max_volume - target_volume):
            self.logger.warning("Warning! MOVE instruction ({0}mL) overfills the target ({1}mL left)!".format(volume, (target_max_volume - target_volume)))

        self.logger.info("Moving {0}mL from {1} to {2} at {3}mL/min. Aspirating at {4}mL/min, dispensing at {5}mL/min.".format(volume, source, dest, move_speed, aspiration_speed, dispense_speed))

        # Debug for simulation
        if self.simulation: self.logger.debug("Following path: {0}".format(path))

        # Checks if it's all valves in the path
        for valve_name, valve_object in self.valves.items():
            if valve_name in valves_in_path:
                if self.is_valid_obj(VALVE, valve_object):
                    continue

        # actually move the pumps and valves
        if len(valves_in_path) == 0:
            raise Exception("Path length is 0, please check movement command!")
        elif len(valves_in_path) == 1:
            self.move_single_valve(valves_in_path[0], source, dest, volume, aspiration_speed, dispense_speed)
        else:
            self.move_multiple_valves(valves_in_path, source, dest, volume, aspiration_speed, move_speed, dispense_speed)

        self.update_node_volumes(source, dest, volume)

        self.logger.debug("New volumes are: {0}: {1}mL; {2}: {3}mL.".format(source, self.get_current_node_volume(source), dest, self.get_current_node_volume(dest)))
        
    def move_single_valve(self, valve, source, dest, volume, aspiration_speed, dispense_speed):
        """
        Performs the movement with a single valve
        This occurs when the path would be [source_flask, valve, destination_flask]

        Args:
            valve: (str) Name of the valve
            source: (str) Name of the source flask
            dest: (str) Name of the destination flask
            volume: (float) Volume to move in mL
            aspiration_speed: (float) Speed in mL/min for the initial aspiration
            dispense_speed: (float) Speed in mL/min for the final dispensing
        """
        target_valve = valve
        target_pump = None
        for each_node in self.graph.predecessors_iter(valve):
            if self.graph.node[each_node][CLASS] == PUMP:
                target_pump = each_node
                break

        valve_obj = self.valves[target_valve]
        if target_pump:
            pump_obj = self.pumps[target_pump]
        else:
            raise KeyError("No pump attached to valve!")

        try:
            source_position = self.graph.succ[valve][source][PORT]
            dest_position = self.graph.succ[valve][dest][PORT]
        except KeyError:
            raise KeyError("Unable to locate source/destination valve position")

        self.logger.debug("*** VOLUME TO MOVE: {0} ***".format(volume))
        while volume > EMPTY:
            valve_obj.move_to_position(source_position)
            valve_obj.wait_until_ready()

            if volume > self.graph.node[target_pump][MAX_VOLUME]:
                vol_to_pump = self.graph.node[target_pump][MAX_VOLUME]
            else:
                vol_to_pump = volume

            pump_obj.move_absolute(vol_to_pump, aspiration_speed)
            pump_obj.wait_until_ready()
            if not self.simulation: sleep(EQUILIBRATION_TIME)
            valve_obj.move_to_position(dest_position)
            valve_obj.wait_until_ready()
            pump_obj.move_absolute(EMPTY, dispense_speed)
            pump_obj.wait_until_ready()

            volume -= vol_to_pump
            if volume < 0:
                volume = 0
            self.logger.info("{0}mL left...".format(volume))
        self.logger.info("Done.")

    def move_multiple_valves(self, valves, source, dest, volume, aspiration_speed, move_speed, dispense_speed):
        """
        Performs the movement with multiple valves
        Occurs when the path has multiple connections E.g. [source_flask, valve1, valve2, valve2, destination_flask]

        Args:
            valves (list): Names of the valves
            source (str): Name of the source flask
            dest (str): Name of the destination flask
            volume (float): Volume to move in mL
            aspiration_speed (float): Speed in mL/min for the initial aspiration
            move_speed (float): Speed in mL/min for the moves across the backbone
            dispense_speed (float: Speed in mL/min for the final dispensing
        """
        if self.simulation: self.logger.debug("*** TOTAL VOLUME TO MOVE: {0} ***".format(volume))

        connection_dict = {}
        pumps = []
        minimal_pump_volume = None

        for i, valve in enumerate(valves):
            # set up the valve position ditionary
            connection_dict[valve] = {}
            for each_node in self.graph.successors_iter(valve):
                try:
                    if each_node == source:  # if the source flask is connected
                        connection_dict[valve][INPUT] = self.graph.succ[valve][source][PORT]
                    elif i != 0 and each_node == valves[i - 1]:  # else if the previous valve is connected
                        connection_dict[valve][INPUT] = self.graph.succ[valve][valves[i - 1]][PORT]
                except IndexError:
                    continue

                try:
                    if each_node == dest:  # if the destination flask is connected
                        connection_dict[valve][OUTPUT] = self.graph.succ[valve][dest][PORT]
                    elif each_node == valves[i + 1]:  # else if the next valve is connected
                        connection_dict[valve][OUTPUT] = self.graph.succ[valve][valves[i + 1]][PORT]
                except IndexError:
                    continue

            # figure out the list of pumps involved
            for each_node in self.graph.predecessors_iter(valve):
                if self.graph.node[each_node][CLASS] == PUMP:
                    pumps.append(each_node)
                    break

            # work out volume of the smallest syringe in the path
            for pump in pumps:
                if not minimal_pump_volume:  # for the first pump, just use the volume regardless
                    minimal_pump_volume = self.graph.node[pump][MAX_VOLUME]
                elif self.graph.node[pump][MAX_VOLUME] < minimal_pump_volume:  # for subsequent pumps, check if volume is smaller
                    minimal_pump_volume = self.graph.node[pump][MAX_VOLUME]

        i = 0  # loop iterator
        while True:
            # switch all the valves
            for j, valve in enumerate(valves):
                valve_object = self.graph.node[valve][OBJECT]
                if bool(i % 2) ^ bool(j % 2):  # that is, on odd loop iterations, even valves, and vice versa
                    position = connection_dict[valve][OUTPUT]  # switch to output
                else:
                    position = connection_dict[valve][INPUT]  # switch to input
                valve_object.move_to_position(position)

            for valve in valves:
                valve_object = self.graph.node[valve][OBJECT]
                valve_object.wait_until_ready()

            # move all the pumps
            # this is a bit complicated. I have to iterate over the pumps backwards, otherwise it accesses the volume of
            # the "previous" pump after the volume has been updated. Python offers the reversed() method, but that only
            # works on lists, not enumerator objects. So in order to "reverse enumerate" the reversed list, I do a
            # normal enumeration, and then inside the loop "flip" the index j with "j = len(pumps) - j - 1".
            for j, pump in enumerate(reversed(pumps)):
                j = len(pumps) - j - 1  # "flip" iterator
                pump_object = self.graph.node[pump][OBJECT]
                if j == 0 and not (i % 2):  # i.e. even loop iterations
                    # work out volume to pump
                    if volume > minimal_pump_volume:
                        volume_to_pump = minimal_pump_volume
                    else:
                        volume_to_pump = volume
                    volume -= volume_to_pump
                    if volume_to_pump != 0:
                        self.logger.info("{0}mL left...".format(volume))
                        pump_object.move_absolute(volume_to_pump, aspiration_speed)
                        self.graph.node[pump][CURRENT_VOLUME] = volume_to_pump  # update node
                elif j == 0 and (i % 2):  # i.e. odd loop iterations
                    # move to 0
                    if self.graph.node[pump][CURRENT_VOLUME] != 0:
                        pump_object.move_absolute(EMPTY, move_speed)
                        self.graph.node[pump][CURRENT_VOLUME] = 0  # update node
                elif bool(i % 2) ^ bool(j % 2):  # that is, on odd loop iterations, even pumps, and vice versa
                    # move to 0
                    if self.graph.node[pump][CURRENT_VOLUME] != 0:
                        if j + 1 == len(pumps):  # if it's the last pump
                            pump_object.move_absolute(EMPTY, dispense_speed)
                        else:
                            pump_object.move_absolute(EMPTY, move_speed)
                        self.graph.node[pump][CURRENT_VOLUME] = 0  # update node
                else:
                    # move to volume of pump j - 1
                    prev_volume = self.graph.node[pumps[j - 1]][CURRENT_VOLUME]
                    if prev_volume != 0:
                        pump_object.move_absolute(prev_volume, move_speed)
                        self.graph.node[pump][CURRENT_VOLUME] = prev_volume  # update node

            for pump in pumps:
                pump_object = self.graph.node[pump][OBJECT]
                pump_object.wait_until_ready()

            # figure out if we're done yet
            busy = False
            for pump in pumps:
                if self.graph.node[pump][CURRENT_VOLUME]:  # if even one pump is not empty, this goes to True
                    busy = True
            if volume:  # same idea, if volume remains, this goes to True
                busy = True
            if not busy:
                break

            i += 1  # increment loop iterator

        self.logger.info("Done.")

    def separate_phases(self, lower_phase_target, upper_phase_target, separator_top="flask_separator_top", separator_bottom="flask_separator_bottom", step_size=1, threshold=700):
        """
        Routine for separating layers in the automated sep funnel based on the conductivity sensor. Draws a known amount
        into the tube, measures response, then keeps removing portions until the response drops below the threshold.
        The implementation of the sensor is still insanely crude, basically an Arduino hack I shat together in a minute.
        Probably worthwhile changing at some point.

        Args:
            lower_phase_target (str): name of the flask the lower phase will be deposited to
            upper_phase_target (str): name of the flask the upper phase will be deposited to
            separator_top (str): name of the node which the sensor is associated with
            separator_bottom (str): name of the location the lower phase is to be withdrawn from
            step_size (float): size of the individual withdrawals in mL
            threshold (int): minimum sensor reading indicating aqueous phase
        """
        # acquire sensor
        try:
            sensor_connection = self.graph.node[separator_top]["conductivity_sensor"]
        except KeyError:
            self.logger.exception("Error. Separator top or sensor connection not found!")
            return

        # work out path
        self.logger.info("Starting separation")
        try:
            path = nx.shortest_path(nx.Graph(self.graph), separator_bottom, lower_phase_target)
        except Exception:
            self.logger.exception("Encountered an error during MOVE command.")
            return

        # prime sensor
        self.move(path=path, move_speed=SEPARATION_DEFAULT_DRAW_SPEED, volume=SEPARATION_DEFAULT_PRIMING_VOLUME)

        # start separation by repeatedly withdrawing some of the lower phase until the reading disappears
        while True:
            self.move(path=path, move_speed=SEPARATION_DEFAULT_DRAW_SPEED, volume=step_size)
            if self.simulation:
                self.logger.info("This is where the magic happens")
                break
            else:
                sensor_connection.write("Q".encode())
                reading = int(sensor_connection.readline().strip())
                self.logger.info("Sensor reading is {0}.".format(reading))
                if reading < threshold:
                    self.logger.info("Nope still the same phase.")
                else:
                    self.logger.info("Phase changed! Hurrah!")
                    break

        # transfer the upper layer to its destination
        if upper_phase_target == separator_top:  # i.e. keep the stuff
            self.logger.info("Done.")
        else:
            # withdraw separator dead volume
            self.logger.info("Now withdrawing dead volume...")
            self.move(path=path, move_speed=SEPARATION_DEFAULT_DRAW_SPEED, volume=SEPARATION_DEAD_VOLUME)

            self.logger.info("Done. Now transferring the upper layer...")
            try:
                path = nx.shortest_path(nx.Graph(self.graph), separator_bottom, upper_phase_target)
            except Exception:
                self.logger.exception("Encountered an error during MOVE command.")
                return
            volume = self.get_current_node_volume(separator_bottom)
            self.move(path=path, move_speed=SEPARATION_DEFAULT_DRAW_SPEED, volume=volume)
            self.logger.info("Done.")

    def prime_tubes(self, aspiration_speed):
        """
        Iterates over all nodes, and for all flasks moves the volume of the connecting tube from the flask to waste.
        Args:
            aspiration_speed (float): Speed at which to withdraw from each flask
        """
        for each_node in self.graph.node:
            if self.graph.node[each_node][CLASS] == FLASK:
                # find valve and tube volume
                try:
                    parent_valve = self.graph.predecessors(each_node)[0]
                    tube_volume = self.graph.pred[each_node][parent_valve][VOLUME]
                except KeyError:
                    self.logger.exception("Error! Can't find valve and tube volume for flask {0}".format(each_node))
                    raise
                # find waste position
                for successor in self.graph.succ[parent_valve].keys():
                    if self.graph.node[successor][CLASS] == WASTE:
                        associated_waste = successor
                        break
                # move volume to waste
                self.move(path=[each_node, parent_valve, associated_waste], volume=tube_volume, move_speed=DEFAULT_PUMP_SPEED, aspiration_speed=aspiration_speed)

    def clean_all(self, source, volume):
        """
        Iterates over all valves, and pumps a given volume from the source to each outlet.

        Args:
            source (str): flask from which the fluid should be withdrawn
            volume (float): volume to be transferred
        """
        for each_node in self.graph.node:
            if self.graph.node[each_node][CLASS] == VALVE:
                for successor in self.graph.succ[each_node].keys():
                    if successor != source and self.graph.node[successor][CLASS] != VALVE:
                        try:
                            path = nx.shortest_path(nx.Graph(self.graph), source, successor)
                        except Exception:
                            self.logger.exception("Encountered an error during MOVE command.")
                            return

                        self.move(path=path, volume=volume, move_speed=DEFAULT_PUMP_SPEED)

    def switch_vacuum(self, flask, destination):
        """
        Crude hack for switching a flask to vacuum via attached valve.

        Args:
            flask (str): flask which is to be evacuated
            destination (str): either "vacuum" or "backbone"
        """
        self.logger.info("Switching flask {0} to {1}...".format(flask, destination))
        vacuum_valve = self.graph.node[flask]["vacuum_valve"]
        if destination == "vacuum":
            vacuum_valve.move_to_position(VACUUM_PORT)
            vacuum_valve.wait_until_ready()
        elif destination == "backbone":
            vacuum_valve.move_to_position(BACKBONE_PORT)
            vacuum_valve.wait_until_ready()
        else:
            raise ValueError("ERROR! Supplied position \"{0}\" isn't recognised!".format(destination))
        self.logger.info("Done.")

    def switch_cartridge(self, flask, cartridge):
        """
        Crude hack to swicht a cartridge carousel consisting of two valves. Assumes identical ports are connected,
        i.e. port 0 to 0, 1 to 1 etc.

        Args:
            flask (str): node the carousel is connected to
            cartridge (int): number of the cartridge to switch to
        """
        self.logger.info("Switching cartridge carousel on {0} to cartridge {1}...".format(flask, cartridge))

        valve_one = self.graph.node[flask]["cartridge_carousel"][0]
        valve_two = self.graph.node[flask]["cartridge_carousel"][1]

        valve_one.move_to_position(cartridge)
        valve_one.wait_until_ready()
        valve_two.move_to_position(cartridge)
        valve_two.wait_until_ready()

        self.logger.info("Done.")

    def switch_column_fraction(self, column, destination):
        """
        Crude hack for switching the fractionating valve on the flash column.

        Args:
            column (str): column which is to be switched
            destination (str): either "collect" or "waste"
        """
        self.logger.info("Switching column {0} to {1}...".format(column, destination))
        column_valve = self.graph.node[column]["switching_valve"]

        # find valve and tube volume
        try:
            parent_valve = self.graph.predecessors(column)[0]
        except KeyError:
            self.logger.exception("Error! Can't find parent valve for {0}".format(column))
            raise

        # find waste position
        associated_waste = None
        associated_collection_flask = None

        for successor in self.graph.succ[parent_valve].keys():
            if self.graph.node[successor][CLASS] == WASTE:
                associated_waste = successor
            elif self.graph.node[successor][CLASS] == COLLECTION_FLASK:
                associated_collection_flask = successor
        if not (associated_waste and associated_collection_flask):
            raise KeyError("ERROR! Could not find waste position ({0}) or collect position ({1})!".format(associated_waste, associated_collection_flask))

        # switch the valve and update the graph
        if destination == "collect":
            column_valve.move_to_position(COLLECTION_PORT)
            column_valve.wait_until_ready()
            self.graph.node[column][ASSOCIATED_FLASK] = associated_collection_flask
        elif destination == "waste":
            column_valve.move_to_position(WASTE_PORT)
            column_valve.wait_until_ready()
            self.graph.node[column][ASSOCIATED_FLASK] = associated_waste
        else:
            raise ValueError("ERROR! Supplied position \"{0}\" isn't recognised!".format(destination))
        self.logger.info("Done.")
