# coding=utf-8
# !/usr/bin/env python
"""
:mod:"camera_execution" -- Mid-level hack to change camera recording speed
===================================

.. module:: sticamera_executionrrer_execution
   :platform: Windows
   :synopsis: Mid-level hack to change camera recording speed.
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2018 The Cronin Group, University of Glasgow

This class provides a method to change the frame rate of a video log which may or may be recorded. This is accomplished
by logging messages at a level below DEBUG containing the requested recording speed (in multiples of real time). The
beauty of this approach is that a) most of the complicated message passing is handled by the logging module, and b) if
no recording is running, the workings of this module are entirely without consequence because all other loggers reject
this level.

For style guide used see http://xkcd.com/1513/
"""

import logging


class CameraExecutioner(object):
    """
    Class to change camera recording speed

    TODO: add try/except statements to catch calls to unsupported methods!
    """
    def __init__(self):
        """
        Initialiser for the CameraExecutioner class
        """
        self.logger = logging.getLogger("main_logger.camera_logger")
        self.logger.setLevel(5)

    def change_recording_speed(self, recording_speed):
        """
        Method to change the camera recording speed. This method simply logs a message at level 5 (below DEBUG), which
        may or may not be intercepted by an appropriate vlogging handler.

        Args:
            recording_speed (int): Requested recording speed (in multiples of real time speed)
        """
        if recording_speed >= 1:
            self.logger.log(level=5, msg=recording_speed)
        else:
            pass  # TODO maybe raise a ValueError or something
