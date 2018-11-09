# coding=utf-8
# !/usr/bin/env python
"""
:mod:"vacuum_execution" -- Mid-level wrapper class around :mod:"Vacuubrand_CVC_3000"
===================================

.. module:: vacuum_execution
   :platform: Windows, Unix
   :synopsis: Mid-level wrapper around vacuum pump control, provides real-live useful methods
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This class provides all real-life applications of vacuum pumps within the Chemputer rig, essentially
just wrapping the original class methods. It also has a "vent to ambient pressure" function for convenience.

For style guide used see http://xkcd.com/1513/
"""

from time import sleep
import logging


class VacuumExecutioner(object):
    """
    Class to interface with the CVC3000 vacuum pump
    """
    def __init__(self, vacuum, simulation):
        """
        Initialiser for the VacuumExecutioner class.

        Args:
            vacuum (dict): Dictionary containing the vacuum pump name and their associated objects
            simulation (bool): Simulation mode
        """
        self.vacuum = vacuum
        self.simulation = simulation
        self.ATMOSPHERIC_PRESSURE = 900
        self.logger = logging.getLogger("main_logger.vacuum_executioner_logger")

    def initialise(self, vacuum_pump):
        """
        Sets up the vacuum pump, getting it ready for operation

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        self.logger.info("Initialising vacuum pump {0}...".format(vacuum_pump))
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.initialise()
        self.logger.info("Done.")

    def get_vacuum_set_point(self, vacuum_pump):
        """
        Reads the set point (target) for the vacuum pump in Vac control

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        vacuum_obj = self.vacuum[vacuum_pump]
        self.logger.info("Vacuum setpoint for vacuum pump {0} is {1}...".format(vacuum_pump, vacuum_obj.vacuum_sp))

    def set_vacuum_set_point(self, vacuum_pump, vac):
        """
        Sets the vacuum set point

        Args:
            vacuum_pump (str): The name of the vacuum pump
            vac (int): Set point to set
        """
        self.logger.info("Setting vacuum for vacuum pump  {0} to {1}mbar...".format(vacuum_pump, vac))
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.vacuum_sp = vac
        self.logger.info("Done.")

    def start_vacuum(self, vacuum_pump):
        """
        Starts the vacuum pump

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        self.logger.info("Starting vacuum pump {0}...".format(vacuum_pump))
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.start()
        self.logger.info("Done.")

    def stop_vacuum(self, vacuum_pump):
        """
        Stops the vacuum pump

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        self.logger.info("Stopping vacuum pump {0}...".format(vacuum_pump))
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.stop()
        self.logger.info("Done.")

    def vent_vacuum(self, vacuum_pump):
        """
        Vents all the way to atmospheric pressure.

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        self.logger.info("Venting vacuum pump {0}...".format(vacuum_pump))
        if self.simulation:
            self.logger.info("Pffffffffsssssshhhhhhhhhh...")
        else:
            vacuum_obj = self.vacuum[vacuum_pump]
            vacuum_obj.vent()
            # wait for the venting to complete
            while True:
                pressure = vacuum_obj.vacuum_pv()
                self.logger.debug("Current pressure is {0} {1}.".format(pressure[0], pressure[1]))
                if float(pressure[0]) > self.ATMOSPHERIC_PRESSURE:  # if the pressure is about ambient pressure
                    vacuum_obj.vent(0)
                    self.logger.info("Venting finished.")
                    break
                else:
                    self.logger.debug("Still venting...")
                    sleep(5)
            self.logger.info("Done.")

    def get_status(self, vacuum_pump):
        """
        Gets the status of the vacuum pump

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        vacuum_obj = self.vacuum[vacuum_pump]
        self.logger.info(vacuum_obj.query_status())

    def get_end_vacuum_set_point(self, vacuum_pump):
        """
        Gets the set point (target) for the switch off vacuum in mode Auto

        Args:
            vacuum_pump (str): The name of the vacuum pump             
        """
        vacuum_obj = self.vacuum[vacuum_pump]
        self.logger.info(vacuum_obj.end_vacuum_sp)

    def set_end_vacuum_set_point(self, vacuum_pump, vac):
        """
        Sets the switch off vacuum set point

        Args:
            vacuum_pump (str): The name of the vacuum pump
            vac (int): Set point value to set
        """
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.end_vacuum_sp = vac

    def get_runtime_set_point(self, vacuum_pump):
        """
        Gets the set point (target) for the run time in mode Auto

        Args:
            vacuum_pump (str): The name of the vacuum pump
        """
        vacuum_obj = self.vacuum[vacuum_pump]
        self.logger.info(vacuum_obj.runtime_sp)

    def set_runtime_set_point(self, vacuum_pump, time):
        """
        Sets the set point for the runtime

        Args:
            vacuum_pump (str): The name of the vacuum pump
            time (int): Desired runtime
        """
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.runtimesp = time

    def set_speed_set_point(self, vacuum_pump, speed):
        """
        Sets the set point for the speed

        Args:
            vacuum_pump (str): The name of the vacuum pump
            speed (int): Desired speed
        """
        self.logger.info("Setting speed for vacuum pump {0} to {1}%...".format(vacuum_pump, speed))
        vacuum_obj = self.vacuum[vacuum_pump]
        vacuum_obj.speed_sp = speed
