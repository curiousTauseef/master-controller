# THIS USES PYTHON 3

# ESCAPE ROOM MASTER CONTROL
# FRAMEWORK LAID OUT BY ROBERT WOLTERMAN (xtacocorex)

# MODULE IMPORTS
import argparse
import json
import http.server
import socketserver
import urllib.parse
import socket
import threading
import datetime
import time
import signal
import sys
import logging
# LOCAL MODULES
import tasker

# CONSTANTS
ANYHOST = ""
WEBPORT = 8080
NAME = "ESCAPE ROOM"
FORMAT = '%(asctime)-15s %(levelname)-10s %(module)-12s %(message)s'

# LOGGING
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(NAME)
logger.setLevel(logging.DEBUG)

# GLOBALS
sevent = threading.Event()

# CLASSES
class LoopingTimer:
    """
    LoopingTimer - CLASS THAT IMPLEMENTS A LOOPING TIMER
    # HAT TIP TO:
    # https://stackoverflow.com/questions/12435211/python-threading-timer-repeat-function-every-n-seconds
    """
    def __init__(self, interval, func_to_run, immediate_fire=False):
        logger.info("LOOPING TIMER CREATED")
        self.interval = interval
        self.func = func_to_run
        self.timer = threading.Timer(self.interval, self._handle)
        self.immediate_fire = immediate_fire

    def _handle(self):
        # RUN FUNCTION
        self.func()
        self.timer = threading.Timer(self.interval, self._handle)
        self.timer.start()

    def start(self):
        if self.immediate_fire:
            self.func()
        self.timer.start()

    def cancel(self):
        self.timer.cancel()


class WebControlHandler(http.server.SimpleHTTPRequestHandler):
    # HAT TIP TO: https://codereview.stackexchange.com/questions/112222/web-server-to-switch-gpio-pin
    # MODIFIED FOR PYTHON 3 AND FOR REMOVING GPIO

    # OVERLOADED FUNCTION
    def do_GET(self):

        # PARSE THE URL
        urlcomp = urllib.parse.urlparse(self.path) # split url in components
        query = urllib.parse.parse_qs(urlcomp.query) # Get args as dictionary
        # LOOK FOR QUERY INFO
        try:
            cmd = query['cmd']
        except KeyError:
            message = "<p>NO COMMANDS PROCESSED</p>"
        else:
            message = "<p></p>"
            if cmd == ["start"]:
                self.server.start_has_been_pushed = True
                # ONLY RUN CALLBACK IF NO TASKS ARE RUNNING
                if not self.server.tasks_running:
                    self.server.run_callback()
                    message = "<p>SCRIPT STARTED</p>"
                else:
                    message = "<p>SCRIPT IS ALREADY RUNNING</p>"
            elif cmd == ["stop"]:
                message = "<p>FEATURE NOT IMPLEMENTED</p>"
            else:
                message = "<p>UNKNOWN ACTION {}</p>".format(cmd.upper())
        # Build links whatever the action was
        message += """<p>
                      <a href="/control.html?cmd=start">START EVERYTHING</a>
                      </p><p>
                      <a href="/control.html?cmd=stop">STOP EVERYTHING</a>
                      </p>"""
        self.send_response(200)
        # Custom headers, if need be
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        # Custom body
        self.wfile.write(str.encode(message))


class WebControl(socketserver.TCPServer):

    # WE KINDA WANT TO BE A DAEMON
    daemon_threads = True
    # FASTER BINDING
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, callback=None):
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.callback = callback
        self.start_has_been_pushed = False
        self.tasks_running = False

    def run_callback(self):
        if self.callback:
            self.callback()

    def set_tasks_running(self, running):
        self.tasks_running = running

    def has_start_been_pushed(self):
        return self.start_has_been_pushed


