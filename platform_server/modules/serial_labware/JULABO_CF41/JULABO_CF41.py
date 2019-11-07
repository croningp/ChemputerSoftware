# coding=utf-8
# !/usr/bin/env python
"""
:mod:"JULABO_CF41" -- API for Julabo CF41 remote controllable recirculation chiller
===================================

.. module:: JULABO_CF41
   :platform: Windows
   :synopsis: Control Julabo CF41 recirculation chiller
.. moduleauthor:: Cronin Group 2017

(c) 2017 The Cronin Group, University of Glasgow

This provides a python class for the Julabo CF41 recirculation chiller. Command implementation is based on the manual
version 1.951.4871-V3 downloaded from the Julabo homepage. Nota bene: the chiller needs a null modem cable!

For style guide used see http://xkcd.com/1513/
"""

# system imports
import serial
import os
import sys
import inspect
from time import sleep

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

# additional module imports
from SerialDevice.serial_labware import SerialDevice, command


class JULABOCF41(SerialDevice):
    """
    This provides a python class for the JULABO CF41 chiller
    """
    def __init__(self, port=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the JULABOCF41 class

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
        self.baudrate = 9600
        self.bytesize = serial.SEVENBITS
        self.parity = serial.PARITY_EVEN
        self.rtscts = True

        self.write_delay = 0.25
        self.read_delay = 0.1

        # answer patterns
        # TODO: compile a few

        # DOCUMENTED COMMANDS for easier maintenance

        self.OUT_MODE_01 = "OUT_MODE_01"
        # Use working temperature   
        # Parameter 0, >Setpoint1<
        # Parameter 1, >Setpoint2<
        # Parameter 2, >Setpoint3<

        self.OUT_MODE_02 = "OUT_MODE_02"
        # parameter = 0, Selftuning „off“.
        # Temperature control by using the stored parameters.
        # parameter = 1, Selftuning „once“ Single selftuning of
        # controlled system after the next start.
        # parameter = 2, Selftuning „always“ Continual selftuning
        # of controlled system whenever a new setpoint is to be reached.

        self.OUT_MODE_03 = "OUT_MODE_03"
        # parameter = 0, Set external programmer input to voltage.
        # Voltage 0 V ... 10 V
        # parameter = 1, Set external programmer input to current.
        # Current 0 mA ... 20 mA

        self.OUT_MODE_04 = "OUT_MODE_04"
        # parmaeter = 0, Temperature control of internal bath.
        # parameter = 1, External control with Pt100 sensor.

        self.OUT_MODE_05 = "OUT_MODE_05"
        # parameter = 0, Stop the unit = R –OFF-.
        # parameter = 1, Start the unit.

        self.OUT_MODE_08 = "OUT_MODE_08"
        # parameter = 0, Set the control dynamics - aperiodic
        # parameter = 1, Set the control dynamics - standard

        self.OUT_SP_00 = "OUT_SP_00"
        # parameter = xxx.xx, Set working temperature. „Setpoint 1“
        
        self.OUT_SP_01 = "OUT_SP_01"
        # parameter = xxx.xx, Set working temperature. „Setpoint 2“
        
        self.OUT_SP_02 = "OUT_SP_02"
        # parameter = xxx.xx, Set working temperature. „Setpoint 3“
        
        self.OUT_SP_03 = "OUT_SP_03"
        # parameter = xxx.xx, Set high temperature warning limit „OverTemp“
        
        self.OUT_SP_04 = "OUT_SP_04"
        # parameter = xxx.xx, Set low temperature warning limit „SubTemp“

        self.OUT_SP_07 = "OUT_SP_07"
        # parameter = 1..4, Set the pump pressure stage.

        self.OUT_HIL_00 = "OUT_HIL_00"
        # parameter = -xxx, Set the desired maximum cooling power (0 % to 100 %).
        # Note: Enter the value with a preceding negative sign!
        # This command only valid with the CF41.

        self.OUT_HIL_01 = "OUT_HIL_01"
        # parameter = xxx, Set the desired maximum
        # heating power (10 % to 100 %).

        self.VERSION = "VERSION"
        # parameter = None, Number of software version (V X.xx)

        self.STATUS = "STATUS"
        # paramter = None, Status message, error message (see page 75)

        self.IN_PV_00 = "IN_PV_00"
        # paramter = None, Actual bath temperature.

        self.IN_PV_01 = "IN_PV_01"
        # parameter = None, Heating power being used (%).
        
        self.IN_PV_02 = "IN_PV_02"
        # parameter = None, Temperature value registered by the external Pt100 sensor.
        
        self.IN_PV_03 = "IN_PV_03"
        # parameter = None, Temperature value registered by the safety sensor.

        self.IN_PV_04 = "IN_PV_04"
        # parameter = None, Setpoint temperature („SafeTemp“)
        # of the excess temperature protection

        self.IN_SP_00 = "IN_SP_00"
        # parameter = None, Working temperature „Setpoint 1“

        self.IN_SP_01 = "IN_SP_01"
        # parameter = None, Working temperature „Setpoint 2“

        self.IN_SP_02 = "IN_SP_02"
        # parameter = None, Working temperature „Setpoint 3“

        self.IN_SP_03 = "IN_SP_03"
        # parameter = None, High temperature warning limit „OverTemp“

        self.IN_SP_04 = "IN_SP_04"
        # parameter = None, Low temperature warning limit „SubTemp“

        self.IN_MODE_01 = "IN_MODE_01"
        # parameter = None, Selected setpoint:0 = Setpoint 1
        # 1 = Setpoint 2 2 = Setpoint 3

        self.IN_MODE_02 = "IN_MODE_02"
        # parameter = None, Selftuning type: 0 = Selftuning „off“
        # 1 = Selftuning „once“, 2 = Selftuning „alway“

        self.IN_MODE_03 = "IN_MODE_03"
        # parameter = None, Type of the external programmer input:
        # 0 = Voltage 0 V to 10 V, 1 = Current 0 mA to 20 mA

        self.IN_MODE_04 = "IN_MODE_04"
        # parameter = None, Internal/external temperature control:
        # 0 = Temperature control with internal sensor.
        # 1 = Temperature control with external Pt100 sensor.

        self.IN_MODE_05 = "IN_MODE_05"
        # parameter = None, Cryo-Compact Circulator in Stop/Start condition:
        # 0 = Stop, 1 = Start

        self.IN_MODE_08 = "IN_MODE_08"
        # parameter = None, Adjusted control dynamics
        # 0 = aperiodic, 1 = standard

        self.IN_HIL_00 = "IN_HIL_00"
        # parameter = None, Max. cooling power (%).

        self.IN_HIL_01 = "IN_HIL_01"
        # parameter = None,  Max. heating power (%).

        self.status_messages = {
            '00 MANUAL STOP': 'Cryo-Compact Circulator in „OFF“ state.',
            '01 MANUAL START': 'Cryo-Compact Circulator in keypad control mode.',
            '02 REMOTE STOP': 'Cryo-Compact Circulator in „r OFF“ state.',
            '03 REMOTE START': 'Cryo-Compact Circulator in remote control mode.',
        }

        self.error_messages = {
            '-01 LOW LEVEL ALARM': 'Low liquid level alarm',
            '-03 EXCESS TEMPERATURE WARNING': 'High temperature warning',
            '-04 LOW TEMPERATURE WARNING': 'Low temperature warning.',
            '-05 WORKING SENSOR ALARM': 'Working temperature sensor short-circuited or interrupted.',
            '-06 SENSOR DIFFERENCE ALARM': 'Sensor difference alarm. Working temperature and safety sensors report a temperature difference of more than 35 K.',
            '-07 I2C-BUS ERROR': 'Internal error when reading or writing the I2C bus.',
            '-08 INVALID COMMAND': 'Invalid command.',
            '-09 COMMAND NOT ALLOWED IN CURRENT OPERATING MODE': 'Invalid command in current operating mode.',
            '-10 VALUE TOO SMALL': 'Entered value too small.',
            '-11 VALUE TOO LARGE': 'Entered value too large.',
            '-12 TEMPERATURE MEASUREMENT ALARM': 'Error in A/D converter.',
            '-13 WARNING : VALUE EXCEEDS TEMPERATURE LIMITS': 'Value lies outside the adjusted range for the high and low temperature warning limits. But value is stored.',
            '-14 EXCESS TEMPERATURE PROTECTOR ALARM': 'Excess temperature protector alarm',
            '-15 EXTERNAL SENSOR ALARM': 'External control selected, but external Pt100 sensor not connected.',
            '-20 WARNING: CLEAN CONDENSOR OR CHECK COOLING WATER CIRCUIT OF REFRIGERATOR': 'Cooling of the condenser is affected. Clean air-cooled condenser. Check the flow rate and cooling water temperature on water-cooled condenser.',
            '-21 WARNING: COMPRESSOR STAGE 1 DOES NOT WORK': 'Compressor stage 1 does not work.',
            '-26 WARNING: STAND-BY PLUG IS MISSING': 'External standby contact is open. (see page 57and 70)',
            '-33 SAFETY SENSOR ALARM': 'Excess temperature sensor short-circuited or interrupted.',
            '-38 EXTERNAL SENSOR SETPOINT PROGRAMMING ALARM': 'Ext. Pt100 sensor input without signal and setpoint programming set to external Pt100.',
            '-40 NIVEAU LEVEL WARNUNG': 'Low liquid level warning in the internal reservoir.',
        }

        self.launch_command_handler()

        if connect_on_instantiation:
            self.open_connection()

    @command
    def set_temperature(self, temp, setpoint=0):
        """
        Sets the target temperature of the chiller by default using first setpoint parameter

        Args:
            temp (float): Temperature setpoint
            setpoint (int): Which of the three distinct setpoints (0..2) is to be set
        """
        # setting the setpoint
        if setpoint == 0:
            self.send_message('{} {}'.format(self.OUT_SP_00, round(temp, 2)), False)
        elif setpoint == 1:
            self.send_message('{} {}'.format(self.OUT_SP_01, round(temp, 2)), False)
        elif setpoint == 2:
            self.send_message('{} {}'.format(self.OUT_SP_02, round(temp, 2)), False)
        else:
            raise ValueError('The set point should be in range 0..2')
            
        # Using working from set point
        self.send_message('{} {}'.format(self.OUT_MODE_01, setpoint), False)

    @command
    def set_cooling_power(self, cooling_power=100):
        """
        Sets the target temperature of the chiller by default using first setpoint parameter

        Args:
            cooling_power (int): Desired cooling power in % (range 0..100)
        """
        # for some incomprehensible reason the number has to be set with a preceding "-"
        if cooling_power < 0 or cooling_power > 100:
            raise ValueError("ERROR: supplied value {0} is outside the limits (0..100)!".format(cooling_power))
        else:
            cooling_power = -cooling_power

        # Using working from set point
        self.send_message('{} {}'.format(self.OUT_HIL_00, cooling_power), False)

    @command
    def start(self):
        """Starts the chiller"""
        self.send_message('{} {}'.format(self.OUT_MODE_05, 1), False)

    @command
    def stop(self):
        """Stops the chiller"""
        self.send_message('{} {}'.format(self.OUT_MODE_05, 0), False)

    @command
    def get_temperature(self):
        """Reads the current temperature of the bath"""
        return float(self.send_message(self.IN_PV_00, True))

    @command
    def get_setpoint(self):
        """Reads the current temperature setpoint"""
        setpoint_used = self.send_message(self.IN_MODE_01, True)  # check which of the three setpoints is in use
        if setpoint_used == "0":
            return float(self.send_message(self.IN_SP_00, True))
        elif setpoint_used == "1":
            return float(self.send_message(self.IN_SP_01, True))
        elif setpoint_used == "2":
            return float(self.send_message(self.IN_SP_02, True))
        else:
            self.logger.critical("ERROR! Setpoint query returned {0} which is not a recognised setpoint!".format(setpoint_used))

    @command
    def get_status(self):
        """ Returns the status of the chiller"""
        status = self.send_message(self.STATUS, True)
        return status


if __name__ == '__main__':
    chiller = JULABOCF41('COM5', 'chiller', True, False)

    chiller.start()
    chiller.set_temperature(60.0)
    for i in range(10):
        sleep(1)
        print(chiller.get_temperature)
    print(chiller.get_status())
    chiller.stop()
