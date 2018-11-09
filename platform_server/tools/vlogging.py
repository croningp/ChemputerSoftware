# coding=utf-8
# !/usr/bin/env python
"""
:mod:"vlogging" -- Utilities for video logging
===================================

.. module:: vlogging
   :platform: Windows
   :synopsis: Utilities for video logging.
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2018 The Cronin Group, University of Glasgow

This file contains all utilities required to record webcam videos at variable frame rates, with time stamp, and the
current INFO level log message overlaid.

For style guide used see http://xkcd.com/1513/
"""

import logging
import time
import multiprocessing
import numpy as np
import cv2


class VlogHandler(logging.Handler):
    """
    Logging module handler class. Inherits directly from the logging.Handler prototype, as no fancy stuff is required.
    """
    def __init__(self, queue=None):
        """
        Initialize the handler.

        Args:
            queue (multiprocessing.Queue): A queue object shared with the video recording process.
        """
        super().__init__()
        if queue:
            self.queue = queue
        else:
            raise Exception("ERROR: No queue object supplied!")

    def flush(self):
        """
        Empties the queue by popping all items until it's empty.
        """
        self.acquire()
        try:
            while not self.queue.empty():
                self.queue.get()
        finally:
            self.release()

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then put into the queue.
        """
        try:
            msg = self.format(record)
            # print("Logger {0} is enqueuing \"{1}\"".format(self.name, msg))
            self.queue.put(msg)

        except Exception:
            self.handleError(record)


class RecordingSpeedFilter(logging.Filter):
    """
    Logging filter that only allows messages with logging level 5 to be passed on. Used for controlling video recording
    speed.
    """
    def filter(self, record):
        return record.levelno == 5


def recording_worker(message_queue, recording_speed_queue, video_path):
    """
    Worker process which records a video to a file at variable frame rate. The main loop grabs an image from the camera,
    overlays a time stamp and the most recent log message, and then waits the appropriate time until the next frame is
    due. Log messages and requests to change recording speed are passed via multiprocessing queues. This worker is meant
    to be run as an individual process to improve performance in cPython.

    Args:
        message_queue (multiprocessing.Queue): A queue object containing logging messages
        recording_speed_queue (multiprocessing.Queue): A queue object containing requests to change frame rate
        video_path (str): A path to the output video file
    """
    # constants for easy maintenance
    camera_id = 1
    resolution = (1280, 720)
    fps = 24
    time_per_frame = 1 / fps

    # start capture
    cap = cv2.VideoCapture(camera_id)

    # set image size
    cv2.VideoCapture.set(cap, cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cv2.VideoCapture.set(cap, cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    # start video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(video_path, fourcc, fps, resolution)

    # initialise working variables
    recording_speed = 1
    current_log_message = ""

    # keep recording
    while cap.isOpened():
        try:
            beginning_of_frame = time.time()
            ret, frame = cap.read()
            if ret:
                # create and format time stamp
                timestamp = time.localtime(beginning_of_frame)
                timestamp_pretty_print = time.strftime("%Y-%m-%d %H:%M:%S", timestamp)
                timestamp_string = "{0} {1}X".format(timestamp_pretty_print, recording_speed)

                # check if there is a new log message, if there's more than one discard all but the most recent one
                while not message_queue.empty():
                    current_log_message = message_queue.get()

                # insert time stamp and log message as overlay
                cv2.putText(frame, timestamp_string, (10, 660), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, current_log_message, (10, 710), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

                # write the frame
                out.write(frame)

                # display video
                # cv2.imshow('frame', frame)
            else:
                break

            # wait until the next frame is due
            while (time.time() - beginning_of_frame) < (time_per_frame * recording_speed):
                # if a speed change is requested end the wait immediately
                if not recording_speed_queue.empty():
                    recording_speed = recording_speed_queue.get()
                    recording_speed = int(recording_speed)
                    break
                # else wait for a couple dozen milliseconds to save CPU time
                else:
                    time.sleep(0.005)

        except EOFError:
            cap.release()
            out.release()
            cv2.destroyAllWindows()
            return -1
