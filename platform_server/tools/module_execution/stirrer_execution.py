# coding=utf-8
# !/usr/bin/env python
"""
:mod:"stirrer_execution" -- Mid-level wrapper class around :mod:"IKA_RET_Control_Visc"
===================================

.. module:: stirrer_execution
   :platform: Windows, Unix
   :synopsis: Mid-level wrapper around hotplate stirrer control, provides real-live useful methods
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This class provides all real-life applications of hotplate stirrers within the Chemputer rig, essentially
just wrapping the original class methods.

For style guide used see http://xkcd.com/1513/
"""

import logging
from time import sleep


class StirrerExecutioner(object):
    """
    Class to interface with Stirrer plates

    TODO: add try/except statements to catch calls to unsupported methods!
    """
    def __init__(self, stirrers, simulation):
        """
        Initialiser for the StirrerExecutioner class

        Args:
            stirrers (dict): Dictionary containing the stirrer names and their associated objects
            simulation (bool): Simulation mode
        """
        self.stirrers = stirrers
        self.simulation = simulation
        self.logger = logging.getLogger("main_logger.stirrer_executioner_logger")

    def stir(self, stirrer_name):
        """
        Starts the stirring the stirrer plate

        Args:
            stirrer_name (str): Name of the stirrer
        """
        self.logger.info("Starting stirring for hotplate {0}...".format(stirrer_name))
        stirrer_obj = self.stirrers[stirrer_name]
        stirrer_obj.start_stirrer()
        self.logger.info("Done.")

    def heat(self, stirrer_name):
        """
        Starts heating the stirrer plate

        Args:
            stirrer_name (str): Name of the stirrer 
        """
        self.logger.info("Starting heating for hotplate {0}...".format(stirrer_name))
        stirrer_obj = self.stirrers[stirrer_name]
        stirrer_obj.start_heater()
        self.logger.info("Done.")

    def wait_for_temp(self, stirrer_name):
        """
        Waits for the stirrer to reach its setpoint temperature (approaching from either way)

        Args:
            stirrer_name (str): Name of the stirrer
        """
        if self.simulation:
            self.logger.info("Waiting for temperature... Done.")
        else:
            stirrer_obj = self.stirrers[stirrer_name]
            setpofloat = float(stirrer_obj.temperature_sp[0])
            self.logger.info("Stirrer {0} waiting to reach {1}°C...".format(stirrer_name, setpofloat))
            if float(stirrer_obj.temperature_pv[0]) < setpofloat:  # approach from below
                while float(stirrer_obj.temperature_pv[0]) < setpofloat:
                    self.logger.info("Still heating... Current temperature: {0}°C".format(float(stirrer_obj.temperature_pv[0])))
                    sleep(5)
            elif float(stirrer_obj.temperature_pv[0]) > setpofloat:  # approach from above
                while float(stirrer_obj.temperature_pv[0]) > setpofloat:
                    self.logger.info("Still cooling... Current temperature: {0}°C".format(float(stirrer_obj.temperature_pv[0])))
                    sleep(5)

    def stop_stir(self, stirrer_name):
        """
        Stops stirring the stirrer plate

        Args:
            stirrer_name (str): Name of the stirrer
        """
        self.logger.info("Stopping stirring for hotplate {0}...".format(stirrer_name))
        stirrer_obj = self.stirrers[stirrer_name]
        stirrer_obj.stop_stirrer()
        self.logger.info("Done.")

    def stop_heat(self, stirrer_name):
        """
        Stops heating the stirrer plate

        Args:
            stirrer_name (str): Name of the stirrer
        """
        self.logger.info("Stopping heating for hotplate {0}...".format(stirrer_name))
        stirrer_obj = self.stirrers[stirrer_name]
        stirrer_obj.stop_heater()
        self.logger.info("Done.")
    
    def set_temp(self, stirrer_name, temp):
        """
        Sets the temperature of the stirrer plate

        Args:
            stirrer_name (str): Name of the stirrer
            temp (float): Temperature to set
        """
        self.logger.info("Setting temperature for hotplate {0} to {1}°C...".format(stirrer_name, temp))
        stirrer_obj = self.stirrers[stirrer_name]
        stirrer_obj.temperature_sp = temp
        self.logger.info("Done.")
    
    def set_stir_rate(self, stirrer_name, stir_rate):
        """
        Sets the stirring rate of the stirrer

        Args:
            stirrer_name (str): Name of the stirrer
            stir_rate (int): Stirring rate to set
        """
        self.logger.info("Setting stir rate for hotplate {0} to {1} RPM...".format(stirrer_name, stir_rate))
        stirrer_obj = self.stirrers[stirrer_name]
        stirrer_obj.stir_rate_sp = stir_rate
        self.logger.info("Done.")