class ControllerHandler(socketserver.BaseRequestHandler):
    """
    ControllerHandler - Class to handle receiving data from the clients
    """

    # OVERLOAD THE SETUP
    def setup(self):
        logger.debug("CONTROLLER HANDLER CREATED")

    # OVERLOAD THE HANDLE FUNCTION
    def handle(self):
        # STRIP EXTRA STUFF AND MAKE IT LOWERCASE
        data = self.request[0]
        # FIGURE OUT WHO THIS IS FROM - GET JUST THE IP
        sender = self.client_address[0]

        # FIGURE OUT IF THE DATA IS A PONG
        # NOTE: THIS LOOKS GOOFY, BUT CONTROLLER HANDLER WILL BE PASSED
        # INTO CONTROLLER SERVER AND CAN ACCESS THE PARENT CLASS MEMBER VARIABLES
        if data == self.server.PONG:
            # SEND THE IP INTO THE SERVER FUNCTION TO SET CONNECTED
            logger.info("PONG RECEIVED FROM: {0}".format(sender))
            self.server.set_client_connected(sender)
            # IF WE ARE ABLE TO AUTO START AND EVERYTHING IS CONNECTED
            if not self.server.started and self.server.get_start_auto() and self.server.all_connected:
                logger.info("AUTO STARTING ALL CLIENTS")
                self.server.start_all()
        else:
            logger.info(data.upper())


class Controller(socketserver.UDPServer):
    """
    Controller
     - This code handles control of all connected clients
     - Runs any tasks the master controller is responsible for 
    """

    # WE KINDA WANT TO BE A DAEMON
    daemon_threads = True
    # FASTER BINDING
    allow_reuse_address = True

    # CLASS CONSTANTS
    START_AUTO = "AUTO"
    START_BUTTON = "GPIO"
    START_WEB = "WEB"

    # STUFF FOR DETERMINING CONNECTION
    PING = str.encode("ping")
    PONG = str.encode("pong")
    START = str.encode("start")

    def __init__(self, server_address, RequestHandlerClass, config, gpio=None, debug=False):
        socketserver.UDPServer.__init__(self, server_address, RequestHandlerClass)
        # STORE OUR CONFIG SO WE CAN KEEP TRACK OF THINGS
        self.config = config
        # LOCAL INSTANCE OF GPIO LIBRARY
        # THIS CAN BE USED IF ONE WANTS AN ACTUAL BUTTON TO START
        self.gpio = gpio
        # TASKER DEBUG
        self.debug = debug
        # VARIABLE TO LET US KNOW IF ALL CLIENTS HAVE CONNECTED
        self.all_connected = False
        # VARIABLE TO LET US KNOW IF WE'VE STARTED
        self.started = False
        # ARE WE DONE WITH TASKS
        self.done_with_tasks = False

        # RUN THE STUFF TO ENHANCE THE DICTIONARY
        self._update_local_config()

        # CREATE THE TASKER INSTANCE FOR THE CONTROLLER
        # WE WON'T START UNTIL ALL CLIENTS HAVE CONNECTED
        self.tasky = tasker.Tasker(self.config["TASKS"], debug=self.debug)

        # CREATE OUR LOOPING TIMER - WE WANT IT TO IMMEDATELY RUN THE COMMAND
        self.looper = LoopingTimer(self.config["PING TIMER"], self.send_ping, True)
        self.looper.start()

        # WEB CONTROL
        self.webcontrol = WebControl((ANYHOST, WEBPORT), WebControlHandler, callback=self.start_all)
        self.web_thread = threading.Thread(target=self.webcontrol.serve_forever)
        self.web_thread.start()

    def kill(self):
        # THIS IS HERE TO KILL THE LOOPING TIMER
        self.looper.cancel()

    # TODO: THINK ABOUT BUTTON CONTROL - CAN USE A GPIO THAT HANDLES
    # EVENT DETECTION TO RUN A CALLBACK THAT CAN START THE STUFF
    # IF ONE WANTED TO USE THE CALLBACK TO ALSO STOP, A NEW COMMAND
    # WOULD HAVE TO BE ADDED TO SEND TO THE CLIENT
    # AND TELL THEM TO STOP

    def get_tasks_completed(self):
        return self.done_with_tasks

    def reset(self):
        # FUNCTION TO RESET THE CLIENT FOR ANOTHER GO
        logger.info("RESET")
        self.done_with_tasks = False
        self.tasky = tasker.Tasker(self.config["TASKS"], debug=self.debug)

    def _update_local_config(self):
        # THIS FUNCTION ADDS A CONNECTED KEY TO THE DICTIONARY
        # SO WE CAN KEEP TRACK WHO IS CONNECTED
        for client in self.config["CLIENTS"]:
            client["CONNECTED"] = False
            client["ADDRESS"] = (client["IP"], client["PORT"])
    
    def set_client_connected(self, ip):
        # THIS FUNCTION IS USED TO SET A SPECIFIC CLIENT THAT IT'S BEEN CONNECTED
        for client in self.config["CLIENTS"]:
            if client["IP"] == ip:
                logger.info("CLIENT ID: {0} CONNECTED!".format(client["ID"]))
                client["CONNECTED"] = True

        # UPDATE THE ALL CONNECTED VARIABLE
        self._determine_all_clients_connected()

    def get_start_auto(self):
        if self.config["START OPTION"].upper() == self.START_AUTO:
            return True

    def get_start_web(self):
        if self.config["START OPTION"].upper() == self.START_WEB:
            return True

    def _determine_all_clients_connected(self):
        # LOOP THROUGH AND UPDATE THE ALL CONNECTED BOOLEAN TO SEE IF WE HAVE ALL CLIENTS
        tlist = []
        for client in self.config["CLIENTS"]:
            tlist.append(client["CONNECTED"])
        self.all_connected = (not (False in tlist))

    def send_ping(self):
        # FUNCTION TO VERIFY CLIENT CONNECTION
        for client in self.config["CLIENTS"]:
            logger.info("PINGING CLIENT {0}".format(client["ID"]))
            self.socket.sendto(self.PING, client["ADDRESS"])

    def start_all(self):
        # FIGURE OUT IF WE'VE RUN BEFORE AND IF SO, RESET
        if self.get_tasks_completed():
            self.reset()
        # FUNCTION TO START CLIENTS
        for client in self.config["CLIENTS"]:
            self.socket.sendto(self.START, client["ADDRESS"])
        self.started = True
        self.webcontrol.set_tasks_running(self.started)
        # ONCE DONE WITH THE CLIENTS, START TASKY
        self.tasky.start()

    # THIS IS AN OVERLOADED FUNCTION
    def service_actions(self):
        # CHECK FOR TASKY RUNNING
        # IF NOT, AUTO SHUTDOWN
        if not self.tasky.is_running() and not self.done_with_tasks:
            logger.info("TASKS COMPLETE")
            self.started = False
            self.webcontrol.set_tasks_running(self.started)
            self.done_with_tasks = True
            self.tasky.join()


