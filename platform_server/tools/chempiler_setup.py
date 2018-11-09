# coding=utf-8
# !/usr/bin/env python
"""
:mod:"chempiler_setup" -- Setup and initialisation routines for the Chemputer
===================================

.. module:: chempiler_setup
   :platform: Windows, Unix
   :synopsis: Setup and initialisation routines for the Chemputer
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

Performs the initial setup of the Chempiler
Reads and sanitises a graph from a GraphML file.
This graph is populated with objects related to the platform e.g. Stirrer plates, pumps, etc

For style guide used see http://xkcd.com/1513/
"""

import inspect
import os
import sys
import time

import networkx as nx
import serial

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

""" Imports """
# Import all modules available
from modules.pv_api.Chemputer_Device_API import ChemputerPump, ChemputerValve, initialise_udp_keepalive
from modules.serial_labware.IKA_RV.IKA_RV10 import IKARV10  # That's a rotavap
from modules.serial_labware.Vacuubrand.Vacuubrand_CVC_3000 import CVC3000  # That's a pump
from modules.serial_labware.IKA_RET_Stirrer.IKA_RET_Control_Visc import IKARETControlVisc  # That's a stirrer plate
from modules.serial_labware.Heidolph_RZR_2052_control.Heidolph_RZR_2052_control import RZR_2052  # That's an overhead stirrer
from modules.serial_labware.IKA_microstar_75.IKA_microstar_75 import IKAmicrostar75  # That's a different overhead stirrer
from modules.serial_labware.JULABO_CF41.JULABO_CF41 import JULABOCF41  # That's a chiller
from modules.serial_labware.Huber_Petite_Fleur.Huber_Petite_Fleur import Huber  # That's a different chiller

# Import simulation classes
from sims.hardware_sim import *

# Import constants
from tools.constants import *


