# THIS USES PYTHON 3

# TASKER
# ROBERT WOLTERMAN (xtacocorex)
# CODE TO HANDLE RUNNING TASKS AT PRE-DETERMINED INTERVALS

# MODULE IMPORT
import threading
import datetime
import time
import subprocess
import shlex
import logging

# LOGGER HANDLER
NAME = "ESCAPE ROOM"
logger = logging.getLogger(NAME)

# CLASS
class Tasker(threading.Thread):
    """
    Tasker - Class to handle running tasks at specific times from when it's started
    Inherits: threading
    """
    def __init__(self, tasks, loop_sleep = 0.5, debug = False):
        # SINCE WE'RE INHERITING THREAD, WE HAVE TO INIT THAT ALSO
        threading.Thread.__init__(self)
        # SET DAEMON
        self.daemon = True
        # SET CLASS VARIABLES
        self.tasks = tasks
        self.start_time = None
        self.loop_sleep = loop_sleep
        self.debug = debug
        self.dead = False
        # CREATE DELTA TIME OBJECTS
        self._create_delta_times()
        # PRE-PROCESS COMMANDS FOR EASY USE LATER
        self._process_commands()

        logger.info("TASKER CREATED")

    def is_running(self):
        # THIS FUNCTION IS USED TO TELL THE PARENT THAT IT'S RUNNING
        # IT RETURNS THE OPPOSIDE OF self.dead AS IF WE'RE DEAD
        # WE WANT TO RETURN FALSE
        return not self.dead

    def _create_delta_times(self):
        # THIS FUNCTION ADDS A DELTA TIME OBJECT TO THE TASK LIST
        # TO HAVE THAT REFERENCE PRE-BUILD BEFORE THE TASKS ARE
        # STARTED
        # THIS ALSO ADDS A RUN BOOLEAN
        for task in self.tasks:
            unit = task["TIME UNITS"].lower()
            dtraw = task["DELTA TIME FROM START"]
            td = None
            if unit == "microseconds":
                td = datetime.timedelta(microseconds = dtraw)
            elif unit == "milliseconds":
                td = datetime.timedelta(milliseconds = dtraw)
            elif unit == "seconds":
                td = datetime.timedelta(seconds = dtraw)
            elif unit == "minutes":
                td = datetime.timedelta(minutes = dtraw)
            elif unit == "hours":
                td = datetime.timedelta(hours = dtraw)
            # TODO: THINK ABOUT DAYS AND WEEKS, THOSE MAY BE A TAD EXCESSIVE
            # ADD td TO THE DICTIONARY
            task["TD"] = td

    def _process_commands(self):
        # THIS FUNCTION PRE-BUILDS THE COMMANDS FROM THE COMMAND STRING
        # FED IN BY THE TASK LIST
        for task in self.tasks:
            task["ARGS"] = shlex.split(task["COMMAND"])
            # ADD NEW KEY TO LOCAL CONFIG FOR IF COMMAND WAS RUN OR NOT
            task["RUN"] = False

    def kill(self):
        # KILL THE STUFF, THIS MOSTLY WORKS MOST OF THE TIME
        logging.info("TASKER KILLED")
        self.dead = True

    def run(self):
        # CAPTURE START TIME
        self.start_time = datetime.datetime.now()

        logger.info("TASKER STARTED")
        #logger.debug(self.start_time)
        # LOOP FOREVER - UNTIL WE'RE KILLED
        while not self.dead:
            # GET CURRENT TIME
            now = datetime.datetime.now()
            # LOOP THROUGH TASKS
            for task in self.tasks:
                # IF WE HAVEN'T RUN THE TASK AND THE TIME DELTA BETWEEN NOW AND 
                # START IS GREATER THAN OR EQUAL TO THE CURRENT TASK DELTA
                if not task["RUN"] and now - self.start_time >= task["TD"]:
                    # FLAG THE TASK AS RUN NOW
                    task["RUN"] = True
                    # HANDLE TYPE OF TASK
                    if task["TYPE"].upper() == "TASK":
                        if not self.debug:
                            p = subprocess.Popen(task["ARGS"])
                        else:
                            # DEBUG
                            logger.debug(task["ARGS"])
                    elif task["TYPE"].upper() == "STOP":
                        logger.info("AUTO STOPPING PER TASK LIST")
                        self.dead = True
            # LOOP SLEEPER - NOT SURE IF THIS IS NEEDED AT THE MOMENT
            time.sleep(self.loop_sleep)

# UNIT TEST
if __name__ == "__main__":

    FORMAT = '%(asctime)-15s %(levelname)-10s %(module)-12s %(message)s'
    logging.basicConfig(format=FORMAT)

    logger.info("UNIT TEST")

    TASKLIST = [
      {
      "TYPE" : "TASK",
      "DELTA TIME FROM START" : 1.5,
      "TIME UNITS" : "SECONDS",
      "COMMAND" : "/bin/vikings -input eggs.txt -output \"spam spam.txt\" -cmd \"echo '$MONEY'\""
      },
      {
      "TYPE" : "TASK",
      "DELTA TIME FROM START" : 2.23,
      "TIME UNITS" : "SECONDS",
      "COMMAND" : "vlc red_nosed_reindeer.mp3"
      },
      {
      "TYPE" : "STOP",
      "DELTA TIME FROM START" : 3.23,
      "TIME UNITS" : "SECONDS",
      "COMMAND" : ""
      }
    ]

    tasky = Tasker(TASKLIST)
    logger.info(tasky.tasks)

    # RUN AND WAIT FOR IT TO AUTO STOP
    tasky.run()