# FUNCTIONS
def sigterm_handler(_signo, _stack_frame):
    logger.info("FORCE KILLED")
    sys.exit(0)


def main():
    """
    main - This is the main function for doing all the work
    """

    # GET THE CLI ARGUMENTS
    parser = argparse.ArgumentParser(description='Escape Room Master Script', argument_default=argparse.SUPPRESS)
    # CONFIG ARGUMENT
    parser.add_argument('--config', metavar='file',
                        default='config.json', type=argparse.FileType('r'),
                        help='JSON Configuration File (defaults to config.json)')
    # DEBUG
    parser.add_argument('--debug', '-d', default=False, help="Debug capability: For simulating Tasker")
    # LOGGING VERBOSITY - DEFAULTS TO WARNING
    parser.add_argument('--verbose', '-v', action='count', 
                        default=0,
                        help='Set the logging level, nothing is Warnings and Critical, -v is Info, -vv is Debug')
    # PARSE
    args = parser.parse_args()

    logger.info("INITIALIZING")

    # HANDLE LOGGING LEVEL
    if args.verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    # CONVERT CONFIG TO JSON
    config = json.loads(args.config.read())

    # DEBUG
    logger.debug("CONFIGURATION")
    logger.debug(config)

    # SETUP BACKDOOR KILL SIGNALLING
    signal.signal(signal.SIGTERM, sigterm_handler)

    # CREATE OUR LOCAL ADDRESS
    address = (ANYHOST, config["PORT"])

    # INSTANTIATE CLASSES
    controller = Controller(address, ControllerHandler, config, debug=args.debug)

    # RUN FOREVER
    logger.info("STARTING MASTER CONTROLLER")
    try:
        controller.serve_forever()

        while True:
            time.sleep(1)

        logger.info("SHUTTING DOWN CONTROLLER")
        controller.shutdown()
    except KeyboardInterrupt:
        controller.kill()
        controller.shutdown()
    finally:
        # WANT THIS PRINT TO PUSH THINGS DOWN TO A NEW LINE
        print("")
        logger.info("EXITING")

if __name__ == "__main__":
    main()