class Setup(object):
    """
    Performs the inital set up of the Chempiler rig
    Creates a graph object which maps the topology of the physical system

    Args:
        graphml_file (str): Absolute path to the graphml file to parse
        simulation (bool): Whether or not we're simulating hardware
    """
    def __init__(self, graphml_file, simulation=False):
        self.graph = self.load_graph(graphml_file)
        self.simulation = simulation

    def load_graph(self, file):
        """
        Loads a .graphml file containing the architecture, discards unnecessary information and relabels the nodes.

        :param file: GraphML file containing the architecture
        :return: sanitised graph object
        """
        graph = nx.read_graphml(file)
        mapping = {}
        for node in graph.nodes():
            label = graph.node[node].pop("label", "NaN")
            mapping[node] = label
        graph = nx.relabel_nodes(graph, mapping)
        for node in graph.nodes():
            graph.node[node].pop("x", None)
            graph.node[node].pop("y", None)

        return graph

    def setup_platform(self):
        """
        Performs the set up of the platform_server
        Populates the graph with instances of the relavent module objects

        Returns:
            graph (ChemOSGraph): Graph object populated with module objects
        """
        self.graph = self.setup_pumps_and_valves()
        time.sleep(0.1)  # To ensure that the graph has time to update itself
        self.graph = self.setup_serial_devices()
        time.sleep(0.1)  # To ensure that the graph has time to update itself
        self.graph = self.setup_special_devices()
        time.sleep(0.1)  # To ensure that the graph has time to update itself
        return self.graph

    def setup_pumps_and_valves(self):
        """
        Populates the graph with pump and valve objects and initialises them.
        Adapted from `chemputer_control.py` from the old ChemOS
        """
        initialise_udp_keepalive(UDP_HOST)
        time.sleep(0.1)

        pumps = []
        valves = []
        try:
            for each_node in self.graph.nodes():  # where each_node is a string containing the node name
                device_class = self.graph.node[each_node][CLASS]
                # name = self.graph.node[each_node][NAME]

                if device_class in PUMPS:
                    address = self.graph.node[each_node][ADDRESS]
                    if self.simulation:
                        device_object = SimChemputerPump(address=address, name=each_node)
                    else:
                        device_object = ChemputerPump(address=address, name=each_node)
                        pumps.append(device_object)
                    if OBJECT not in self.graph.node[each_node]:
                        self.graph.node[each_node][OBJECT] = device_object
                elif device_class in VALVES:
                    address = self.graph.node[each_node][ADDRESS]
                    if self.simulation:
                        device_object = SimChemputerValve(address=address, name=each_node)
                    else:
                        device_object = ChemputerValve(address=address, name=each_node)
                        valves.append(device_object)
                    if OBJECT not in self.graph.node[each_node]:
                        self.graph.node[each_node][OBJECT] = device_object

        except Exception as e:
            print('Pumps/Valves could not be instantiated!\nError: {0}'.format(e))

        if not self.simulation:
            # home all valves
            for valve in valves:
                valve.clear_errors()
                valve.move_home()
            for valve in valves:
                valve.wait_until_ready()

            for valve in valves:
                for successor, edge in self.graph.succ[valve.name].items():
                    if self.graph.node[successor][CLASS] == WASTE:
                        valve.move_to_position(edge[PORT])
                        break

            for valve in valves:
                valve.wait_until_ready()

            # hard home all pumps
            for pump in pumps:
                pump.clear_errors()
                pump.hard_home()
            for pump in pumps:
                pump.wait_until_ready()

        return self.graph

    def setup_serial_devices(self):
        """
        Grabs all serial devices from the graph and instantiates them.
        """
        # TODO: there must be a way to loop over the device types instead of explicitly coding every type individually

        # initialise dict of already instantiated devices
        found_devices = {
            "IKA_ret_visc": {},
            "RZR2052": {},
            "IKA_RV10": {},
            "CVC3000": {},
            "CF41": {},
            "Huber": {},
            "conductivity_sensor": {},
            "vacuum_valve": {},
            "cartridge_carousel": {},
            "microstar": {},
            "usb_switch": {},
            "chiller_switch": {},
            "switching_valve": {}
        }

        try:
            for each_node in self.graph.nodes():  # where each_node is a string containing the node name
                i = 1
                while True:
                    device_type = self.graph.node[each_node].pop("serial_device_{0}_type".format(i), None)
                    device_port = self.graph.node[each_node].pop("serial_device_{0}_port".format(i), None)

                    if not (device_type or device_port):
                        break

                    elif device_type == "IKA_ret_visc":
                        if found_devices["IKA_ret_visc"].get(device_port):
                            device_object = found_devices["IKA_ret_visc"][device_port]
                        elif self.simulation:
                            device_object = SimIKARET(port=device_port)
                            found_devices["IKA_ret_visc"][device_port] = device_object
                        else:
                            device_object = IKARETControlVisc(
                                port=device_port,
                                device_name="{0}_IKA_ret_visc".format(each_node),
                                connect_on_instantiation=True
                            )
                            found_devices["IKA_ret_visc"][device_port] = device_object
                        self.graph.node[each_node]["IKA_ret_visc"] = device_object  # TODO this is potentially troublesome as it precludes multiple serial devices of the same type on one node. I'm somewhat struggling to think of a case where that would be desirable but it's something to keep in mind

                    elif device_type == "RZR2052":
                        if found_devices["RZR2052"].get(device_port):
                            device_object = found_devices["RZR2052"][device_port]
                        elif self.simulation:
                            device_object = SimRZR2052(port=device_port)
                            found_devices["RZR2052"][device_port] = device_object
                        else:
                            device_object = RZR_2052(
                                port=device_port,
                                device_name="{0}_RZR2052".format(each_node),
                                connect_on_instantiation=True
                            )
                            found_devices["RZR2052"][device_port] = device_object
                        self.graph.node[each_node]["RZR2052"] = device_object

                    elif device_type == "microstar":
                        if found_devices["microstar"].get(device_port):
                            device_object = found_devices["microstar"][device_port]
                        elif self.simulation:
                            device_object = SimIKAmicrostar(port=device_port)
                            found_devices["microstar"][device_port] = device_object
                        else:
                            device_object = IKAmicrostar75(
                                port=device_port,
                                device_name="{0}_microstar".format(each_node),
                                connect_on_instantiation=True
                            )
                            found_devices["microstar"][device_port] = device_object
                        self.graph.node[each_node]["microstar"] = device_object

                    elif device_type == "IKA_RV10":
                        if found_devices["IKA_RV10"].get(device_port):
                            device_object = found_devices["IKA_RV10"][device_port]
                        elif self.simulation:
                            device_object = SimIKARV(port=device_port)
                            found_devices["IKA_RV10"][device_port] = device_object
                        else:
                            device_object = IKARV10(
                                port=device_port,
                                device_name="{0}_IKA_RV10".format(each_node),
                                connect_on_instantiation=True,
                                soft_fail_for_testing=True
                            )
                            found_devices["IKA_RV10"][device_port] = device_object
                            device_object.initialise()
                        self.graph.node[each_node]["IKA_RV10"] = device_object

                    elif device_type == "CVC3000":
                        if found_devices["CVC3000"].get(device_port):
                            device_object = found_devices["CVC3000"][device_port]
                        elif self.simulation:
                            device_object = SimCVC3000(port=device_port)
                            found_devices["CVC3000"][device_port] = device_object
                        else:
                            device_object = CVC3000(
                                port=device_port,
                                device_name="{0}_CVC3000".format(each_node),
                                connect_on_instantiation=True
                            )
                            found_devices["CVC3000"][device_port] = device_object
                            device_object.initialise()
                        self.graph.node[each_node]["CVC3000"] = device_object

                    elif device_type == "CF41":
                        if found_devices["CF41"].get(device_port):
                            device_object = found_devices["CF41"][device_port]
                        elif self.simulation:
                            device_object = SimJULABOCF41(port=device_port)
                            found_devices["CF41"][device_port] = device_object
                        else:
                            device_object = JULABOCF41(
                                port=device_port,
                                device_name="{0}_CF41".format(each_node),
                                connect_on_instantiation=True
                            )
                            found_devices["CF41"][device_port] = device_object
                        self.graph.node[each_node]["CF41"] = device_object

                    elif device_type == "Huber":
                        if found_devices["Huber"].get(device_port):
                            device_object = found_devices["Huber"][device_port]
                        elif self.simulation:
                            device_object = SimHuber(port=device_port)
                            found_devices["Huber"][device_port] = device_object
                        else:
                            device_object = Huber(
                                port=device_port,
                                device_name="{0}_Huber".format(each_node),
                                connect_on_instantiation=True
                            )
                            found_devices["Huber"][device_port] = device_object
                        self.graph.node[each_node]["Huber"] = device_object

                    elif device_type == "conductivity_sensor":
                        if found_devices["conductivity_sensor"].get(device_port):
                            device_object = found_devices["conductivity_sensor"][device_port]
                        elif self.simulation:
                            device_object = None  # TODO: do something useful here
                            found_devices["conductivity_sensor"][device_port] = device_object
                        else:
                            device_object = serial.Serial(port=device_port)
                            found_devices["conductivity_sensor"][device_port] = device_object
                        self.graph.node[each_node]["conductivity_sensor"] = device_object

                    elif device_type == "chiller_switch":
                        if found_devices["chiller_switch"].get(device_port):
                            device_object = found_devices["chiller_switch"][device_port]
                        elif self.simulation:
                            device_object = None  # TODO: do something useful here
                            found_devices["chiller_switch"][device_port] = device_object
                        else:
                            device_object = serial.Serial(port=device_port)
                            found_devices["chiller_switch"][device_port] = device_object
                        self.graph.node[each_node]["chiller_switch"] = device_object

                    elif device_type == "vacuum_valve":
                        if found_devices["vacuum_valve"].get(device_port):
                            device_object = found_devices["vacuum_valve"][device_port]
                        elif self.simulation:
                            device_object = SimChemputerValve(address=device_port, name="{0}_vacuum_valve".format(each_node))
                            found_devices["vacuum_valve"][device_port] = device_object
                        else:
                            device_object = ChemputerValve(address=device_port, name="{0}_vacuum_valve".format(each_node))
                            found_devices["vacuum_valve"][device_port] = device_object
                            device_object.clear_errors()
                        device_object.move_home()
                        device_object.wait_until_ready()
                        device_object.move_to_position(BACKBONE_PORT)
                        device_object.wait_until_ready()
                        self.graph.node[each_node]["vacuum_valve"] = device_object

                    elif device_type == "cartridge_carousel":
                        ip_addresses = device_port.split(" ")
                        if found_devices["cartridge_carousel"].get(device_port):
                            first_valve = found_devices["cartridge_carousel"][device_port][0]
                            second_valve = found_devices["cartridge_carousel"][device_port][1]
                        elif self.simulation:
                            first_valve = SimChemputerValve(address=ip_addresses[0], name="{0}_first_cartridge_valve".format(each_node))
                            second_valve = SimChemputerValve(address=ip_addresses[1], name="{0}_second_cartridge_valve".format(each_node))
                            found_devices["cartridge_carousel"][device_port] = [first_valve, second_valve]
                        else:
                            first_valve = ChemputerValve(address=ip_addresses[0], name="{0}_first_cartridge_valve".format(each_node))
                            second_valve = ChemputerValve(address=ip_addresses[1], name="{0}_second_cartridge_valve".format(each_node))
                            found_devices["cartridge_carousel"][device_port] = [first_valve, second_valve]
                            first_valve.clear_errors()
                            second_valve.clear_errors()
                        first_valve.move_home()
                        second_valve.move_home()
                        first_valve.wait_until_ready()
                        second_valve.wait_until_ready()
                        first_valve.move_to_position(STRAIGHT_THROUGH)
                        second_valve.move_to_position(STRAIGHT_THROUGH)
                        first_valve.wait_until_ready()
                        second_valve.wait_until_ready()
                        self.graph.node[each_node]["cartridge_carousel"] = [first_valve, second_valve]

                    elif device_type == "switching_valve":
                        if found_devices["switching_valve"].get(device_port):
                            device_object = found_devices["switching_valve"][device_port]
                        elif self.simulation:
                            device_object = SimChemputerValve(address=device_port, name="{0}_switching_valve".format(each_node))
                            found_devices["switching_valve"][device_port] = device_object
                        else:
                            device_object = ChemputerValve(address=device_port, name="{0}_switching_valve".format(each_node))
                            found_devices["switching_valve"][device_port] = device_object
                            device_object.clear_errors()
                        device_object.move_home()
                        device_object.wait_until_ready()
                        device_object.move_to_position(WASTE_PORT)
                        device_object.wait_until_ready()
                        self.graph.node[each_node]["switching_valve"] = device_object

                    i += 1

        except Exception as e:
            print('Serial devices could not be instantiated!\nError: {0}'.format(e))
            sys.exit(1)

        return self.graph

    def setup_special_devices(self):
        """
        Finds all devices that have two physical inputs (e.g. separator, filter etc.), find the attached "bottom", and
        deletes the edge between them.
        """
        for each_node in self.graph.nodes():  # where each_node is a string containing the node name
            if self.graph.node[each_node][CLASS] in SPECIAL_DEVICES:
                if len(self.graph.successors(each_node)) == 1:  # that is, if it has exactly one successor
                    associated_flask = self.graph.successors(each_node)[0]
                    self.graph.node[each_node][ASSOCIATED_FLASK] = associated_flask  # make the successor an associated item
                    self.graph.node[associated_flask][PARENT_FLASK] = each_node  # establish bidirectional association
                    self.graph.remove_edge(each_node, associated_flask)  # and then remove the edge (otherwise path finding gets screwed)

        return self.graph
