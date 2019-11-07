# coding=utf-8
# !/usr/bin/env python
"""
:mod:"serial_labware" -- Generic base class for communicating with lab equipment via serial connection
===================================

.. module:: serial_labware
   :platform: Windows
   :synopsis: Generic base class to control lab equipment via serial.
.. moduleauthor:: Cronin Group 2017

(c) 2017 The Cronin Group, University of Glasgow

This provides a generic python class for safe serial communication
with various lab equipment over serial interfaces (RS232, RS485, USB)
by sending command strings. This parent class handles establishing
a connection as well as sending and receiving commands.
Based on code originally developed by the Cronin Group.

For style guide used see http://xkcd.com/1513/
"""

# system imports
import platform
import threading
import re
from queue import Queue
from functools import wraps
from time import time, sleep

# additional module imports
import serial
import logging


def command(func):
    """
    Decorator for command_set execution. Checks if the method is called in the same thread as the class instance,
    if so enqueues the command_set and waits for a reply in the reply queue. Else it concludes it must be the command
    handler thread and actually executes the method. This way methods in the child classes need to be written
    just once and decorated accordingly.
    :return: decorated method
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        device_instance = args[0]
        if threading.get_ident() == device_instance.current_thread:
            command_set = [func, args, kwargs]
            device_instance.command_queue.put(command_set)
            while True:
                if not device_instance.reply_queue.empty():
                    return device_instance.reply_queue.get()
        else:
            return func(*args, **kwargs)

    return wrapper


class SerialDevice:
    """
    This is a generic parent class handling serial communication with lab equipment. It provides
    methods for opening and closing connections as well as a keepalive. It works by spawning a
    daemon thread which periodically checks a queue for commands. If no commands are enqueued,
    a keepalive method is executed periodically. Replies are put in their own reply queue where
    they can be retrieved at any time.
    """
    def __init__(self, port=None, device_name=None, soft_fail_for_testing=False):
        """
        Initializer of the SerialDevice class
        :param str port: The port name/number of the serial device
        :param str device_name: A descriptive name for the device, used mainly in debug prints.
        :param bool soft_fail_for_testing: (optional) determines if an invalid serial port raises an error or merely
            logs a message. Default: Off
        """
        # note down current thread number
        self.current_thread = threading.get_ident()
        # implement class logger
        self.logger = logging.getLogger("main_logger.serial_device_logger")
        # spawn queues
        self.command_queue = Queue()
        self.reply_queue = Queue()
        # DEBUG testing switch, to allow soft-fails instead of exceptions
        self.__soft_fail_for_testing = soft_fail_for_testing
        # check if the port passed is of the correct format
        if platform.system() == "Windows":
            try:
                if port[0:3] == "COM" and int(port[3:]) > 0:
                    self.port = port
                else:
                    # allowing for soft fail in test modes, this will allow an outer script to continue, even if an
                    # invalid port was passed
                    if not self.__soft_fail_for_testing:
                        # in normal use raise an exception to make surrounding python scrips stop
                        raise (ValueError("The port number ({0}) is not a valid serial port!".format(port)))
                    else:
                        # soft-fail error message
                        self.logger.debug("ERROR: The specified serial port is not valid: {0}".format(port))
            except (AttributeError, ValueError) as e:
                # self.logger.debug a more descriptive error message before re-raising the exception
                self.logger.debug("ERROR: The specified serial port is not valid: {0}".format(e))
                # raising the exception again so the surrounding script is aware that this failed
                raise  # raises the last exception again
        else:
            # TODO ADD port consistency checks for posix operating systems
            raise (OSError(
                "You are running a currently unsupported operating system: \"{0}\"".format(platform.system())
            ))

        # device name
        self.device_name = device_name

        # syntax of a returned answer, to be overridden by child classes
        self.answer_pattern = re.compile("(.*)")  # any number of any character, in one group

        # initialise last time (for non blocking wait
        self.last_time = time()

        # serial parameters, to be overridden by child classes
        self.__connection = None
        self.command_termination = '\r\n'
        self.standard_encoding = 'UTF-8'

        self.baudrate = 9600
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = 1
        self.xonxoff = False
        self.rtscts = False
        self.write_timeout = None
        self.dsrdtr = False
        self.inter_byte_timeout = None

        self.write_delay = 0  # delay in seconds before sending a command
        self.read_delay = 0  # delay in seconds after sending a command

    def __command_handler_daemon(self):
        """
        Daemon thread for relaying any commands to the device. The "possession" of the serial port and therefore
        any actual communication with the device is relegated to its own thread, partially to free up the main
        thread for more important stuff, partially to allow for implementation of watchdog keepalive calls,
        which would be tremendously tricky to do from the main thread.

        This private function polls the command_queue for any commands to send. If no commands are queued,
        a keepalive method is executed. Any replies received from the device are enqueued into reply_queue for
        further processing.
        """
        while True:
            try:
                if not self.command_queue.empty():
                    command_item = self.command_queue.get()
                    method = command_item[0]
                    arguments = command_item[1]
                    keywordarguments = command_item[2]
                    reply = method(*arguments, **keywordarguments)
                    self.reply_queue.put(reply)
                else:
                    self.keepalive()
            except ValueError as e:
                # workaround if something goes wrong with the serial connection
                # future me will certainly not hate past me for this...
                self.logger.critical(e)
                self.__connection.flush()
                # thread-safe purging of both queues
                while not self.command_queue.empty():
                    self.command_queue.get()
                while not self.reply_queue.empty():
                    self.reply_queue.get()

    def launch_command_handler(self):
        command_handler = threading.Thread(target=self.__command_handler_daemon, name="{0}_command_handler".format(self.device_name), daemon=True)
        command_handler.start()

    @command
    def open_connection(self):
        """
        Opens the serial connection to the device.
        If a connection is already open it is closed and then a connection is re-established with the current settings
        """
        if self.__connection is not None and self.__connection.isOpen():
            self.logger.debug("Already connected. Closing connection and re-establishing with parameters given.")
            self.close_connection()
            self.__connection = None

        try:
            self.__connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts,
                write_timeout=self.write_timeout,
                dsrdtr=self.dsrdtr,
                inter_byte_timeout=self.inter_byte_timeout
            )
            return True  # announce success
        except (AttributeError, FileNotFoundError, serial.SerialException) as e:
            # allowing for soft fail in test modes, this will allow an outer script to continue, even if an
            # invalid port was passed
            if not self.__soft_fail_for_testing:
                # in normal use just raise exception again
                raise
            else:
                # soft-fail error message
                self.logger.debug("ERROR: The connection to the serial device could not be established: {0}".format(e))
                return False  # announce failure

    @command
    def close_connection(self):
        """
        Attempts to close the serial connection if one is open.
        """
        if self.__connection is not None:
            self.__connection.close()
            return True  # announce success
        else:
            return False  # announce failure

    def send_message(self, message, get_return=False, return_pattern=None, multiline=False):
        """
        Method for sending messages to the device. This method needs to be publicly accessible, otherwise
        child classes can't use it. This method does not do a consistency check on the arguments passed to it,
        since they may vary wildly. Therefore such a check must be performed before calling send_message!

        Args:
            message (str): The message string. No checks are performed on the message and it is just passed on
            get_return (bool): Are you expecting a return message?
            return_pattern (_sre.SRE_Pattern): Passes on a regex pattern to check the returned message against
            multiline (bool): Are you expecting a return message spanning multiple lines?
                (not evaluated if get_return is False)

        Returns:
            (conditional)
            - returns "True" if no message is expected back
            - does a call back to "__receive_message" and passes on "the return pattern"
            - returns -1 if send message fails
        """
        # send the message and encode it according to the standard settings found in __init__
        # Hint: "{}".format(message) auto converts message to string in case it was something else, so no type checking
        if self.__connection is not None:
            try:
                sleep(self.write_delay)
                # self.__connection.flush()  # get rid of shite from the last transmission
                self.__connection.write(
                    "{0}{1}".format(message, self.command_termination).encode(self.standard_encoding)
                )
                sleep(self.read_delay)
            except Exception as e:
                if not self.__soft_fail_for_testing:
                    # just raise the exception again when not in test mode
                    raise
                else:
                    self.logger.debug("Error: Unexpected error while writing to serial. Error Message: {0}".format(e))

            # if the user specified that a return message is expected
            if get_return:
                # call back to __receive_message and passing on of the expected regex pattern
                return self.__receive_message(return_pattern=return_pattern, multiline=multiline)
            else:
                # just return True of no response is expected
                return True
        else:
            self.logger.debug("Could not send message: no connection to serial device established.")
            return -1

    def __receive_message(self, return_pattern=None, multiline=False):
        """
        Protected member function that is the sole responsible for actually receiving messages from the device.
            This isn't exactly the pythonic way of doing thing (protected member functions should be _ not __).
            However, two leading __ actually prevents the function to be called from the outside (as opposed to just
            raising a flag says "you're accessing a protected member function".
        Pro-Tip: (due to Python weirdness) A savvy user can still gain access to thus protected functions via
            {InstanceName}._{ClassName}__{FunctionName}

        Args:
            return_pattern (_sre.SRE_Pattern): Passes on a regex pattern to check the returned message against
            multiline (bool): Are you expecting a return message spanning multiple lines?

        Returns:
            answer (str or list of str): If no return pattern is specified, the stripped answer string is returned. If
                a pattern is passed, a list of the captured groups is returned instead
        """
        try:
            # checking if a connection is there
            if self.__connection is not None:
                # if multiple lines are expected, keep reading lines until no more lines come in
                if multiline:
                    answer = ""
                    while True:
                        line = self.__connection.readline()
                        if line:
                            answer += line.decode(self.standard_encoding)
                        else:
                            break
                # if just one line is expected, just read one line (faster than always waiting for the timeout)
                else:
                    answer = self.__connection.readline()
                    # decoding the answer using the standard settings from __init__
                    answer = answer.decode(self.standard_encoding)

                # if the user wants a code check performed
                if return_pattern is not None:
                    if type(return_pattern).__name__ != "SRE_Pattern":
                        raise ValueError(
                            "The return code you specified was not a valid regular expression: {0}".format(return_pattern)
                        )

                    if re.fullmatch(pattern=return_pattern, string=answer):
                        # if the answer matches the desired pattern return the read value
                        return re.match(pattern=return_pattern, string=answer).groups()
                    else:
                        self.logger.critical(
                            "Value Error. Serial device did not return correct return code. Send: \"{0}\". "
                            "Received: \"{1}\".".format(return_pattern, answer)
                        )
                        if self.__soft_fail_for_testing:
                            return answer.strip()
                        else:
                            raise ValueError(
                                "Value Error. Serial device did not return correct return code. Send: \"{0}\". "
                                "Received: \"{1}\".".format(return_pattern, answer)
                            )
                else:
                    # if no return code checking was requested, just return the read value
                    return answer.strip()
            else:
                raise Exception("Error. No connection to the device")
        except Exception as e:
            # This is not very elegant, but lets the user know that the device failed while retaining the error
            # information
            raise Exception("Serial device message receive failed. Error Message: {0}\n{1}".format(e, e.__traceback__))

    def non_blocking_wait(self, callback, interval):
        """
        Simple non-blocking wait function crafted after the Arduino Blink Without Delay example. Checks whether the
        time elapsed since the last callback is greater than or equal to the interval. If so, the callback method
        is returned and the time updated.
        :param callback: function or method to be executed
        :param int interval: wait time in seconds
        :return: callback if interval has elapsed, None otherwise
        """
        if time() >= (self.last_time + interval):
            self.last_time = time()
            return callback()
        else:
            return None

    def keepalive(self):
        """
        Dummy keepalive method. This is just a stand-in for whatever keepalive operation needs to be performed
        on the device, meant to be overridden in the actual child class.
        """
        pass
