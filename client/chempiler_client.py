# coding=utf-8
# !/usr/bin/env python

"""
:mod:"chempiler_client" -- User interface for the Chempiler
===================================

.. module:: chempiler_client
   :platform: Windows, Unix
   :synopsis: User interface for the Chempiler
.. moduleauthor:: Graham Keenan <1105045k@student.gla.ac.uk>
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

This module sets up a logging framework, then prompts the user to supply paths to GraphML and ChASM files.
Once the input has been verified, the Chempiler is started.

For style guide used see http://xkcd.com/1513/
"""

import inspect
import logging
import multiprocessing
import os
import sys
import time

import click

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..', 'platform_server'))

from core.chempiler import Chempiler

__all__ = ['main']


@click.command()
@click.option('-e', '--experiment-code', required=True)
@click.option('-g', '--graph', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='GraphML file. Example: C:\\Users\\group\\Documents\\Chempiler\\experiments\\graph\\chemputer_rig_3_sildena/fil.graphml')
@click.option('-c', '--command', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='Command file. Example: C:\\Users\\group\\Documents\\Chempiler\\experiments\\ChASM\\sildenafil.chasm')
@click.option('--log-folder', type=click.Path(file_okay=False, dir_okay=True), required=True)
@click.option('--record-video', is_flag=True)
@click.option('--crash-dump', is_flag=True)
@click.option('--simulation', is_flag=True)
def main(experiment_code, graph, command, log_folder, record_video, crash_dump, simulation):
    """Run the chemputer."""
    # deal with logging
    # create main thread logger
    logger = logging.getLogger("main_logger")
    logger.setLevel(logging.DEBUG)

    # create file handler which logs all messages
    fh = logging.FileHandler(filename=os.path.join(log_folder, "{0}.txt".format(experiment_code)))
    fh.setLevel(logging.DEBUG)

    # create console handler which logs all messages
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # create formatter and add it to the handlers
    file_formatter = logging.Formatter("%(asctime)s ; %(levelname)s ; %(module)s ; %(threadName)s ; %(message)s")
    fh.setFormatter(file_formatter)
    console_formatter = logging.Formatter("%(asctime)s ; %(module)s ; %(message)s")
    ch.setFormatter(console_formatter)

    # add the handlers to the loggers
    logger.addHandler(fh)
    logger.addHandler(ch)

    # record the entered parameters
    logger.debug("User Input:\nXML file: {0}\nCommand file: {1}\nSimulation: {2}".format(graph, command, SIM))

    # deal with video recording
    if record_video:
        from tools.vlogging import VlogHandler, RecordingSpeedFilter, recording_worker

        # spawn queues
        message_queue = multiprocessing.Queue()
        recording_speed_queue = multiprocessing.Queue()

        # create logging message handlers
        video_handler = VlogHandler(message_queue)
        recording_speed_handler = VlogHandler(recording_speed_queue)

        # set logging levels
        video_handler.setLevel(logging.INFO)
        recording_speed_handler.setLevel(5)  # set a logging level below DEBUG

        # only allow dedicated messages for the recording speed handler
        speed_filter = RecordingSpeedFilter()
        recording_speed_handler.addFilter(speed_filter)

        # attach the handlers
        logger.addHandler(video_handler)
        logger.addHandler(recording_speed_handler)

        # work out video name and path
        i = 0
        video_path = os.path.join(log_folder, "{0}_{1}.avi".format(experiment_code, i))
        while True:
            # keep incrementing the file counter until you hit one that doesn't yet exist
            if os.path.isfile(video_path):
                i += 1
                video_path = os.path.join(log_folder, "{0}_{1}.avi".format(experiment_code, i))
            else:
                break

        # launch recording process
        recording_process = multiprocessing.Process(target=recording_worker,
                                                    args=(message_queue, recording_speed_queue, video_path))
        recording_process.start()
        time.sleep(5)  # wait for the video feed to stabilise

    chempiler = Chempiler(graph, command, crash_dump=crash_dump, simulation=simulation)
    chempiler.run_platform()
    return sys.exit(0)


if __name__ == "__main__":
    main()
