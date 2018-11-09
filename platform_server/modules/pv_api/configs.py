from collections import OrderedDict

########################################################################################################################
#                                                                                                                      #
# Default configurations for Chemputer Devices                                                                         #
#                                                                                                                      #
########################################################################################################################

# Default values for pump and valve configurations
DEFAULT_PUMP_CONFIG = {
    "microsteps": 256,
    "positive_direction": 1,
    "motor_profile": "Longs_17HS0417",
    "motor_off_after_move": True,
    "accel_steps": 2560,
    "accel_resolution": 256,
    "home_position": 700,
    "home_far_window": 1000,
    "backlash_compensation": 100,
    "starting_frequency": 3400,
    "syringe_size": 50
}

DEFAULT_VALVE_CONFIG = {
    "microsteps": 256,
    "positive_direction": -1,
    "home_magnet_direction": -1,
    "number_of_positions": 6,
    "motor_profile": "Longs_23HS0420",
    "motor_off_after_move": True,
    "accel_steps": 512,
    "accel_resolution": 128,
    "positive_threshold": 2700,
    "negative_threshold": 1800,
    "blanking_steps": 256,
    "starting_frequency": 5000,
    "travel_frequency": 70000
}

# Default network configuration for CroninDevices
DEFAULT_NETWORK_CONFIG = OrderedDict()
DEFAULT_NETWORK_CONFIG["mac_address"] = "1A:99:B0:0B:5A:55"
DEFAULT_NETWORK_CONFIG["ip_address"] = "192.168.1.99"
DEFAULT_NETWORK_CONFIG["subnet_mask"] = "255.255.0.0"
DEFAULT_NETWORK_CONFIG["gateway_ip"] = "192.168.1.1"
DEFAULT_NETWORK_CONFIG["dns_server_ip"] = "192.168.255.255"
DEFAULT_NETWORK_CONFIG["dhcp_flag"] = 1

########################################################################################################################
#                                                                                                                      #
# Boilerplate options for config assembly and parsing                                                                  #
#                                                                                                                      #
########################################################################################################################

# Maps the number of microsteps for the pumps to their numerical value
MICROSTEP_MAP = {
    256: 0,
    128: 1,
    64: 2,
    32: 3,
    16: 4,
    8: 5,
    4: 6,
    2: 7,
    1: 8
}

# Maps the syringe size to the number of millimeters to move
SYRINGE_VOL_TO_MM = {
    5: 12,
    10: 6,
    25: 2.44,
    50: 1.2,
    100: 1.2
}

# Maps motor profile names to their sequence number
MOTOR_PROFILE_MAP = {
    "Longs_17HS0417": 0,
    "Longs_23HS0420": 1
}

# Additional motor parameters
ANGLE_PER_STEP = 1.8
THREAD_PITCH = 4

# List of items required for a config in their respective order
PUMP_CONFIG_ITEMS = [
    "microsteps",               # uint8_t
    "positive_direction",       # int8_t
    "motor_profile",            # uint8_t
    "motor_off_after_move",     # int8_t
    "accel_steps",              # uint16_t
    "accel_resolution",         # uint16_t
    "home_position",            # uint16_t
    "home_far_window",          # uint16_t
    "backlash_compensation",    # uint16_t
    "syringe_volume_steps",     # uint32_t
    "steps_per_ml",             # uint32_t
    "starting_frequency"        # uint32_t
]

VALVE_CONFIG_ITEMS = [
    "microsteps",               # uint8_t
    "positive_direction",       # int8_t
    "home_magnet_direction",    # int8_t
    "number_of_positions",      # uint8_t
    "motor_profile",            # uint8_t
    "motor_off_after_move",     # int8_t
    "accel_steps",              # uint16_t
    "accel_resolution",         # uint16_t
    "positive_threshold",       # uint16_t
    "negative_threshold",       # uint16_t
    "clearing_distance",        # uint16_t
    "blanking_steps",           # uint16_t
    "starting_frequency",       # uint32_t
    "travel_frequency",         # uint32_t
    "full_revolution"           # uint32_t
]

# Keywords for parsing
PUMP_TYPE = "PUMP"
VALVE_TYPE = "VALVE"
