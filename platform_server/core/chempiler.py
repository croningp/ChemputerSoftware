# coding=utf-8
# !/usr/bin/env python
"""
:mod:"chempiler" -- Main class for Chemputer operation
===================================

.. module:: chempiler
   :platform: Windows, Unix
   :synopsis: Main class for Chemputer operation
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This class ties all other modules together. A GraphML file is parsed into a networkx graph object
containing the architecture. A ChASM file is parsed into a list of commands. The graph and command list
are then passed on to the Executioner, to be executed one by one.

For style guide used see http://xkcd.com/1513/
"""

import inspect
import logging
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

from tools.parsing.ChASM_parser import parser
from tools.chempiler_setup import Setup
from tools.cmd_execution import Executioner

CRASH_DUMP = os.path.normpath(os.path.join(HERE, "..", "..", "client", "crash_dump", "crash_dump.json"))
CRASH_DUMP_KEYS = ["current_volume"]


class Chempiler(object):
    """
    Parses the GraphML file to generate the graph for the platform_server
    Parses the command file for the list of commands to execute and adds them to a queue
    Continues executing commands until the command queue is exhausted

    Args:
        graphml_file (str): Absolute path to the GraphML file for the platform_server
        command_file (str): Absolute path to the command file for the synthesis
    """
    def __init__(self, graphml_file, command_file, crash_dump=False, simulation=False):
        init_setup = Setup(graphml_file, simulation)

        self.logger = logging.getLogger("main_logger")

        self.graph = init_setup.setup_platform()
        if crash_dump:
            self.rebuild_graph()

        self.executioner = Executioner(self.graph, simulation)

        with open(command_file) as f:
            command_string = f.read()
            self.command_queue = parser.parse(command_string, debug=False)

        self.simulation = simulation

        # debug logging
        self.logger.debug("Parsing ChASM file. Command stack:")
        for instruction in self.command_queue:
            self.logger.debug(instruction)

    def run_platform(self):
        """
        Pops a command from the queue and executes it
        """
        if self.simulation:
            self.logger.info('\n\n*** Starting simulated command procedure... ***\n')
        while self.command_queue:
            cmd = self.command_queue.pop(0)
            self.executioner.execute(cmd)
            self.dump_graph()

    def dump_graph(self):
        """
        Gets the useful info of the graph nodes into a dict and dumps them to file
        """
        dump = {}
        for each_node in self.graph.nodes():
            clean_dict = {}
            class_node = self.graph.node[each_node]["class"]
            if class_node == "chemputer_pump" or class_node == "chemputer_valve":
                continue
            for key, value in self.graph.node[each_node].items():
                if key in CRASH_DUMP_KEYS:  # if we want to save the item
                    clean_dict[key] = value

            dump[each_node] = clean_dict
        self.crash_dump_json(dump)

    def crash_dump_json(self, data):
        """
        Dumps the dictionary to file
        """
        with open(CRASH_DUMP, "w+") as f:
            json.dump(data, f, indent=2)

    def rebuild_graph(self):
        """
        Rebuilds the graph from the crash dump
        """
        with open(CRASH_DUMP) as f:
            graph_data = json.load(f)

        for each_node in self.graph.nodes():
            saved_node = graph_data.get(each_node)
            if not saved_node:
                continue
            for key in self.graph.node[each_node].keys():
                saved_value = saved_node.get(key)
                if saved_value:
                    self.graph.node[each_node][key] = saved_value
