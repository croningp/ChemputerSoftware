# coding=utf-8
# !/usr/bin/env python
"""
:mod:"IKA_microstar_75" -- API for IKA microstar 7.5 remote controllable overhead stirrer
===================================

.. module:: IKA_microstar_75
   :platform: Windows
   :synopsis: Control IKA microstar 7.5 overhead stirrer.
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>
.. moduleauthor:: Stefan Glatzel <stefan.glatzel@croningroupplc.com>

(c) 2018 The Cronin Group, University of Glasgow

This provides a python class for the IKA microstar 7.5 overhead stirrer
based on software developed by Stefan Glatzel.
The command implementation is based on the German manual pages 32-34.

For style guide used see http://xkcd.com/1513/
"""

# system imports
import re
import os
import inspect
import sys
from time import sleep

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

# additional module imports
from SerialDevice.serial_labware import SerialDevice, command


class IKAmicrostar75(SerialDevice):
    """
    This provides a python class for the IKA microstar 7.5 overhead stirrers
    The command implementation is based on the German manual pages 32-34.
    """

    def __init__(self, port=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the IKAmicrostar75 class

        Args:
            port (str): The port name/number of the stirrer.
            device_name (str): A descriptive name for the device, used mainly in debug prints.
            connect_on_instantiation (bool): (optional) determines if the connection is established on instantiation of
                the class. Default: Off
            soft_fail_for_testing (bool): (optional) switch for just logging an error rather than raising it.
                Default: False
        """
        super().__init__(port, device_name, soft_fail_for_testing)

        # serial settings
        # baud rate etc are default

        self.write_delay = 0.1
        self.read_delay = 0.1

        # answer patterns
        self.valueanswer = re.compile("(\d+\.\d+) (\d)\r\n")
        self.diranswer = re.compile("IN_MODE_(\d)\r\n")

        # DOCUMENTED COMMANDS for easier maintenance
        self.GET_NAME = "IN_NAME"
        self.GET_TEMP_PV = "IN_PV_3"
        self.GET_STIR_RATE_PV = "IN_PV_4"
        self.GET_TORQUE_PV = "IN_PV_5"
        self.GET_STIR_RATE_SP = "IN_SP_4"
        self.GET_TORQUE_SP = "IN_SP_5"
        self.GET_MAX_RPM = "IN_SP_6"
        self.GET_SAFETY_RPM = "IN_SP_8"
        self.SET_STIR_RATE_SP = "OUT_SP_4"
        self.SET_TORQUE_SP = "OUT_SP_5"
        self.SET_MAX_RPM = "OUT_SP_6"
        self.SET_SAFETY_RPM = "OUT_SP_8"
        self.START_STIR = "START_4"
        self.STOP_STIR = "STOP_4"
        self.RESET = "RESET"
        self.SET_DIRECTION = "OUT_MODE_"  # argument: 1 or 2
        self.GET_DIRECTION = "IN_MODE"

        self.launch_command_handler()

        if connect_on_instantiation:
            self.open_connection()

    @property
    @command
    def stir_rate_pv(self):
        """
        Reads the process variable (i.e. the current) stir rate

        Returns:
            call back to send_message with a request to return and check a value
        """
        return self.send_message(self.GET_STIR_RATE_PV, True, self.valueanswer)

    @property
    @command
    def stir_rate_sp(self):
        """
        Reads the set point (target) for the stir rate

        Returns:
            call back to send_message with a request to return and check a value
        """
        return self.send_message(self.GET_STIR_RATE_SP, True, self.valueanswer)

    @stir_rate_sp.setter
    @command
    def stir_rate_sp(self, stir_rate=None):
        """
        Sets the stirrer rate

        Args:
            stir_rate (int): the target stir rate of the hot plate
        """
        try:
            # type checking of the stir rate that the user provided
            stir_rate = int(stir_rate)
        except ValueError:
            raise(ValueError("Error setting stir rate. Rate was not a valid integer \"{0}\"".format(stir_rate)))

        self.logger.debug("Setting stir rate to {0} RPM...".format(stir_rate))

        # actually sending the command
        self.send_message("{0} {1}".format(self.SET_STIR_RATE_SP, stir_rate))

    @property
    @command
    def temperature_pv(self):
        """
        Reads the process variable (i.e. the current) temperature

        Returns:
            call back to send_message with a request to return and check a value
        """
        return self.send_message(self.GET_TEMP_PV, True, self.valueanswer)

    @command
    def start_stirrer(self):
        """
        Starts the stirring operation. Since the stirrer "forgets" the current stir rate every time "START" is sent,
        the method first queries the current setpoint, then starts the stirrer, then sets the RPM again.
        """
        self.logger.debug("Starting stirrer...")
        current_rpm = int(float(self.stir_rate_sp[0]))
        self.send_message(self.START_STIR)
        self.stir_rate_sp = current_rpm

    @command
    def stop_stirrer(self):
        """
        Stops the stirring operation.

        Returns:
            call back to send_message with a request to stop the stirring
        """
        self.logger.debug("Stopping heater...")
        return self.send_message(self.STOP_STIR)

    @property
    @command
    def name(self):
        """
        Returns the name of the stirrer

        Returns:
            call back to send_message with a request to return the name
        """
        return self.send_message(self.GET_NAME, True)

    @property
    @command
    def direction(self):
        """
        Returns the current stirring direction

        Returns:
            either "cw" or "ccw" depending on the currently set direction
        """
        current_direction = self.send_message(self.GET_DIRECTION, True, self.diranswer)
        if current_direction == 1:
            return "cw"
        elif current_direction == 2:
            return "ccw"
        else:
            raise ValueError("ERROR: Stirrer did not return correct direction: \"{0}\"".format(current_direction))

    @direction.setter
    @command
    def direction(self, stir_direction):
        """
        Sets the stirring direction

        Args:
            stir_direction (str): either "cw" or "ccw" for clockwise or counterclockwise
        """
        if stir_direction == "cw":
            self.send_message("{0}1".format(self.SET_DIRECTION))
        elif stir_direction == "ccw":
            self.send_message("{0}2".format(self.SET_DIRECTION))
        else:
            raise ValueError("ERROR: Supplied direction string is invalid: \"{0}\"".format(stir_direction))


if __name__ == '__main__':
    s = IKAmicrostar75(port="COM12", connect_on_instantiation=True)
    s.stir_rate_sp = 500
    s.start_stirrer()
    sleep(10)
    s.stir_rate_sp = 100
    sleep(10)
    print("stir rate = {0}".format(s.stir_rate_pv))
    s.stop_stirrer()
    while True:
        pass
