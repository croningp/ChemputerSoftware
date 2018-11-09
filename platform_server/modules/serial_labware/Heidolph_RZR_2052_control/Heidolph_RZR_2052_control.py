# coding=utf-8
# !/usr/bin/env python
"""
:mod:"Heidolph_RZR_2052_control" -- API for Heidolph RZR 2052 control remote controllable overhead stirrer
===================================

.. module:: Heidolph_RZR_2052_control
   :platform: Windows
   :synopsis: Control Heidolph RZR 2052 control overhead stirrer
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>
.. moduleauthor:: Stefan Glatzel <stefan.glatzel@croningroupplc.com>

(c) 2018 The Cronin Group, University of Glasgow

This provides a python class for the Heidolph RZR 2052 control overhead stirrer. Command implementation is based on the
manual dated 21/10/2011 downloaded from the Heidolph homepage. The english translation is rubbish, "OUT" refers to
queries, "IN" refers to setting values. Thank fuck I speak German!

For style guide used see http://xkcd.com/1513/
"""

# system imports
import os
import sys
import inspect
import re
from time import sleep

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, ".."))

# additioanl module imports
from SerialDevice.serial_labware import SerialDevice, command


class RZR_2052(SerialDevice):
    """
    This provides a python class for the overhead stirrer
    """
    def __init__(self, port=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the RZR_2052 class

        Args:
            port (str): The port name/number of the stirrer
            device_name (str): A descriptive name for the device, used mainly in debug prints
            connect_on_instantiation (bool): (optional) determines if the connection is established on instantiation of
                the class. Default: Off
            soft_fail_for_testing (bool): (optional) determines if an invalid serial port raises an error or merely
                logs a message. Default: Off
        """
        super().__init__(port, device_name, soft_fail_for_testing)

        # serial settings
        # all settings are at default, 9600 Baud, 8N1, no flow control
        self.timeout = 0.2
        self.command_termination = '\r'

        self.write_delay = 0.1
        self.read_delay = 0.1

        # answer patterns
        self.query_answer = re.compile("([A-Z]{3}): ([0-9]+)\r\n\r\n")  # most answers, except for status and setpoint
        self.setpoint_answer = re.compile("R([0-9]+)\r\n([A-Z]{3}): ([0-9]+)\r\n")  # reply to setting the RPM
        self.status_answer = re.compile("([A-Z]{3}): (.*)\r\n")  # most answers, except for status and setpoint

        # DOCUMENTED COMMANDS for easier maintenance
        self.set_rpm = "R"  # Rxxxx (1-4 digits) sets RPM. limits are 30-1000 rpm
        self.range_II = "A"  # no effect on 2052
        self.range_I = "B"  # no effect on 2052
        self.delete_error = "C"  # restarts the motor
        self.remote_off = "D"  # erroneous translation, meant to be "motor control uses potentiometer" i.e. THE KNOB
        self.set_reference = "N"  # sets zero for analog speed out

        self.get_rpm = "r"  # queries current RPM
        self.get_setpoint = "s"  # queries setpoint
        self.get_torque = "m"  # queries torque
        self.get_error = "f"  # No Error! / Motor Error! / Motor Temperature!

        self.launch_command_handler()

        if connect_on_instantiation:
            self.open_connection()

    @property
    @command
    def stir_rate_pv(self):
        """
        Returns the stir rate process value

        Returns:
            rpm (int): RPM process value
        """
        rpm = self.send_message(self.get_rpm, get_return=True, return_pattern=self.query_answer, multiline=True)
        return int(rpm[1])

    @property
    @command
    def stir_rate_sp(self):
        """
        Returns the stir rate setpoint

        Returns:
            rpm (int): RPM setpoint
        """
        rpm = self.send_message(self.get_setpoint, get_return=True, return_pattern=self.query_answer, multiline=True)
        return int(rpm[1])

    @stir_rate_sp.setter
    @command
    def stir_rate_sp(self, rpm):
        """
        Sets the target rpm for the stirrer, thereby switching it on.

        Args:
            rpm (int): RPM setpoint
        """
        try:
            # type checking of the stir rate that the user provided
            rpm = int(rpm)
        except ValueError:
            raise(ValueError("Error setting stir rate. Rate was not a valid integer \"{0}\"".format(rpm)))

        self.logger.debug("Setting stir rate to {0} RPM...".format(rpm))
        # setting the setpoint
        if 30 <= rpm <= 1000:
            self.send_message("{0}{1:04}".format(self.set_rpm, rpm), get_return=True, return_pattern=self.setpoint_answer, multiline=True)
        else:
            raise ValueError("The set point should be in range 30..1000")

    @command
    def start_stirrer(self):
        """Start the stirrer"""
        self.send_message(self.delete_error, get_return=True, multiline=True)

    @command
    def stop_stirrer(self):
        """Stops the stirrer"""
        self.send_message("{0}{1:04}".format(self.set_rpm, 0), get_return=True, return_pattern=self.setpoint_answer, multiline=True)

    @command
    def get_status(self):
        """ Returns the status of the chiller"""
        status = self.send_message(self.get_error, get_return=True, return_pattern=self.status_answer, multiline=True)
        return status


if __name__ == "__main__":
    stirrer = RZR_2052("COM1", "stirrer", True, False)
    stirrer.stir_rate_sp = 100
    stirrer.start_stirrer()
    for i in range(10):
        sleep(1)
        print(stirrer.stir_rate_pv)
    stirrer.stir_rate_sp = 500
    sleep(5)
    stirrer.stop_stirrer()

