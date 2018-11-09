"""
:mod:"Chemputer_Device_API" -- API for Chemputer pumps and valves
===================================

.. module:: Chemputer_Device_API
   :platform: Unix, Windows
   :synopsis: Control Chemputer pumps and valves.
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

This API is intended for controlling a set of Chemputer pumps and valves over a local network.
"""

import logging
import socket
import sys
import threading
import time
import re
from collections import OrderedDict

import modules.pv_api.configs as cfgs

""" CONSTANTS """
TCP_PORT = 5000
BUFFER_SIZE = 1024

RESPOND = "RESPOND: "
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
STALL = "Stall"
DONE = "DONE"
READ_PUMP_CFG = "PUMP_CFG "
READ_VALVE_CFG = "VALVE_CFG "
READ_NETWORK_CFG = "NETCFG "
ERRORS = "ERRORS: "
ADC = "ADC: "
PUMP_CFG = "PUMP"
VALVE_CFG = "VALVE"
NETWORK_CFG = "NETWORK"

KEEPALIVE_COOKIE = "reset_wdt\0"

ip_pattern = re.compile("(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})")

# debug setting
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s ; %(levelname)s ; %(message)s")


def udp_keepalive(udp_host):
    """
    Broadcasts the UDP keepalive signal to ensure the board is still alive

    Args:
        udp_host (Tuple): Tuple containing the IP address and port of the server e.g. (192.168.255.255, 3000)
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Starting UDP keepalive broadcast...")
    while True:
        udp.sendto(KEEPALIVE_COOKIE.encode(), udp_host)
        time.sleep(0.5)


# TODO: Maybe keep the port constant so they only need to provide address and build tuple from that.
def initialise_udp_keepalive(udp_host):
    """
    Starts a thread for the UDP keepalive broadcast to the server

    Args:
        udp_host (Tuple): Tuple containing the IP address and host port of the server.
    """
    if not isinstance(udp_host, tuple):
        print("Failed to launch UDP Keepalive thread.\nParameter is not tuple")
    else:
        udp_thread = threading.Thread(target=udp_keepalive, args=(udp_host,), name="Keepalive thread for subnet {0}".format(udp_host[0]))
        udp_thread.start()


class ChemputerDevice(object):
    """
    API for interfacing with the Chemputer pumps and valves.

    Args:
        address (str): Address of the device
        name (str): Optional name of the device
    """
    def __init__(self, address, name=""):
        self.name = name
        self.address = str(address)
        self.device_cfg = {}
        self.network_cfg = {}
        self.device_ready_flag = threading.Event()

        self.device_type = None

        self.logger = logging.getLogger("main_logger.pv_logger")

        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

        self.tcp_response_thread = threading.Thread(target=self.receive_response, name="{0} TCP thread".format(name))
        self.tcp_response_thread.start()

        """ COMMAND STRINGS """
        # common
        self.READ_CONFIG = "read_config"
        self.WRITE_CONFIG = "write_config"
        self.READ_NETWORK_CONFIG = "read_netcfg"
        self.WRITE_NETWORK_CONFIG = "write_netcfg"
        self.READ_ERRORS = "read_errors"
        self.CLEAR_ERRORS = "clear_errors"
        self.READ_ADC = "read_ADC"

        # pump
        self.MOVE_ABSOLUTE = "move_abs"     # param: speed in uL/min, position in uL (both integers)
        self.MOVE_RELATIVE = "move_rel"     # param: speed in uL/min, volume in uL (both integers)
        self.MOVE_PUMP_HOME = "move_home"   # param: speed in uL/min (integer)
        self.HARD_HOME = "hard_home"        # param: speed in uL/min (integer)

        # valve
        self.AUTO_CONFIG = "cfg"
        self.MOVE_VALVE_HOME = "home"
        self.MOVE_TO_POSITION = "pos"

        """ Default configs """
        self.DEFAULT_PUMP_CONFIG = cfgs.DEFAULT_PUMP_CONFIG
        self.DEFAULT_VALVE_CONFIG = cfgs.DEFAULT_VALVE_CONFIG
        self.DEFAULT_NETWORK_CONFIG = cfgs.DEFAULT_NETWORK_CONFIG

    def __del__(self):
        """
        Destructor that closes the server connection and joins the listening thread
        """
        self.tcp.close()
        try:
            self.tcp_response_thread.join()
        except AttributeError:
            pass

    def connect_to_server(self):
        """
        Attempts to connect to the TCP server.

        Raises:
            Exception (OSException): The connection has failed.
        """
        try:
            self.tcp.connect((self.address, TCP_PORT))
            # self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # turn on the TCP keepalive
            # self.tcp.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 1000, 1000))  # configure to send a keepalive packet every second
        except Exception:
            self.logger.exception("Unable to connect to host device: IP {0} did not respond.".format(self.address))
            sys.exit(1)

    def receive_response(self):
        """
        Received the response from the server and prints out the response to screen.
        Specific cases are present for reading configurations (device/network) and for checking the completion flag.
        """
        while True:
            try:
                response = self.tcp.recv(BUFFER_SIZE).decode()
            except(TimeoutError, ConnectionResetError):
                self.logger.exception("Device {0} has disconnected.".format(self.name))
                break  # TODO raise disconnection error

            # response = self.tcp.recv(BUFFER_SIZE).decode()

            if not response:
                continue

            elif READ_PUMP_CFG in response:
                split = response.split(READ_PUMP_CFG)
                cfg_string = split[1]

                self.device_cfg = self.parse_device_config_string(cfg_string, PUMP_CFG)

                for k, v in self.device_cfg.items():
                    self.logger.debug("{0} {1}".format(k, v))

                self.device_ready_flag.set()
                continue

            elif READ_VALVE_CFG in response:
                split = response.split(READ_VALVE_CFG)
                cfg_string = split[1]

                self.device_cfg = self.parse_device_config_string(cfg_string, VALVE_CFG)

                for k, v in self.device_cfg.items():
                    self.logger.debug("{0} {1}".format(k, v))

                self.device_ready_flag.set()
                continue

            elif READ_NETWORK_CFG in response:
                split = response.split(READ_NETWORK_CFG)
                network_cfg_string = split[1]
                self.network_cfg = self.parse_network_config_string(network_cfg_string)
                for k, v in self.network_cfg.items():
                    self.logger.debug("{0} {1}".format(k, v))
                self.device_ready_flag.set()
                continue

            elif ERRORS in response:
                split = response.split(ERRORS)
                try:
                    error_byte = int(split[1])
                    error_list = []
                    if error_byte & (1 << 1):
                        error_list.append("CONFIGURATION_ERROR")
                    if error_byte & (1 << 2):
                        error_list.append("COMMUNICATION_ERROR")
                    if error_byte & (1 << 3):
                        error_list.append("WATCHDOG_ERROR")
                    if error_byte & (1 << 4):
                        error_list.append("MOTOR_STALL_ERROR")
                    if error_byte & (1 << 5):
                        error_list.append("ACTUATION_ERROR")
                    if error_byte & (1 << 6):
                        error_list.append("SHUTDOWN_ERROR")
                    if error_byte & (1 << 7):
                        error_list.append("UNDEFINED_ERROR")
                    self.logger.debug(error_list)
                    self.device_ready_flag.set()
                except TypeError:
                    self.logger.exception("Invalid response: {0}".format(split[1]))
                continue

            elif ADC in response:
                split = response.split(ADC)
                try:
                    ADC_reading = int(split[1])
                    self.logger.debug("ADC reading: {0}".format(ADC_reading))
                    self.device_ready_flag.set()
                except TypeError:
                    self.logger.exception("Invalid response: {0}".format(split[1]))
                continue

            elif STALL in response:
                self.logger.critical("Error! Device has stalled!")  # TODO maybe raise an error?
                # TODO not sure about the ready flag. Need to think some more.
                # self.device_ready_flag.set()
                continue

            elif SUCCESS in response:
                self.logger.debug(response)

            elif FAILURE in response:
                self.logger.debug(response)
                # TODO not sure about the ready flag. Need to think some more.
                # self.device_ready_flag.set()
                continue

            elif DONE in response:
                self.logger.debug(response)
                self.device_ready_flag.set()

            else:
                self.logger.info(response)
                continue

    def build_command(self, *cmds):
        """
        Builds the command string from a varying list of arguments, adding a null-terminated character

        Args:
            cmds (Variadic): List of commands to create the string.
        """
        cmd_string = ""
        for cmd in cmds:
            cmd_string += (str(cmd) + " ")

        return cmd_string[:-1] + "\0"

    def send_command(self, *cmds):
        """
        Constructs the command string and sends it to the TCP server.

        Args:
            cmds (Variadic): List of commands used to create the string.
        """
        self.device_ready_flag.clear()
        cmd = self.build_command(*cmds)
        try:
            self.tcp.send(cmd.encode())
        except ConnectionResetError:
            self.logger.exception("Device {0} has disconnected.".format(self.name))  # TODO raise connection error

    def convert_network_address_to_list(self, address, split_delimiter):
        """
        Converts a network address to a python list
        Splits the address based off of a delimiter and adds the elements as string to a list

        Args:
            address (str): Address to convert
            split_delimiter (str): Delimiting character used to split the address ("." for IP addresses, ":" for MAC Addresses)

        Returns:
            addr_split (List): List of strings containing the values of the address minus the delimiting character
        """
        addr_split = address.split(split_delimiter)
        for pos, val in enumerate(addr_split):
            if split_delimiter == ":":
                mac_seg = int(val, 16)
                addr_split[pos] = str(mac_seg)
            else:
                addr_split[pos] = val

        return addr_split

    def construct_network_config_string(self, cfg_list):
        """
        Creates the network configuration string from a list of addresses created via convert_network_address_to_list

        Args:
            cfg_list (List): List of lists containing all the addresses

        Returns:
            cfg_string (str): String containing the numbers of the addresses
        """
        cfg_string = ""
        for sublist in cfg_list:
            for elem in sublist:
                cfg_string += (elem + " ")
        return cfg_string[:-1]

    def construct_network_config(self, mac_address, ip_address, subnet_mask, gateway_ip, dns_server_ip, DHCP_mode):
        """
        Constructs the network configuration
        Parses the addresses and joining them into a string of numbers that represent the addresses

        Args:
            mac_address (str): MAC address of the device
            ip_address (str): IP address of the device
            subnet_mask (str): Address f the subnet mask of the network
            gateway_ip (str): Address of the default gateway of the network
            dns_server_ip (str): Address of the DNS server
            DHCP_mode (int): Flag for determining if the device should use static IP allocation (1) or the DHCP allocation (2).

        Returns:
            cfg_string (str): String representing all the addresses as individual numbers
        """
        mac_addr = self.convert_network_address_to_list(mac_address, ":")
        ip_addr = self.convert_network_address_to_list(ip_address, ".")
        subnet_addr = self.convert_network_address_to_list(subnet_mask, ".")
        gateway_addr = self.convert_network_address_to_list(gateway_ip, ".")
        dns_server_addr = self.convert_network_address_to_list(dns_server_ip, ".")
        DHCP_mode = [str(DHCP_mode)]  # sorry for butchering that...

        cfg_list = []
        cfg_list.extend((mac_addr, ip_addr, subnet_addr, gateway_addr, dns_server_addr, DHCP_mode))
        cfg_string = self.construct_network_config_string(cfg_list)

        return cfg_string

    def construct_pump_config(self, config_dict=None):
        """
            Constructs a pump configuration
            Takes a normal (unordered) dictionary with human-readable parameters (e.g. 256 microsteps rather than
            microsteps = 0) and constructs an ordered dict containing all values that need to be sent to the pump in their
            proper order. The process involves three steps: first, the microstep value, the motor profile, number of steps
            per mL and for the entire syringe are worked out based on the information provided, and stored in the
            PUMP_CONFIG dict. Then all keys that have not yet been populated are just transferred over. Third, the new
            dict is ordered by iterating over the key list and sending each item to the end.

            Args:
                config_dict (dict): dictionary containing all necessary information to configure a pump

            Returns:
                PUMP_CONFIG (ordereddict): ordered dictionary ready to be sent to the pump
        """
        if not config_dict:  # TODO find out if a property can be passed as kwarg somehow
            config_dict = self.DEFAULT_PUMP_CONFIG
        
        PUMP_CONFIG = OrderedDict()

        # first, figure out all the "special" items
        try:
            PUMP_CONFIG["microsteps"] = cfgs.MICROSTEP_MAP[config_dict["microsteps"]]
            PUMP_CONFIG["motor_profile"] = cfgs.MOTOR_PROFILE_MAP[config_dict["motor_profile"]]
            PUMP_CONFIG["steps_per_ml"] = int((360 / cfgs.ANGLE_PER_STEP) * config_dict["microsteps"] * (
                cfgs.SYRINGE_VOL_TO_MM[config_dict["syringe_size"]] / cfgs.THREAD_PITCH))
            PUMP_CONFIG["syringe_volume_steps"] = int(PUMP_CONFIG["steps_per_ml"] * config_dict["syringe_size"])
        except KeyError:
            print("error")  # TODO log that

        # then, just fill up the rest
        for item in cfgs.PUMP_CONFIG_ITEMS:
            if item not in PUMP_CONFIG.keys():
                PUMP_CONFIG[item] = int(config_dict[item])  # the int() function casts booleans to integers

        # finally, sort the items in the right order
        for item in cfgs.PUMP_CONFIG_ITEMS:
            try:
                PUMP_CONFIG.move_to_end(item)
            except KeyError:
                print("error")  # TODO log that

        return PUMP_CONFIG

    def construct_valve_config(self, config_dict=None):
        """
            Constructs a valve configuration


            Args:
                config_dict (dict): dictionary containing all necessary information to configure a valve

            Returns:
                VALVE_CONFIG (ordereddict): ordered dictionary ready to be sent to the valve
        """
        if not config_dict:
            config_dict = self.DEFAULT_VALVE_CONFIG
        
        VALVE_CONFIG = OrderedDict()

        # first, figure out all the "special" items
        try:
            VALVE_CONFIG["microsteps"] = cfgs.MICROSTEP_MAP[config_dict["microsteps"]]
            VALVE_CONFIG["motor_profile"] = cfgs.MOTOR_PROFILE_MAP[config_dict["motor_profile"]]
            VALVE_CONFIG["full_revolution"] = int((360 / cfgs.ANGLE_PER_STEP) * config_dict["microsteps"])
            VALVE_CONFIG["clearing_distance"] = int(
                VALVE_CONFIG["full_revolution"] / (2 * config_dict["number_of_positions"]))
        except KeyError:
            print("error")  # TODO log that

        # then, just fill up the rest
        for item in cfgs.VALVE_CONFIG_ITEMS:
            if item not in VALVE_CONFIG.keys():
                VALVE_CONFIG[item] = int(config_dict[item])  # the int() function casts booleans to integers

        # finally, sort the items in the right order
        for item in cfgs.VALVE_CONFIG_ITEMS:
            try:
                VALVE_CONFIG.move_to_end(item)
            except KeyError:
                print("error")  # TODO log that

        return VALVE_CONFIG

    def parse_device_config_string(self, cfg_string, cfg_type):
        """
        Parses the config string message and sets the appropriate values in the relevant dictionary

        Args:
            cfg_string (str): String representing the configuration
            cfg_type (str): Type of configuration to parse into (Pump/Valve/Network)

        Returns:
            config (OrderedDict): Configuration of the device/network

        Raises:
            Exception: Unable to parse the configuration string
        """
        str_split = cfg_string.split(" ")

        if cfg_type == cfgs.PUMP_TYPE:
            PUMP_CONFIG = dict(zip(cfgs.PUMP_CONFIG_ITEMS, str_split))
            return PUMP_CONFIG

        if cfg_type == cfgs.VALVE_TYPE:
            VALVE_CONFIG = dict(zip(cfgs.VALVE_CONFIG_ITEMS, str_split))
            return VALVE_CONFIG

        raise Exception("Unable to parse configuration string!")

    def parse_network_config_string(self, cfg_string):
        """
        Parses the network configuration string for the relevant information
        Hardcoded values should not change but a fix will be implemented to make it a bit more robust

        Args:
            cfg_string (str): String representing the network information

        Returns:
            network_config (OrderedDict): Ordered Dictionary containing all the network information
        """
        cfg_split = cfg_string.split(" ")

        self.DEFAULT_NETWORK_CONFIG["mac_address"] = cfg_split[0]
        self.DEFAULT_NETWORK_CONFIG["ip_address"] = cfg_split[1]
        self.DEFAULT_NETWORK_CONFIG["gateway_ip"] = cfg_split[2]
        self.DEFAULT_NETWORK_CONFIG["subnet_mask"] = cfg_split[3]
        self.DEFAULT_NETWORK_CONFIG["dns_server_ip"] = cfg_split[4]
        self.DEFAULT_NETWORK_CONFIG["dhcp_flag"] = int(cfg_split[5])

        return self.DEFAULT_NETWORK_CONFIG

    def convert_list_to_address(self, addr_list, mac=False):
        """
        Converts a list into an address
        Will also convert the decimal mac address into the appropriate hex format

        Args:
            addr_list (List): List containing the elements of the address
            mac (bool): Flag for determining if the address is a mac address

        Returns:
            addr (str): The string representation of the address
        """
        addr = ""
        for elem in addr_list:
            if mac:
                mac_seg = hex(int(elem)).strip("0x").upper()
                addr += (mac_seg + ":")
            else:
                addr += (elem + ".")
        return addr[:-1]

    def wait_until_ready(self):
        """
        Waits until the device is ready by listening for a DONE command from the server.
        This then sets the flag that the operation has completed.
        """
        # set = self.device_ready_flag.is_set()  # TODO statement seems to have no effect
        self.device_ready_flag.wait()
        time.sleep(0.1)

    def send_and_wait_reply(self, msg):
        """
        Debug method for sending arbitrary strings to the server.

        Args:
            msg (str): Message to send
        """
        self.send_command(msg)

    ################################### PUMPS & VALVES ##############################################
    def read_device_configuration(self):
        """ Reads the device configuration from the server and displays it back to the user """
        self.send_command(self.READ_CONFIG)
        self.device_ready_flag.wait()

    def read_network_configuration(self):
        """ Reads the network configuration for the device from the server and displays it back to the user """
        self.send_command(self.READ_NETWORK_CONFIG)
        self.device_ready_flag.wait()

    def write_network_configuration(self, mac_address, ip_address, subnet_mask, gateway_ip, dns_server_ip, DHCP_mode=1):
        """
        Creates the network configuration for the device and sends it to the server.

        Args:
            mac_address (str): MAC address of the device
            ip_address (str): IP Address of the device
            subnet_mask (str):  Address of the subnet mask of the network
            gateway_ip (str): Address of the default gateway of the network
            dns_server_ip (str): Address of  the DNS server
            DHCP_mode (int): Flag for determining if the device should use static IP allocation (1) or the DHCP allocation (2). Default is 1
        """
        network_cfg = self.construct_network_config(mac_address, ip_address, subnet_mask, gateway_ip, dns_server_ip, DHCP_mode)
        self.send_command(self.WRITE_NETWORK_CONFIG, network_cfg)
        self.device_ready_flag.wait()

    def assign_ip_address(self, ip_address):
        """
        High-level method to assign a new IP to a device. Constructs a standard MAC from the provided IP and sends over
        the entire network config.

        Args:
            ip_address (str): new IP Address of the device
        """
        if not re.fullmatch(ip_pattern, ip_address):
            raise ValueError("Supplied address {0} is not a valid IP!".format(ip_address))

        ip_ending = re.match(ip_pattern, ip_address).group(4)

        if self.device_type == "pump":
            mac_address = "0A:{0}:B0:0B:5A:55".format(ip_ending)
        elif self.device_type == "valve":
            mac_address = "1A:{0}:B0:0B:5A:55".format(ip_ending)
        else:
            raise TypeError("Unknown device type!")

        network_cfg = self.construct_network_config(
            mac_address=mac_address,
            ip_address=ip_address,
            subnet_mask=cfgs.DEFAULT_NETWORK_CONFIG["subnet_mask"],
            gateway_ip=cfgs.DEFAULT_NETWORK_CONFIG["gateway_ip"],
            dns_server_ip=cfgs.DEFAULT_NETWORK_CONFIG["dns_server_ip"],
            DHCP_mode=cfgs.DEFAULT_NETWORK_CONFIG["dhcp_flag"]
        )
        self.send_command(self.WRITE_NETWORK_CONFIG, network_cfg)
        self.device_ready_flag.wait()

    def read_errors(self):
        """ Reads error flags from the server """
        self.send_command(self.READ_ERRORS)
        self.device_ready_flag.wait()

    def clear_errors(self):
        """ Clears the previously set errors """
        self.send_command(self.CLEAR_ERRORS)
        self.device_ready_flag.wait()

    def read_ADC(self):
        """ Reads ADC """
        self.send_command(self.READ_ADC)
        self.device_ready_flag.wait()

    ###################################################################################################

    # TODO implement some sort of check whether the device is a pump or valve, and disallow the wrong commands outright


    ################################### PUMPS ##############################################
class ChemputerPump(ChemputerDevice):
    """
    Child class of ChemputerDevice. Gives the user control over the pump commands

    Args:
        address (str): Address of the pump
        name (str): Optional name of the device
    
    Extends:
        ChemputerDevice
    """
    def __init__(self, address, name=""):
        ChemputerDevice.__init__(self, address, name)
        self.device_type = "pump"

    def move_relative(self, volume_in_milliliters, speed_in_milliliters_per_min):
        """
        Moves the plunger to a specific volume relative to the current position

        Args:
            volume_in_milliliters (int): Volume to move in milliliters
            speed_in_milliliters_per_min (int): Speed to move in milliliters per minute
        """
        self.logger.debug("Pump {0} is moving by {1}mL at {2}mL/min.".format(self.name, volume_in_milliliters, speed_in_milliliters_per_min))
        volume_in_microliters = int(float(volume_in_milliliters) * 1000)
        speed_in_microliters_per_min = int(float(speed_in_milliliters_per_min) * 1000)
        self.send_command(self.MOVE_RELATIVE, volume_in_microliters, speed_in_microliters_per_min)

    def move_absolute(self, target_volume_in_milliliters, speed_in_milliliters_per_min):
        """
        Moves the plunger to a set volume, regardless of current position

        Args:
            target_volume_in_milliliters (int): Target volume to move in milliliters
            speed_in_milliliters_per_min (int): Speed to move in milliliters per minute
        """
        self.logger.debug("Pump {0} is moving to {1}mL at {2}mL/min.".format(self.name, target_volume_in_milliliters, speed_in_milliliters_per_min))
        target_volume_in_microliters = int(float(target_volume_in_milliliters) * 1000)
        speed_in_microliters_per_min = int(float(speed_in_milliliters_per_min) * 1000)
        self.send_command(self.MOVE_ABSOLUTE, target_volume_in_microliters, speed_in_microliters_per_min)

    def move_to_home(self, speed_in_milliliters_per_min):
        """
        Moves the plunger to the home position

        Args:
            speed_in_milliliters_per_min (int): Speed to move in milliliters per minute
        """
        self.logger.debug("Pump {0} is homing at {1}mL/min.".format(self.name, speed_in_milliliters_per_min))
        speed_in_microliters_per_min = int(float(speed_in_milliliters_per_min) * 1000)
        self.send_command(self.MOVE_PUMP_HOME, speed_in_microliters_per_min)

    def hard_home(self, speed_in_milliliters_per_min=50):
        """
        Finds the home position by stalling the plunger against the base, then backing up a number of steps.

        Args:
            speed_in_milliliters_per_min (int): Speed to move in milliliters per minute
        """
        speed_in_microliters_per_min = int(float(speed_in_milliliters_per_min) * 1000)
        if speed_in_microliters_per_min >= 35000:  # slower speeds don't really work
            self.send_command(self.HARD_HOME, speed_in_microliters_per_min)
        else:
            self.logger.critical("Error. Supplied speed too low!")

    def write_default_pump_configuration(self):  # TODO make another method that allows writing an arbitrary config
        """
        Writes a default configuration for the pump to the server
        This uses the default configuration (OrderedDict) laid out in the default_configs script
        """
        default_cfg = self.construct_pump_config()
        pump_cfg = [val for val in default_cfg.values()]
        self.send_command(self.WRITE_CONFIG, *pump_cfg)
        self.device_ready_flag.wait()

    ########################################################################################


    ################################### VALVES ##############################################
class ChemputerValve(ChemputerDevice):
    """
    Child class of the ChemputerDevice. Gives the user control over the valve commands

    Args:
        address (str): Address of the valve
        name (str): Optional name for the device.

    Extends:
        ChemputerDevice
    """
    def __init__(self, address, name=""):
        ChemputerDevice.__init__(self, address, name)
        self.device_type = "valve"

    def auto_config(self):
        """
        Generates an automatic configuration for the valve device
        """
        self.send_command(self.AUTO_CONFIG)

    def move_home(self):
        """
        Moves the valve to its home position
        """
        self.send_command(self.MOVE_VALVE_HOME)
    
    def move_to_position(self, position):
        """
        Moves the valve to a specific position

        Args:
            position (int/str): Position to move to
        """
        self.send_command(self.MOVE_TO_POSITION, position)

    def write_default_valve_configuration(self):
        """
        Writes a default configuration for the valve to the server
        This uses the default configuration (OrderedDict) laid out in the default_configs script
        """
        default_cfg = self.construct_valve_config()
        valve_cfg = [val for val in default_cfg.values()]
        self.send_command(self.WRITE_CONFIG, *valve_cfg)
        self.device_ready_flag.wait()

    #########################################################################################
