# coding=utf-8
# !/usr/bin/env python
"""
:mod:"Vacuubrand_CVC_3000" -- API for Vacuubrand CVC3000 remote controllable vacuum controller
===================================

.. module:: Vacuubrand_CVC_3000
   :platform: Windows
   :synopsis: Control CVC3000 vacuum controller.
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This provides a python class for Vacuubrand vacuum pumps with
CVC 3000 vacuum controller.
The command implementation is based on the english manual:
English manual version: 999222 / 11/03/2016 Pages 40 - 45

For style guide used see http://xkcd.com/1513/
"""

# system imports
import re
import serial
import os
import inspect
import sys
from time import sleep

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

# additional module imports
from SerialDevice.serial_labware import SerialDevice, command


class CVC3000(SerialDevice):
    """
    This provides a python class for Vacuubrand vacuum pumps with
    CVC 3000 vacuum controller.
    The command implementation is based on the english manual:
    English manual version: 999222 / 11/03/2016 Pages 40 - 45
    """

    def __init__(self, port=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the IKARETControlVisc class
        :param str port: The port name/number of the vacuum pump
        :param str name: A descriptive name for the device, used mainly in debug prints.
        :param bool connect_on_instantiation: (optional) determines if the connection is established on instantiation of
            the class. Default: Off
        """
        # implement class logger
        super().__init__(port, device_name, soft_fail_for_testing)

        # serial settings
        self.baudrate = 19200
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.rtscts = True

        # answer patterns
        self.getanswer = re.compile("([0-9.]+) ([0-9A-z%]+)\r\n")
        self.setanswer = re.compile("([0-9A-z%]+)\r\n")
        self.timepattern = re.compile("\d{2}:\d{2}")
        self.timeanswer = re.compile("(\d{2}:\d{2}) ([hms]:[hms])\r\n")
        self.timesecondsanswer = re.compile("(\d{2}:\d{2}:\d{2}) ([hms]:[hms]:[hms])\r\n")

        # dictionary for modes
        self.MODES_3 = {
            "VACUULAN": 0,
            "pump down": 1,
            "vac control": 2,
            "auto": 3,
            "auto low": 30,
            "auto normal": 31,
            "auto high": 32,
            "program": 4
        }

        # DOCUMENTED COMMANDS for easier maintenance
        # general commands
        self.SET_CONTROLLER_VERSION = "CVC"             # params: 2: CVC 2000; 3: CVC 3000
        self.ECHO = "ECHO"                              # params: 0: echo off, returns nothing; 1: echo on, returns 1
        self.STORE = "STORE"                            # no params, store settings permanently

        # CVC 2000 command set
        # read commands
        self.GET_CURRENT_PRESSURE_2 = "IN_PV_1"         # unit mbar/hPa/Torr (according to preselection)
        self.GET_CURRENT_FREQUENCY_2 = "IN_PV_2"        # unit Hz
        self.GET_DEVICE_CONFIG_2 = "IN_CFG"             # unit none, for decoding see manual p. 41
        self.GET_ERROR_2 = "IN_ERR"                     # unit none, for decoding see manual p. 41
        self.GET_STATUS_2 = "IN_STAT"                   # unit none, for decoding see manual p. 41
        # write commands
        self.SET_MODE_2 = "OUT_MODE"                    # unit none, for parameters see manual p. 41
        self.SET_VACUUM_2 = "OUT_SP_1"                  # unit mbar/hPa/Torr (according to preselection)
        self.SET_VACUUM_WITH_VENTING_2 = "OUT_SP_V"     # unit mbar/hPa/Torr (according to preselection)
        self.SET_FREQUENCY_2 = "OUT_SP_2"               # unit Hz; format XX.X; 99.9 for "HI"
        self.SET_VACUUM_FOR_SWITCH_ON_2 = "OUT_SP_3"    # unit mbar/hPa/Torr (according to preselection), VACUU·LAN only
        self.SET_DELAY_2 = "OUT_SP_4"                   # unit hh:mm; format XX:XX; VACUU·LAN only; max. 05:00
        self.SET_SWITCHING_OFF_VAC_2 = "OUT_SP_5"       # unit mbar/hPa/Torr (according to preselection)
        self.SET_SWITCHING_OFF_TIME_2 = "OUT_SP_6"      # unit hh:mm; format XX:XX
        self.START_2 = "START"                          # always returns 1
        self.STOP_2 = "STOP"                            # params: None: stops operation, returns 0; 1: stops operation,
                                                        # returns 1; 2: stops operation and stores current pressure as
                                                        # new setpoint, returns 2
        self.REMOTE_2 = "REMOTE"                        # params: 0: local operation, returns 0;
                                                        # 1: remote operation, returns 1
        self.VENT_VALVE_2 = "OUT_VENT"                  # params: 0: closed, returns 0;
                                                        # 1: open and stop operation, returns 1

        # CVC 3000 command set
        # read commands
        self.GET_CURRENT_PRESSURE_3 = "IN_PV_1"         # unit mbar/hPa/Torr (according to preselection)
        self.GET_TRANSDUCER_X_PRESSURE_3 = "IN_PV_S"    # command is followed by transducer Nr without space;
                                                        # unit mbar/hPa/Torr (according to preselection)
        self.GET_CURRENT_SPEED_3 = "IN_PV_2"            # unit 1-100% or "HI"
        self.GET_PROCESS_TIME_3 = "IN_PV_3"             # unit hh:mm; format XX:XX h:m
        self.GET_ALL_PRESSURES_3 = "IN_PV_X"            # unit mbar/hPa/Torr (according to preselection);
                                                        # returns pressures of all connected sensors separated by spaces
        self.GET_CONTROLLER_RUN_TIME_3 = "IN_PV_T"      # unit days and hours; format XXXXdXXh
        self.GET_DEVICE_CONFIG_3 = "IN_CFG"             # unit none, for decoding see manual p. 42
        self.GET_ERROR_3 = "IN_ERR"                     # unit none, for decoding see manual p. 42
        self.GET_STATUS_3 = "IN_STAT"                   # unit none, for decoding see manual p. 42
        self.GET_VACUUM_SETPOINT_3 = "IN_SP_1"          # unit mbar/hPa/Torr (according to preselection)
        self.GET_MAX_SPEED_SETPOINT_3 = "IN_SP_2"       # unit 1-100% or "HI"
        self.GET_SWITCHING_PRESSURE_3 = "IN_SP_3"       # switching pressure for VACUU·LAN or two point control,
                                                        # unit mbar/hPa/Torr (according to preselection)
        self.GET_DELAY_3 = "IN_SP_3"                    # unit hh:mm; format XX:XX h:m; 00:00 = off
        self.GET_SWITCHING_OFF_VAC_3 = "IN_SP_5"        # "maximum" for "vac control"; "minimum" for "pump down";
                                                        # unit mbar/hPa/Torr (according to preselection)
        self.GET_RUNTIME_3 = "IN_SP_6"                  # process runtime; unit hh:mm; format XX:XX h:m
        self.GET_STEP_TIME_3 = "IN_SP_P1"               # followed by a number y without space; time in program step y
                                                        # unit hh:mm:ss; format XX:XX:XX h:m:s
        self.GET_STEP_PRESSURE_3 = "IN_SP_P2"           # followed by a number y without space;
                                                        # pressure in program step y;
                                                        # unit mbar/hPa/Torr (according to preselection)
        self.GET_STEP_VALVE_3 = "IN_SP_P3"              # followed by a number y without space; venting valve in
                                                        # program step y; unit none; 0: no vent; 1: vent
        self.GET_STEP_STEP_3 = "IN_SP_P4"               # followed by a number y without space; step mark in
                                                        # program step y; unit none; 0: no step; 1: step
        self.GET_STEP_AUTO_3 = "IN_SP_P5"               # followed by a number y without space; automatic boiling point
                                                        # finding in program step y; 0: no auto; 1: auto
        self.GET_VERSION_3 = "IN_VER"                   # software version; format CVC 3000 VX.XX
        # write commands
        self.SET_MODE_3 = "OUT_MODE"                    # unit none, for parameters see manual p. 44
        self.SET_CONFIG_3 = "OUT_CFG"                   # unit none, for parameters see manual p. 44
        self.SET_VACUUM_3 = "OUT_SP_1"                  # unit mbar/hPa/Torr (according to preselection)
        self.SET_VACUUM_WITH_VENTING_3 = "OUT_SP_V"     # unit mbar/hPa/Torr (according to preselection)
        self.SET_SPEED_3 = "OUT_SP_2"                   # unit 1-100% or "HI"
        self.SET_START_UP_PRESSURE_3 = "OUT_SP_3"       # unit mbar/hPa/Torr (according to preselection)
        self.SET_DELAY_3 = "OUT_SP_4"                   # unit hh:mm; format XX:XX
        self.SET_SWITCHING_OFF_VAC_3 = "OUT_SP_5"       # "maximum" for "vac control"; "minimum" for "pump down";
                                                        # unit mbar/hPa/Torr (according to preselection)
        self.SET_RUNTIME_3 = "OUT_SP_6"                 # process runtime; unit hh:mm
        self.OPEN_PROGRAM_3 = "OUT_SP_PL"               # unit none, program 0...9
        self.STORE_PROGRAM_3 = "OUT_SP_PS"              # unit none, program 0...9
        self.SET_STEP_TIME_3 = "OUT_SP_P1"              # followed by a number y without space; time in program step y
                                                        # unit hh:mm:ss; format XX:XX:XX or +XX:XX:XX for additive time
        self.SET_STEP_PRESSURE_3 = "OUT_SP_P2"          # followed by a number y without space;
                                                        # pressure in program step y;
                                                        # unit mbar/hPa/Torr (according to preselection)
        self.SET_STEP_VALVE_3 = "OUT_SP_P3"             # followed by a number y without space; venting valve in
                                                        # program step y; unit none; 0: no vent; 1: vent
        self.SET_STEP_STEP_3 = "OUT_SP_P4"              # followed by a number y without space; step mark in
                                                        # program step y; unit none; 0: no step; 1: step
        self.SET_STEP_AUTO_3 = "OUT_SP_P5"              # followed by a number y without space; automatic boiling point
                                                        # finding in program step y; 0: no auto; 1: automatic
                                                        # determination of boiling point,
                                                        # 2: automatic adaption to changes
        self.START_3 = "START"                          # always returns 1
        self.STOP_3 = "STOP"                            # params: None: stops operation, returns 0; 1: stops operation,
                                                        # returns 1; 2: stops operation and stores current pressure as
                                                        # new setpoint, returns 2
        self.REMOTE_3 = "REMOTE"                        # params: 0: local operation, returns 0;
                                                        # 1: remote operation, returns 1
        self.VENT_VALVE_3 = "OUT_VENT"                  # params: 0: closed, returns 0;
                                                        # 1: open and stop operation, returns 1
        self.SET_SENSOR_3 = "OUT_SENSOR"                # params: 1: internal sensor; 2...9: external sensors

        self.launch_command_handler()

        if connect_on_instantiation:
            self.open_connection()

    def initialise(self, controller_version="CVC 3000"):
        """
        Does the necessary setup work. Turns ECHO on, sets the desired controller version
        and sets the mode to Vac control (in order to always start from the same spot).
        :param controller_version: desired controller version ("CVC 2000" or "CVC 3000")
        """
        self.logger.debug("Initialising CVC3000...")
        if controller_version == "CVC 2000":
            # switch to remote control
            self.send_message("{0} {1}".format(self.REMOTE_2, "1"), get_return=True)
            # turn echo on
            self.send_message("{0} {1}".format(self.ECHO, "1"), get_return=True, return_pattern=self.setanswer)
            # switch to CVC 2000 command set
            self.send_message("{0} {1}".format(self.SET_CONTROLLER_VERSION, "2"), get_return=True, return_pattern=self.setanswer)
            # switch to Vac control mode
            self.send_message("{0} {1}".format(self.SET_MODE_2, "2"), get_return=True, return_pattern=self.setanswer)
        elif controller_version == "CVC 3000":
            # switch to remote control
            self.send_message("{0} {1}".format(self.REMOTE_3, "1"), get_return=True)
            # turn echo on
            self.send_message("{0} {1}".format(self.ECHO, "1"), get_return=True, return_pattern=self.setanswer)
            # switch to CVC 3000 command set
            self.send_message("{0} {1}".format(self.SET_CONTROLLER_VERSION, "3"), get_return=True, return_pattern=self.setanswer)
            # switch to Vac control mode
            self.send_message("{0} {1}".format(self.SET_MODE_3, "2"), get_return=True)
        self.logger.debug("Done.")

    # CVC 2000 methods
    # TODO: I can't be asked to write that just now, if someone is especially bored please have a go at it...

    # CVC 3000 methods
    @command
    def set_mode(self, mode):
        """
        Sets the mode of the vacuum controller.
        :param mode: (string) the mode to be set. Must be a valid key in the MODES_3 dict.
        :return: call back to __send_message with an order to set the mode
        """
        try:
            mode_number = self.MODES_3[mode]
        except KeyError:
            raise (KeyError("Error setting mode. Input is not a valid mode name \"{0}\"".format(mode)))

        self.logger.debug("Setting mode to {0}...".format(mode))

        reply = self.send_message("{0} {1}".format(self.SET_MODE_3, mode_number), True, self.setanswer)
        if int(reply[0]) != mode_number:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Send: \"{0}\". "
                "Received: \"{1}\".".format(mode_number, reply[0])
            )

    @property
    @command
    def vacuum_sp(self):
        """
        Reads the set point (target) for the vacuum in mode Vac control
        :return: call back to send_message with a request to return a value
        """
        return self.send_message(self.GET_VACUUM_SETPOINT_3, True, self.getanswer)

    @vacuum_sp.setter
    @command
    def vacuum_sp(self, vacuum=None):
        """
        Sets the vacuum and returns the set point from the pump so the user can verify that it was successful
        :param vacuum: (integer) the target vacuum
        """
        try:
            # type checking of the vacuum that the user provided
            vacuum = int(vacuum)
        except ValueError:
            raise(ValueError("Error setting vacuum. Vacuum was not a valid integer \"{0}\"".format(vacuum)))

        self.logger.debug("Setting vacuum setpoint to {0}...".format(vacuum))

        # actually sending the command
        reply = self.send_message("{0} {1}".format(self.SET_VACUUM_3, vacuum), True, self.setanswer)
        try:
            reply_value = int(reply[0])
        except ValueError:
            raise (ValueError("Error setting vacuum. Reply was not a valid integer \"{0}\"".format(reply[0])))
        if reply_value != vacuum:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Send: \"{0}\". "
                "Received: \"{1}\".".format(vacuum, reply_value)
            )

    @property
    @command
    def speed_sp(self):
        """
        Reads the set point (target) for the speed.
        
        Returns:
            call back to send_message with a request to return a value
        """
        return self.send_message(self.GET_MAX_SPEED_SETPOINT_3, True, self.getanswer)

    @speed_sp.setter
    @command
    def speed_sp(self, speed=None):
        """
        Sets the maximum pumping speed (1-100%).
        
        Args:
            speed (int): Maximum speed setpoint. Has to be between 1 and 100
        """
        try:
            # type checking of the speed that the user provided
            speed = int(speed)
        except ValueError:
            raise (ValueError("Error setting speed. Speed was not a valid integer \"{0}\"".format(speed)))

        if not 1 <= speed <= 100:
            raise (ValueError("Error setting speed. Speed was not between 1 and 100% \"{0}\"".format(speed)))

        self.logger.debug("Setting speed setpoint to {0}...".format(speed))

        if speed == 100:
            speed = "HI"

        # actually sending the command
        reply = self.send_message("{0} {1}".format(self.SET_SPEED_3, speed), True, self.setanswer)
        if speed == "HI" and reply[0] != "HI":
            try:
                reply_value = int(reply[0])
            except ValueError:
                raise (ValueError("Error setting speed. Reply was not a valid integer \"{0}\"".format(reply[0])))
            if reply_value != speed:
                raise ValueError(
                    "Value Error. Vacuum pump did not return correct return code. Send: \"{0}\". "
                    "Received: \"{1}\".".format(speed, reply_value)
                )

    @command
    def vacuum_pv(self):
        """
        Reads the process value (actual pressure) for the vacuum in any mode
        :return: call back to send_message with a request to return a value
        """
        return self.send_message(self.GET_CURRENT_PRESSURE_3, True, self.getanswer)

    @command
    def start(self):
        """
        Starts the current function.
        :return: True if pump responds properly, else a ValueError is raised.
        """
        self.logger.debug("Starting operation...")
        reply = self.send_message(self.START_3, True, self.setanswer)
        try:
            reply_value = int(reply[0])
        except ValueError:
            raise (ValueError("Error starting operation. Reply was not a valid integer \"{0}\"".format(reply[0])))
        if reply_value == 1:
            self.logger.debug("Done.")
            return True
        elif reply_value == "":
            raise ValueError("Value Error. Vacuum pump appears to be already running!")
        else:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Expected: 1. "
                "Received: \"{0}\".".format(reply_value)
            )

    @command
    def stop(self, stop_mode=None):
        """
        Stops the current function. This does not utilise the different stop parameters, but they seem to serve
        no apparent purpose anyway.
        :return: True if pump responds properly, else a ValueError is raised.
        """
        self.logger.debug("Stopping operation...")
        reply = self.send_message(self.STOP_3, True, self.setanswer)
        try:
            reply_value = int(reply[0])
        except ValueError:
            raise (ValueError(
                "Error stopping operation. Reply was not a valid integer \"{0}\"".format(reply[0])))
        if reply_value != 0:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Expected: {0}. "
                "Received: \"{1}\".".format(stop_mode, reply_value)
            )
        self.logger.debug("Done.")

    @command
    def vent(self, vent_status=1):
        """
        Controls the vent valve.
        :param vent_status: 0: valve closed; 1: valve open; 2: vent to atmospheric pressure
        :return: True if pump responds properly, else a ValueError is raised.
        """
        try:
            # type checking of the vent status that the user provided
            vent_status = int(vent_status)
        except ValueError:
            raise (ValueError("Error while venting. Vent status was not a valid integer \"{0}\"".format(vent_status)))

        self.logger.debug("Actuating vent valve...")

        # actually sending the command
        reply = self.send_message("{0} {1}".format(self.VENT_VALVE_3, vent_status), True, self.setanswer)
        try:
            reply_value = int(reply[0])
        except ValueError:
            raise (ValueError("Error while venting. Reply was not a valid integer \"{0}\"".format(reply[0])))
        if reply_value == vent_status:
            self.logger.debug("Done.")
            return True
        else:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Send: \"{0}\". "
                "Received: \"{1}\".".format(vent_status, reply_value)
            )

    @command
    def query_status(self):
        """
        Queries the status of the pump. For individual parameters see manual p. 43
        :return: dictionary of status items
        """
        status = {}  # initialise empty dict
        reply = self.send_message(self.GET_STATUS_3, True)  # get status as series of digits
        # deconstruct reply and stuff into dict
        try:
            status["Pump state"] = reply[0]
            status["In-line valve state"] = reply[1]
            status["Coolant valve state"] = reply[2]
            status["Vent valve state"] = reply[3]
            status["Mode"] = reply[4]
            status["Controller state"] = reply[5]
            return status
        except IndexError:
            raise ValueError(
                "Value Error. Reply does not conform to format. Received: \"{0}\".".format(reply)
            )

    @property
    @command
    def end_vacuum_sp(self):
        """
        Reads the set point (target) for the switch off vacuum in mode Auto
        :return: call back to send_message with a request to return a value
        """
        return self.send_message(self.GET_SWITCHING_OFF_VAC_3, True, self.getanswer)

    @end_vacuum_sp.setter
    @command
    def end_vacuum_sp(self, vacuum=None):
        """
        Sets the switch off vacuum and returns the set point from the pump so the user can verify that it was successful
        :param vacuum: (integer) the target vacuum
        """
        try:
            # type checking of the vacuum the user provided
            vacuum = int(vacuum)
        except ValueError:
            raise (ValueError("Error setting vacuum. Vacuum was not a valid integer \"{0}\"".format(vacuum)))

        # actually sending the command
        reply = self.send_message("{0} {1}".format(self.SET_SWITCHING_OFF_VAC_3, vacuum), True, self.setanswer)
        try:
            reply_value = int(reply[0])
        except ValueError:
            raise (ValueError("Error setting vacuum. Reply was not a valid integer \"{0}\"".format(reply[0])))
        if reply_value != vacuum:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Send: \"{0}\". "
                "Received: \"{1}\".".format(vacuum, reply_value)
            )

    @property
    @command
    def runtime_sp(self):
        """
        Reads the set point (target) for the run time in mode Auto
        :return: call back to send_message with a request to return a value
        """
        return self.send_message(self.GET_RUNTIME_3, True, self.timeanswer)

    @runtime_sp.setter
    def runtime_sp(self, time=None):
        """
        Sets the runtime and returns the set point from the pump so the user can verify that it was successful
        :param time: (integer) the desired runtime
        """
        # type checking the input
        if not self.timepattern.fullmatch(time):  # this is actually too conservative since the pump can deal with integers, but better confine an idiot to a smaller space than let him roam free
            raise (ValueError("Error setting runtime. Runtime did not match the pattern: \"{0}\"".format(time)))

        # actually sending the command
        reply = self.send_message("{0} {1}".format(self.SET_RUNTIME_3, time), True, self.timeanswer)

        if reply[0] != time:
            raise ValueError(
                "Value Error. Vacuum pump did not return correct return code. Send: \"{0}\". "
                "Received: \"{1}\".".format(time, reply[0])
            )

if __name__ == '__main__':
    p = CVC3000(port="COM3")
    p.open_connection()
    p.initialise()
    print("Vacuum sp {}".format(p.vacuum_sp))
    p.vacuum_sp = 200
    print(p.vacuum_sp)
    p.start()
    sleep(2)
    p.stop()
    sleep(2)
    p.vent()
    print(p.query_status())
