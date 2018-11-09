# coding=utf-8
# !/usr/bin/env python
"""
:mod:"rotavap_execution" -- Mid-level wrapper class around :mod:"IKA_RV10"
===================================

.. module:: rotavap_execution
   :platform: Windows, Unix
   :synopsis: Mid-level wrapper around rotavap control, provides real-live useful methods
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This class provides all real-life applications of rotavaps within the Chemputer rig, essentially just wrapping
the original class methods.

For style guide used see http://xkcd.com/1513/
"""

import logging
from time import sleep


class RotavapExecutioner(object):
    """
    Class for interfacing with the Rotavap objects
    """
    def __init__(self, rotavap, simulation):
        """
        Initialiser for the RotavapExecutioner class

        Args:
            rotavap (dict): Dictionary containing the rotavap names and their associated objects
            simulation (bool): Simulation mode
        """
        self.rotavap = rotavap
        self.simulation = simulation
        self.logger = logging.getLogger("main_logger.rotavap_executioner_logger")
        self.TEMP_WINDOW = 0.5  # degrees

    def initialise(self, rotavap_name):
        """
        Starts the heater for the heating bath

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Initialising rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.initialise()
        self.logger.info("Done.")

    def start_heater(self, rotavap_name):
        """
        Starts the heater for the heating bath

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Starting heater for rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.start_heater()
        self.logger.info("Done.")

    def stop_heater(self, rotavap_name):
        """
        Stops the heater for the heating bath

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Stopping heater for rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.stop_heater()
        self.logger.info("Done.")

    def wait_for_temp(self, rotavap_name):
        """
        Waits for the rotavap to reach its setpoint temperature (approaching from either way)

        Args:
            rotavap_name (str): Name of the rotavap
        """
        if self.simulation:
            self.logger.info("Waiting for temperature... Done.")
        else:
            rotavap_obj = self.rotavap[rotavap_name]
            dummy = rotavap_obj.temperature_sp  # reading the fucking setpoint so the fucking rotavap fucking reports fucking accurately
            setpointfloat = float(rotavap_obj.temperature_sp[0])
            self.logger.info("rotavap {0} waiting to reach {1}°C...".format(rotavap_name, setpointfloat))
            while True:
                try:
                    current_temp = float(rotavap_obj.temperature_pv[0])
                except Exception:
                    self.logger.exception("Oh noes! Something went wrong!")
                    continue
                if current_temp < (setpointfloat - self.TEMP_WINDOW):
                    self.logger.info("Still heating... Current temperature: {0}°C".format(current_temp))
                elif current_temp > (setpointfloat + self.TEMP_WINDOW):
                    self.logger.info("Still cooling... Current temperature: {0}°C".format(current_temp))
                else:
                    break  # that's kinda important...
                sleep(5)
    
    def start_rotation(self, rotavap_name):
        """
        Starts rotating the arm of the rotavap

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Starting rotation for rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.start_rotation()
        self.logger.info("Done.")

    def stop_rotation(self, rotavap_name):
        """
        Stops rotating the arm of the rotavap

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Stopping rotation for rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.stop_rotation()
        self.logger.info("Done.")

    def lift_up(self, rotavap_name):
        """
        Raises the arm of the rotavap

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Lifting up rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.lift_up()
        self.logger.info("Done.")

    def lift_down(self, rotavap_name):
        """
        Lowers the arm of the rotavap

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Lifting down rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.lift_down()
        self.logger.info("Done.")

    def reset(self, rotavap_name):
        """
        Resets the rotavap

        Args:
            rotavap_name (str): Name of the rotavap
        """
        self.logger.info("Resetting rotavap {0}...".format(rotavap_name))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.reset_rotavap()
        self.logger.info("Done.")

    def set_temp(self, rotavap_name, temp):
        """
        Sets the temperature of the heating bath

        Args:
            rotavap_name (str): Name of the rotavap
            temp (float): Temperature to set
        """
        self.logger.info("Setting temperature for rotavap {0} to {1}°C...".format(rotavap_name, temp))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.temperature_sp = temp
        self.logger.info("Done.")

    def set_rotation(self, rotavap_name, speed):
        """
        Sets the speed of rotation for the rotavap arm

        Args:
            rotavap_name (str): Name of the rotavap
            speed (int): Speed of rotation to set
        """
        self.logger.info("Setting RPM for rotavap {0} to {1} RPM...".format(rotavap_name, speed))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.rotation_speed_sp = speed
        self.logger.info("Done.")

    def set_interval(self, rotavap_name, interval):
        """
        Sets the interval for the rotavap

        Args:
            rotavap_name (str): Name of the rotavap
            interval (int): Interval in seconds
        """
        self.logger.info("Setting interval for rotavap {0} to {1} seconds...".format(rotavap_name, interval))
        rotavap_obj = self.rotavap[rotavap_name]
        rotavap_obj.set_interval_sp(interval)
        self.logger.info("Done.")
