# coding=utf-8
# !/usr/bin/env python
"""
:mod:"hardware_sim" -- Collection of classes to simulate the operation of various hardware devices
===================================

.. module:: hardware_sim
   :platform: Windows
   :synopsis: Classes to simulate chemputer hardware.
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This file provides a number of simulation classes that behave like the real
control classes, but mostly just log the commands rather than actually doing anything.

For style guide used see http://xkcd.com/1513/
"""

import logging


class SimDevice(object):
    def __init__(self):
        self.logger = logging.getLogger("main_logger.sim_logger")


class SimChemputerPump(SimDevice):
    def __init__(self, address, name):
        super().__init__()
        self.logger.info('Received Pump \"{0}\" Address: {1}'.format(name, address))
        self.name = name

    def move_relative(self, volume_ul, speed_ul):
        self.logger.debug('Pump \"{0}\" - Moving relative. Volume: {1} Speed: {2}'.format(self.name, volume_ul, speed_ul))

    def move_absolute(self, volume_ul, speed_ul):
        self.logger.debug('Pump \"{0}\" - Moving absolute. Volume: {1} Speed: {2}'.format(self.name, volume_ul, speed_ul))

    def move_to_home(self, speed_ul):
        self.logger.debug('Pump \"{0}\" - Moving home: Speed: {1}'.format(self.name, speed_ul))

    def wait_until_ready(self):
        self.logger.debug('Pump \"{0}\" - Waiting until ready...'.format(self.name))

    
class SimChemputerValve(SimDevice):
    def __init__(self, address, name):
        super().__init__()
        self.logger.info('Received Valve \"{0}\" Address: {1}'.format(name, address))
        self.name = name

    def move_home(self):
        self.logger.debug('Valve \"{0}\" - Moving to home position.'.format(self.name))

    def move_to_position(self, position):
        self.logger.debug('Valve \"{0}\" - Moving to position {1}'.format(self.name, position))
        
    def wait_until_ready(self):
        self.logger.debug('Valve \"{0}\" - Waiting until ready...'.format(self.name))

    
