# coding=utf-8
# !/usr/bin/env python
"""
:mod:"chiller_execution" -- Mid-level wrapper class around :mod:"JULABO_CF41"
===================================

.. module:: chiller_execution
   :platform: Windows, Unix
   :synopsis: Mid-level wrapper around chiller control, provides real-live useful methods
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This class provides all real-life applications of recirculation chillers within the Chemputer rig, essentially just
wrapping the original class methods.

For style guide used see http://xkcd.com/1513/
"""

import os
import sys
import inspect
import logging
from time import sleep

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, "..', '.."))

from tools.constants import *


class ChillerExecutioner(object):
    """
    Class for interfacing with the Chiller objects
    """
    def __init__(self, graph, chiller, simulation):
        """
        Initialiser for the ChillerExecutioner class

        Args:
            graph (DiGraph): Graph representing the platform
            chiller (dict): Dictionary containing the chiller names and their associated objects
            simulation (bool): Simulation mode
        """
        self.chiller = chiller
        self.graph = graph
        self.simulation = simulation
        self.logger = logging.getLogger("main_logger.chiller_executioner_logger")

    def start_chiller(self, chiller_name):
        """
        Starts the circulation and heating/cooling action

        Args:
            chiller_name (str): Name of the chiller
        """
        self.logger.info("Starting chiller {0}...".format(chiller_name))
        chiller_obj = self.chiller[chiller_name]
        chiller_obj.start()
        self.logger.info("Done.")

    def stop_chiller(self, chiller_name):
        """
        Stops the circulation and heating/cooling action

        Args:
            chiller_name (str): Name of the chiller
        """
        self.logger.info("Stopping chiller {0}...".format(chiller_name))
        chiller_obj = self.chiller[chiller_name]
        chiller_obj.stop()
        self.logger.info("Done.")

    def set_temp(self, chiller_name, temp):
        """
        Sets the temperature of the chiller

        Args:
            chiller_name (str): Name of the chiller
            temp (float): Temperature to set
        """
        self.logger.info("Setting temperature for chiller {0} to {1}°C...".format(chiller_name, temp))
        chiller_obj = self.chiller[chiller_name]
        chiller_obj.set_temperature(temp=temp)
        self.logger.info("Done.")

    def cooling_power(self, chiller_name, cooling_power):  # TODO check if CF41
        """
        Sets the cooling power of the chiller. Only works with Julabo CF41.

        Args:
            chiller_name (str): Name of the chiller
            cooling_power (int): Cooling power in % (range 0..100)
        """
        self.logger.info("Setting cooling power for chiller {0} to {1}%...".format(chiller_name, cooling_power))
        chiller_obj = self.chiller[chiller_name]
        chiller_obj.set_cooling_power(cooling_power=cooling_power)
        self.logger.info("Done.")

    def ramp_chiller(self, chiller_name, ramp_duration, temp):
        """
        Sets the ramp duration and the end temperature for the chiller

        Args:
            chiller_name (str): Name of the chiller
            ramp_duration (int): duration of the ramp in sec
            temp (float): End temperature to ramp to in °C
        """
        self.logger.info("Setting ramp duration and temperature for chiller {0} to {1}°C...".format(chiller_name, ramp_duration, temp))
        chiller_obj = self.chiller[chiller_name]
        chiller_obj.set_ramp_duration(ramp_duration=ramp_duration)
        chiller_obj.start_ramp(temp=temp)
        self.logger.info("Done.")

    def switch_vessel(self, vessel_name, state):
        """

        :param vessel_name:
        :param state:
        :return:
        """
        # acquire sensor
        try:
            sensor_connection = self.graph.node[vessel_name]["chiller_switch"] #should be enough, because its on same port

        except KeyError:
            self.logger.exception("Error. Flask or valveconnection not found!")
            return

        if self.simulation:
            self.logger.info("Now the chiller switches")

        else:
            if state == "1":
                sensor_connection.write("1".encode())
                reading = sensor_connection.readline().decode().strip()
                self.logger.info("Chiller is switched {0}.".format(reading))
            elif state == "0":
                sensor_connection.write("0".encode())
                reading = sensor_connection.readline().decode().strip()
                self.logger.info("Chiller is switched {0}.".format(reading))

    def wait_for_temp(self, chiller_name):
        """
        Waits for the chiller to reach its setpoint temperature (approaching from either way)

        Args:
            chiller_name (str): Name of the chiller
        """
        if self.simulation:
            self.logger.info("Waiting for temperature... Done.")
        else:
            chiller_obj = self.chiller[chiller_name]
            setpoint = chiller_obj.get_setpoint()
            self.logger.info("Chiller {0} waiting to reach {1}°C...".format(chiller_name, setpoint))
            if chiller_obj.get_temperature() < setpoint:  # approach from below
                while abs(chiller_obj.get_temperature() - setpoint) > COOLING_THRESHOLD:
                    self.logger.info("Still heating... Current temperature: {0}°C".format(chiller_obj.get_temperature()))
                    sleep(5)
            elif chiller_obj.get_temperature() > setpoint:  # approach from above
                while abs(chiller_obj.get_temperature() - setpoint) > COOLING_THRESHOLD:
                    self.logger.info("Still cooling... Current temperature: {0}°C".format(chiller_obj.get_temperature()))
                    sleep(5)
