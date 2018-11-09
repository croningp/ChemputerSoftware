"""
:mod:"pump_setup" -- Quick setup script for Chemputer Pumps
===================================

.. module:: pump_setup
   :platform: Windows
   :synopsis: Quick setup script for Chemputer Pumps
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

This script is called once after programming a pump device. It will send the required network config via serial, then
send the default pump config via network and finally execute a hard homing, followed by a move to 1mL and back to home
to excercise the device and make sure everything is ok.
"""

import logging
import serial
from time import sleep

from modules.pv_api.Chemputer_Device_API import initialise_udp_keepalive, ChemputerPump

""" CONSTANTS """
com_port = "COM17"
ip_ending = 24

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s ; %(levelname)s ; %(message)s")


def convert_network_address_to_list(address, split_delimiter):
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


def construct_network_config_string(cfg_list):
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


def construct_network_config(mac_address, ip_address, subnet_mask, gateway_ip, dns_server_ip, DHCP_mode):
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
    mac_addr = convert_network_address_to_list(mac_address, ":")
    ip_addr = convert_network_address_to_list(ip_address, ".")
    subnet_addr = convert_network_address_to_list(subnet_mask, ".")
    gateway_addr = convert_network_address_to_list(gateway_ip, ".")
    dns_server_addr = convert_network_address_to_list(dns_server_ip, ".")
    DHCP_mode = [str(DHCP_mode)]  # sorry for butchering that...

    cfg_list = []
    cfg_list.extend((mac_addr, ip_addr, subnet_addr, gateway_addr, dns_server_addr, DHCP_mode))
    cfg_string = construct_network_config_string(cfg_list)

    return cfg_string

network_cfg = construct_network_config(
    mac_address="00:{0}:B0:0B:5A:55".format(ip_ending),
    ip_address="192.168.1.{0}".format(ip_ending),
    subnet_mask="255.255.0.0",
    gateway_ip="192.168.1.1",
    dns_server_ip="192.168.255.255",
    DHCP_mode=1
)

print(network_cfg)

serial_connection = serial.Serial(port=com_port, baudrate=19200)
# serial_connection.open()
serial_connection.write(("write_netcfg " + network_cfg + "\n").encode())

sleep(0.5)
print(serial_connection.read_all().decode())

sleep(5)

initialise_udp_keepalive(("192.168.255.255", 3000))

sleep(0.5)

p = ChemputerPump("192.168.1.{0}".format(ip_ending), "Leeroy Jenkins")

sleep(0.5)

p.write_default_pump_configuration()

sleep(1)

p.clear_errors()
p.hard_home(50)
p.wait_until_ready()

sleep(0.5)

p.move_absolute(1, 50)
p.wait_until_ready()

sleep(0.5)

p.move_to_home(50)

print("Setup SUCCESSFUL!")
