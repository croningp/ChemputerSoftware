# coding=utf-8
# !/usr/bin/env python
"""
:mod:"Huber_Petite_Fleur" -- API for Huber Petite Fleur remote controllable recirculation chiller
===================================

.. module:: Huber_Petite_Fleur
   :platform: Windows
   :synopsis: Control Huber_Petite_Fleur recirculation chiller
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>
.. moduleauthor:: Stefan Glatzel <stefan.glatzel@croningroupplc.com>

(c) 2018 The Cronin Group, University of Glasgow

This provides a python class for the Huber Petite Fleur recirculation chiller. Command implementation is based on the
Data Communication Manual version 1.8.0 downloaded from the Huber homepage. The commands are supposed to work with any
remote controllable Huber temperature controller, but was only tested with our Petite Fleur.

For style guide used see http://xkcd.com/1513/
"""

# system imports
import os
import sys
import inspect
import re
from time import sleep

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

# additioanl module imports
from SerialDevice.serial_labware import SerialDevice, command


class Huber(SerialDevice):
    """
    This provides a python class for the Huber chiller
    """
    def __init__(self, port=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the Huber class

        Args:
            port (str): The port name/number of the chiller
            device_name (str): A descriptive name for the device, used mainly in debug prints
            connect_on_instantiation (bool): (optional) determines if the connection is established on instantiation of
                the class. Default: Off
            soft_fail_for_testing (bool): (optional) determines if an invalid serial port raises an error or merely
                logs a message. Default: Off
        """
        super().__init__(port, device_name, soft_fail_for_testing)

        # serial settings
        # all settings are at default

        self.write_delay = 0.2
        self.read_delay = 0.2

        # TODO check if actually correct
        # answer patterns
        self.answer = re.compile("{S([0-9A-F]{2})([0-9A-F]{4})\r?\n?")  # already picks apart address (capture group 1) and value (capture group 2)

        # DOCUMENTED COMMANDS for easier maintenance
        self.command_start = "{M"
        self.query = "****"  # string for reading a value

        # E-grade "Basic" commands
        self.temp_controller_setpoint = "00"    # LSB = 0.01°C, range = -151.00 - 327.00°C
        self.internal_temperature = "01"        # LSB = 0.01°C, range = -151.00 - 327.00°C
        self.pump_pressure = "03"               # LSB = 1 mbar, range = 0 - 3200 mbar
        self.error_report = "05"                # LSB = 1,      range = -1023 - 0 (set value to 1 to delete errors)
        self.warning_message = "06"             # LSB = 1,      range = -4095 - 0 (set value to 1 to delete errors)
        self.process_temperature = "07"         # LSB = 0.01°C, range = -151.00 - 327.00°C
        self.status = "0A"                      # bit field, for details see manual page 12
        self.temperature_control = "14"         # LSB = 1,      range = 0 - 1 (off or on)
        self.compressor_mode = "15"             # LSB = 1,      range = 0 - 2 (auto, always on, or always off)
        self.circulation = "16"                 # LSB = 1,      range = 0 - 1 (off or on)
        self.key_lock = "17"                    # bit field, for details see manual page 14

        # E-grade "Exclusive" commands
        self.ramp_duration = "59"               # LSB = 1s,     range = -32767 - 32767s (negative values cancel ramp)
        self.start_ramp = "5A"                  # LSB = 0.01°C, range = -151.00 - 327.00°C (sets sp and starts ramp)
        # at this point I got bored, someone may want to type up all the other commands at some point

        self.launch_command_handler()

        if connect_on_instantiation:
            self.open_connection()

    @command
    def set_temperature(self, temp):
        """
        Sets the target temperature of the chiller

        Args:
            temp (float): Temperature setpoint
        """
        # setting the setpoint
        if -151 <= temp <= 327:
            temp = int(temp * 100)  # convert to appropriate decimal format
            temp_string = "{:04X}".format(temp & 0xFFFF)  # convert to two's complement hex string
        else:
            raise ValueError('The set point should be in range 0..2')

        self.send_message('{0}{1}{2}'.format(self.command_start, self.temp_controller_setpoint, temp_string), True, self.answer)

    @command
    def start(self):
        """Starts the chiller"""
        # start circulation
        self.send_message('{0}{1}{2:04}'.format(self.command_start, self.circulation, 1), True, self.answer)
        # start temperature control
        self.send_message('{0}{1}{2:04}'.format(self.command_start, self.temperature_control, 1), True, self.answer)

    @command
    def stop(self):
        """Stops the chiller"""
        # stop temperature control
        self.send_message('{0}{1}{2:04}'.format(self.command_start, self.temperature_control, 0), True, self.answer)
        # stop circulation
        self.send_message('{0}{1}{2:04}'.format(self.command_start, self.circulation, 0), True, self.answer)

    @command
    def get_temperature(self):
        """Reads the current temperature of the bath"""
        answer = self.send_message('{0}{1}{2}'.format(self.command_start, self.internal_temperature, self.query), True, self.answer)
        if answer[0] == self.internal_temperature:
            # convert two's complement 16 bit signed hex to signed int
            if int(answer[1], 16) > 32767:
                return (int(answer[1], 16) - 65536) / 100
            else:
                return (int(answer[1], 16)) / 100

    @command
    def get_setpoint(self):
        """Reads the current temperature setpoint"""
        answer = self.send_message('{0}{1}{2}'.format(self.command_start, self.temp_controller_setpoint, self.query), True, self.answer)
        if answer[0] == self.temp_controller_setpoint:
            # convert two's complement 16 bit signed hex to signed int
            if int(answer[1], 16) > 32767:
                return (int(answer[1], 16) - 65536) / 100
            else:
                return (int(answer[1], 16)) / 100

    @command
    def set_ramp_duration(self, ramp_duration):
        """
        Sets the duration for a temperature ramp in seconds. Range is -32767...32767s where negative values cancel the
        ramp. Maximum ramp is a tad over 9 hours.

        Args:
            ramp_duration (int): duration of the ramp in seconds
        """
        # setting the setpoint
        if -32767 <= ramp_duration <= 32767:
            ramp_duration_string = "{:04X}".format(ramp_duration & 0xFFFF)  # convert to two's complement hex string
        else:
            raise ValueError('The set point should be in range -32767..32767')

        self.send_message('{0}{1}{2}'.format(self.command_start, self.set_ramp_duration, ramp_duration_string), True, self.answer)

    @command
    def start_ramp(self, temp):
        """
        Sets the target temperature of the chiller and starts a ramp towards that temperature.

        Args:
            temp (float): Temperature setpoint
        """
        # setting the setpoint
        if -151 <= temp <= 327:
            temp = int(temp * 100)  # convert to appropriate decimal format
            temp_string = "{:04X}".format(temp & 0xFFFF)  # convert to two's complement hex string
        else:
            raise ValueError('The set point should be in range 0..2')

        self.send_message('{0}{1}{2}'.format(self.command_start, self.start_ramp, temp_string), True, self.answer)

    # @command
    # def get_status(self):
    #     """ Returns the status of the chiller"""
    #     status = self.send_message(self.STATUS, True)
    #     return status


if __name__ == '__main__':
    chiller = Huber('COM7', 'chiller', True, False)

    chiller.set_temperature(1.0)
    chiller.start()
    for i in range(10):
        sleep(2)
        print(chiller.get_temperature())
    print(chiller.get_status())
    chiller.stop()

