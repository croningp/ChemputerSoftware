# coding=utf-8
# !/usr/bin/env python
"""
:mod:"IKA_RET_Control_Visc" -- API for IKA RET Control Visc remote controllable hotplate stirrer
===================================

.. module:: IKA_RET_Control_Visc
   :platform: Windows
   :synopsis: Control IKA RET Control Visc hotplate stirrer.
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>
.. moduleauthor:: Stefan Glatzel <stefan.glatzel@croningroupplc.com>

(c) 2017 The Cronin Group, University of Glasgow

This provides a python class for the IKA RET Control Visc Hotplates
based on software developed by Stefan Glatzel.
The command implementation is based on the english manual:
English manual version: 20000004159, RET control-visc_112015
Pages 31 - 34, the german version, same file pages 15 - 18 appears
to contain more and better information.

For style guide used see http://xkcd.com/1513/
"""

# system imports
import re
import serial
import os
import inspect
import sys

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

# additional module imports
from SerialDevice.serial_labware import SerialDevice, command


class IKARETControlVisc(SerialDevice):
    """
    This provides a python class for the IKA RET Control Visc Hotplates
    The command implementation is based on the english manual:
    English manual version: 20000004159, RET control-visc_112015, Pages 31 - 34,
        the german version, same file pages 15 - 18 appears to contain more and better information.
    """

    def __init__(self, port=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the IKARETControlVisc class.

        Args:
            port (str): The port name/number of the hotplate
            device_name (str): A descriptive name for the device, used mainly in debug prints.
            connect_on_instantiation (bool): (optional) determines if the connection is established on instantiation of
                the class. Default: Off
            soft_fail_for_testing (bool): (optional) determines if an invalid serial port raises an error or merely logs
                a message. Default: Off
        """
        super().__init__(port, device_name, soft_fail_for_testing)

        # serial settings
        self.baudrate = 9600
        self.bytesize = serial.SEVENBITS
        self.parity = serial.PARITY_EVEN
        self.rtscts = True

        self.write_delay = 0.1
        self.read_delay = 0.1

        # answer patterns
        self.stranswer = re.compile("([0-9A-Z_]+)\r\n")
        self.valueanswer = re.compile("(\d+\.\d+) (\d)\r\n")
        self.wdanswer = re.compile("(\d+\.\d+)\r\n")

        # other settings
        self.IKA_default_name = "IKARET"

        # DOCUMENTED COMMANDS for easier maintenance
        self.GET_STIR_RATE_PV = "IN_PV_4"
        self.GET_STIR_RATE_SP = "IN_SP_4"
        self.SET_STIR_RATE_SP = "OUT_SP_4"
        self.GET_TEMP_PV = "IN_PV_1"
        self.GET_TEMP_SP = "IN_SP_1"
        self.SET_TEMP_SP = "OUT_SP_1"
        self.START_TEMP = "START_1"
        self.STOP_TEMP = "STOP_1"
        self.START_STIR = "START_4"
        self.STOP_STIR = "STOP_4"
        self.START_PH = "START_80"
        self.STOP_PH = "STOP_80"
        self.START_WEIGHING = "START_90"
        self.STOP_WEIGHING = "STOP_90"
        self.RESET = "RESET"
        self.GET_NAME = "IN_NAME"
        self.SET_NAME = "OUT_NAME"
        self.GET_SOFTWARE_VERSION = "IN_SOFTWARE"
        self.GET_MEDIUM_TEMPERATURE_SP = "IN_SP_7"
        self.GET_HOT_PLATE_TEMPERATURE_PV = "IN_PV_2"
        self.GET_HOT_PLATE_TEMPERATURE_SP = "IN_SP_2"
        self.SET_HOT_PLATE_TEMPERATURE_SP = "OUT_SP_2"
        self.GET_HOT_PLATE_SAFETY_TEMPERATURE_PV = "IN_PV_3"
        self.GET_HOT_PLATE_SAFETY_TEMPERATURE_SP = "IN_SP_3"
        self.GET_PH_PV = "IN_PV_80"
        self.GET_WEIGHT_PV = "IN_PV_90"

        self.launch_command_handler()

        if connect_on_instantiation:
            self.open_connection()

    @property
    @command
    def stir_rate_pv(self):
        """
        Reads the process variable (i.e. the current) stir rate
        :return: call back to send_message with a request to return and check a value
        """
        return self.send_message(self.GET_STIR_RATE_PV, True, self.valueanswer)

    @property
    @command
    def stir_rate_sp(self):
        """
        Reads the set point (target) for the stir rate
        :return: call back to send_message with a request to return and check a value
        """
        return self.send_message(self.GET_STIR_RATE_SP, True, self.valueanswer)

    @stir_rate_sp.setter
    @command
    def stir_rate_sp(self, stir_rate=None):
        """
        Sets the stirrer rate and return the set point from the hot plate so the user can verify that it was successful.

        Args:
            stir_rate (int): the target stir rate of the hot plate

        Returns:
            call back to get_stirrer_rate_set_point()
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
        # reading the process variable
        return self.send_message(self.GET_TEMP_PV, True, self.valueanswer)

    @property
    @command
    def temperature_sp(self):
        return self.send_message(self.GET_TEMP_SP, True, self.valueanswer)

    @temperature_sp.setter
    @command
    def temperature_sp(self, temperature=None):
        """
        Sets the target temperature for sensor 1 (i.e. "medium temperature (external temperature sensor)"

        Args:
            temperature (float): the target temperature
        """
        try:
            temperature = float(temperature)
        except ValueError:
            raise(ValueError("Error setting  temperature. Value was not a valid float \"{0}\"".format(temperature)))

        self.logger.debug("Setting temperature setpoint to {0}°C...".format(temperature))

        # actually sending the command
        self.send_message("{0} {1}".format(self.SET_TEMP_SP, temperature))

    @command
    def start_heater(self):
        self.logger.debug("Starting heater...")
        return self.send_message(self.START_TEMP)

    @command
    def stop_heater(self):
        self.logger.debug("Stopping heater...")
        return self.send_message(self.STOP_TEMP)

    @command
    def start_stirrer(self):
        self.logger.debug("Starting stirrer...")
        return self.send_message(self.START_STIR)

    @command
    def stop_stirrer(self):
        self.logger.debug("Stopping heater...")
        return self.send_message(self.STOP_STIR)

    @command
    def start_ph_meter(self):
        return self.send_message(self.START_PH)

    @command
    def stop_ph_meter(self):
        return self.send_message(self.STOP_PH)

    @command
    def start_weighing(self):
        return self.send_message(self.START_WEIGHING)

    @command
    def stop_weighing(self):
        return self.send_message(self.STOP_WEIGHING)

    @command
    def reset_hot_plate(self):
        return self.send_message(self.RESET)

    @property
    @command
    def name(self):
        """
        Returns the name of the hot plate
        :return: call back to send_message with a request to return the name
        """
        return self.send_message(self.GET_NAME, True)

    @name.setter
    @command
    def name(self, name=None):
        """
        Sets the name of the hotplate to "name". Resets to default (self.IKA_default_name) if no name is passed.
        Warns that names longer than 6 characters get truncated upon restart of the hotplate.

        Args:
            name (str): the new name
        """
        if name is None:
            name = self.IKA_default_name
        if len(name) > 6:
            self.logger.debug("Warning name will be shortened to \"{}\" by the hot plate, after restart.".format(name[0:6]))
        self.send_message("{0} {1}".format(self.SET_NAME, name))

    @property
    @command
    def software_version(self):
        """
        Returns the software version of the firmware
        !!!WARNING!!! Despite being documented this does not seem to work as intended, it just returns an empty string
        :return: (supposed to...) software version of the firmware
        """
        return self.send_message(self.GET_SOFTWARE_VERSION, True)

    @command
    def set_watch_dog_temp(self):
        # TODO handle echo!
        pass

    @command
    def set_watch_dog_stir_rate(self):
        # TODO handle echo!
        pass

    @command
    def get_hot_plate_temp_current(self):
        pass

    @property
    @command
    def temperature_heat_transfer_medium_sp(self):
        return self.send_message(self.GET_MEDIUM_TEMPERATURE_SP, True, self.valueanswer)

    @property
    @command
    def temperature_hot_plate_pv(self):
        return self.send_message(self.GET_HOT_PLATE_TEMPERATURE_PV, True, self.valueanswer)

    @property
    @command
    def temperature_hot_plate_sp(self):
        return self.send_message(self.GET_HOT_PLATE_TEMPERATURE_SP, True, self.valueanswer)

    @temperature_hot_plate_sp.setter
    @command
    def temperature_hot_plate_sp(self, temperature):
        """
        Sets the target temperature for sensor 2 (i.e. "hot plate temperature"

        Args:
            temperature (float): the target temperature
        """
        try:
            temperature = float(temperature)
        except ValueError:
            raise(ValueError("Error setting hot plate temperature. "
                             "Value was not a valid float \"{0}\"".format(temperature)
                             ))
        self.send_message("{0} {1}".format(self.SET_HOT_PLATE_TEMPERATURE_SP, temperature))

    @property
    @command
    def temperature_hot_plate_safety_pv(self):
        """
        This is a documented function and does return values, but I cannot figure out what it's supposed to be...
        :return: excellent question...
        """
        self.logger.debug("WARNING! Don't use temperature_hot_plate_safety_pv! (see docstring)")
        return self.send_message(self.GET_HOT_PLATE_SAFETY_TEMPERATURE_PV, True, self.valueanswer)

    @property
    @command
    def temperature_hot_plate_safety_sp(self):
        """
        This returns the current safety temperature set point. There is no equivalent setter function (for obvious
            safety reasons, it actually does not exist in the firmware)
        :return: The current setting of the hot plate safety temperature
        """
        return self.send_message(self.GET_HOT_PLATE_SAFETY_TEMPERATURE_SP, True, self.valueanswer)

    @command
    def get_viscosity_trend(self):
        pass

    @command
    def get_ph(self):
        return self.send_message(self.GET_PH_PV, True, self.valueanswer)

    @command
    def get_weight(self):
        # only works with start weight, takes about 4 sec to calibrate
        return self.send_message(self.GET_WEIGHT_PV, True, self.valueanswer)


if __name__ == '__main__':
    hp = IKARETControlVisc(port="COM5", connect_on_instantiation=True)
    hp.temperature_sp = 40  # setting temperature to 100 °C
    print("temperature_pv {}".format(hp.temperature_pv))
    hp.start_heater()  # starting the heater
    hp.stop_heater()  # stopping heater
    print("temperature_hot_plate_safety_pv {}".format(hp.temperature_hot_plate_pv))
    print("temperature_hot_plate_safety_sp {}".format(hp.temperature_hot_plate_sp))
    print("temperature_hot_plate_safety_pv {}".format(hp.temperature_hot_plate_safety_pv))
    print("temperature_hot_plate_safety_sp {}".format(hp.temperature_hot_plate_safety_sp))
    print("software_version {}".format(hp.software_version))
    while True:
        pass
