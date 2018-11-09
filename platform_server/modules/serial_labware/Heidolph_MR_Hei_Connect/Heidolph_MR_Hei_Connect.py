# coding=utf-8
# !/usr/bin/env python
# * ========================================================================= */
# *                                                                           */
# *   Heidolph_MR_Hei_Connect.py                                              */
# *   (c) 2017 Sebastian Steiner, The Cronin Group, University of Glasgow     */
# *                                                                           */
# *   This provides a python class for the Heidolph MR Hei Connect Hotplates  */
# *   The command implementation is based on the German manual version 1.3    */
# *   Serial settings listed in the english version are wrong!                */
# *                                                                           */
# * ========================================================================= */

# system imports
import re
import sys
import inspect
import os
import serial

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

# additional module imports
from SerialDevice.serial_labware import SerialDevice, command


class MRHeiConnect(SerialDevice):
    """
    This provides a python class for the Heidolph MR Hei Connect
    The command implementation is based on the German manual version 1.3
    """

    def __init__(self, port=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the MRHeiConnect class.

        Args:
            port (str): The port name/number of the hotplate
            connect_on_instantiation (bool): (optional) determines if the connection is established on instantiation of
                the class. Default: Off
            soft_fail_for_testing (bool): (optional) determines if an invalid serial port raises an error or merely logs
                a message. Default: Off
        """
        super().__init__(port, connect_on_instantiation, soft_fail_for_testing)

        # serial settings
        self.baudrate = 9600
        self.bytesize = serial.SEVENBITS
        self.parity = serial.PARITY_EVEN

        # answer patterns
        self.stranswer = re.compile("([0-9A-Z_]+)\r\n")
        self.intanswer = re.compile("([0-9A-Z_]+) (-?\d)\r\n")
        self.floatanswer = re.compile("([0-9A-Z_]+) (\d+\.\d+)\r\n")

        # implemented commands
        self.OLD_PROTOCOL = "PA_OLD"
        self.NEW_PROTOCOL = "PA_NEW"
        self.STATUS = "STATUS"
        self.GET_HOT_PLATE_TEMPERATURE_PV = "IN_PV_3"
        self.SET_TEMPERATURE_SP = "OUT_SP_1"
        self.GET_TEMPERATURE_SP = "IN_SP_1"
        self.START_HEATING = "START_1"
        self.WATCHDOG_ON = "CC_ON"
        self.WATCHDOG_OFF = "CC_OFF"

    def keepalive(self):
        """
        Queries the stirrer status every 5 seconds to reset the watchdog. Overrides dummy keepalive from parent method.
        """
        self.non_blocking_wait(callback=self.query_status, interval=5)

    @command
    def switch_protocol(self, protocol="new"):
        if protocol == "new":
            return self.send_message(self.NEW_PROTOCOL, True, self.stranswer)

    @command
    def watchdog_on(self):
        return self.send_message(self.WATCHDOG_ON, True, self.stranswer)

    @command
    def query_status(self):
        return self.send_message(self.STATUS, True, self.intanswer)

    @command
    def start_heating(self):
        return self.send_message(self.START_HEATING, True, self.stranswer)

    @property
    @command
    def temperature_sp(self):
        return self.send_message(self.GET_TEMPERATURE_SP, True, self.floatanswer)

    @temperature_sp.setter
    @command
    def temperature_sp(self, temperature_setpoint):
        try:
            # type checking of the temperature the user provided
            temperature_setpoint = round(int(temperature_setpoint), 1)
        except ValueError:
            raise(ValueError("Error setting temperature. Temperature was not a valid integer \"{0}\"".format(temperature_setpoint)))

        reply = self.send_message("{0} {1}".format(self.SET_TEMPERATURE_SP, temperature_setpoint), True, self.floatanswer)

        try:
            if float(reply[1]) != temperature_setpoint:
                raise ValueError("Error. Setpoint was not set correctly. Sent: {0}. Received: {1}".format(temperature_setpoint, float(reply[1])))
        except:
            raise ValueError("Error. Setpoint was not set correctly. Sent: {0}. Received: {1}".format(temperature_setpoint, float(reply[1])))


if __name__ == "__main__":
    st = MRHeiConnect(port="COM4")
    print("opening {}".format(st.open_connection()))
    print("switching {}".format(st.switch_protocol()))
    print("watchdog on {}".format(st.watchdog_on()))
    print("querying {}".format(st.query_status()))
    print("getting {}".format(st.temperature_sp))
    print("setting")
    st.temperature_sp = 30
    print("getting {}".format(st.temperature_sp))
    print("starting {}".format(st.start_heating()))
    while True:
        pass  # endless loop to keep the daemon thread from dying