class SimIKARET(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received IKARET Port: {0}'.format(port))

    def start_stirrer(self):
        self.logger.info('IKARET - Starting stirrer')

    def start_heater(self):
        self.logger.info('IKARET - Starting heater')

    def stop_stirrer(self):
        self.logger.info('IKARET - Stopping stirrer')

    def stop_heater(self):
        self.logger.info('IKARET - Stopping heater')

    def temperature_setter(self, temp):
        self.logger.info('IKARET - Temperaure set to: {0}'.format(temp))

    def stir_rate_setter(self, stir_rate):
        self.logger.info('IKARET - Stir rate set to: {0}'.format(stir_rate))


class SimUSBswitch(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received USB switch port: {0}'.format(port))

    def start_stirrer(self):
        self.logger.info('usbswitch - Starting stirrer')

    def stop_stirrer(self):
        self.logger.info('usbswitch - Stopping stirrer')


class SimIKARV(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Recevied IKARV port: {0}'.format(port))

    def initialise(self):
        self.logger.info('IKARV - Initialising')

    def start_heater(self):
        self.logger.info('IKARV - Starting Heater')
    
    def stop_heater(self):
        self.logger.info('IKARV - Stopping Heater')

    def start_rotation(self):
        self.logger.info('IKARV - Starting Rotations')

    def stop_rotation(self):
        self.logger.info('IKARV - Stopping roations')

    def lift_up(self):
        self.logger.info('IKARV - Lifting arm')

    def lift_down(self):
        self.logger.info('IKARV - Lifting arm down')

    def reset_rotavap(self):
        self.logger.info('IKARV - Resetting rotavap')

    @property
    def temperature_sp(self):
        self.logger.info('IKARV - Temperature: GIEF TEMP ༼ つ ◕_◕ ༽つ')
    
    @temperature_sp.setter
    def temperature_sp(self, temp):
        self.logger.info('IKARV - Temperature set to {0}'.format(temp))

    @property
    def rotation_speed_sp(self):
        self.logger.info('IKARV - Speed: GIEF SPEED ༼ つ ◕_◕ ༽つ')
    
    @rotation_speed_sp.setter
    def rotation_speed_sp(self, speed):
        self.logger.info('IKARV - Speed set to {0}'.format(speed))

    def set_interval_sp(self, interval=None):
        self.logger.info('IKARV - Interval set to {0}'.format(interval))


class SimCVC3000(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received CVC3000 port: {0}'.format(port))

    def initialise(self):
        self.logger.info('CVC3K - Initialising')  

    @property
    def vacuum_sp(self):
        self.logger.info('CVC3K - GIEF SP ༼ つ ◕_◕ ༽つ')

    @vacuum_sp.setter
    def vacuum_sp(self, sp):
        self.logger.info('CVC3k - Set SP to {0}'.format(sp))

    def start(self):
        self.logger.info('CVC3k - Starting vacuum')

    def stop(self):
        self.logger.info('CVC3K - Stopping Vacuum')

    def vent(self):
        self.logger.info('CVC3K - Venting vacuum')

    def query_status(self):
        self.logger.info('CVC3K - Status is ༼ つ ◕_◕ ༽つ')

    @property
    def end_vacuum_sp(self):
        self.logger.info('CVC3K - GIEF END SP ༼ つ ◕_◕ ༽つ')
    
    @end_vacuum_sp.setter
    def end_vacuum_sp(self, sp):
        self.logger.info('CVC3K - End SP set to {0}'.format(sp))

    @property
    def runtime_sp(self):
        self.logger.info('CVC3K - GIEF RUNTIME SP ༼ つ ◕_◕ ༽つ')

    @runtime_sp.setter
    def runtime_sp(self, sp):
        self.logger.info('CVC3K - Runtime sp set to {0}'.format(sp))


class SimJULABOCF41(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received Julabo CF41 port: {0}'.format(port))

    def start(self):
        self.logger.info('Julabo CF41 - Starting operation')

    def stop(self):
        self.logger.info('Julabo CF41 - Stopping operation')

    def set_temperature(self, temp):
        self.logger.info('Julabo CF41 - Temperature sp set to {0}'.format(temp))

    def set_cooling_power(self, cooling_power=100):
        if cooling_power < 0 or cooling_power > 100:
            raise ValueError("ERROR: supplied value {0} is outside the limits (0..100)!".format(cooling_power))
        else:
            self.logger.info('Julabo CF41 - Cooling power set to set to {0}'.format(cooling_power))


class SimHuber(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received Huber port: {0}'.format(port))

    def start(self):
        self.logger.info('Huber - Starting operation')

    def stop(self):
        self.logger.info('Huber - Stopping operation')

    def set_temperature(self, temp):
        self.logger.info('Huber - Temperature sp set to {0}'.format(temp))

    def set_ramp_duration(self, ramp_duration):
        self.logger.info('Huber - Ramp duration set to {0}'.format(ramp_duration))

    def start_ramp(self, temp):
        self.logger.info('Huber - Starting ramp to {0}°C'.format(temp))


class SimRZR2052(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received RZR 2052 port: {0}'.format(port))

    @property
    def stir_rate_sp(self):
        self.logger.info("RZR 2052 - GIEF SP ༼ つ ◕_◕ ༽つ")

    @stir_rate_sp.setter
    def stir_rate_sp(self, rpm):
        self.logger.info('RZR 2052 - Setting RPM to {0}'.format(rpm))

    def start_stirrer(self):
        self.logger.info('RZR 2052 - Starting operation')

    def stop_stirrer(self):
        self.logger.info('RZR 2052 - Stopping operation')


class SimIKAmicrostar(SimDevice):
    def __init__(self, port):
        super().__init__()
        self.logger.info('Received IKA microstar port: {0}'.format(port))

    @property
    def stir_rate_sp(self):
        self.logger.info("IKA microstar - GIEF SP ༼ つ ◕_◕ ༽つ")

    @stir_rate_sp.setter
    def stir_rate_sp(self, rpm):
        self.logger.info('IKA microstar - Setting RPM to {0}'.format(rpm))

    def start_stirrer(self):
        self.logger.info('IKA microstar - Starting operation')

    def stop_stirrer(self):
        self.logger.info('IKA microstar - Stopping operation')
