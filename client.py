# THIS USES PYTHON 3

# ESCAPE ROOM CLIENT CONTROL
# FRAMEWORK LAID OUT BY ROBERT WOLTERMAN (xtacocorex)

# MODULE IMPORTS
import argparse
import json
import socketserver
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
NAME = "ESCAPE ROOM"
FORMAT = '%(asctime)-15s %(levelname)-10s %(module)-12s %(message)s'

# LOGGING
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(NAME)
logger.setLevel(logging.DEBUG)

# CLASSES
class ClientHandler(socketserver.BaseRequestHandler):
    """
    ClientHandler - Class to handle receiving data from the controller
    """

    # OVERLOAD THE SETUP
    def setup(self):
        logger.debug("CLIENT HANDLER CREATED")

    # OVERLOAD THE HANDLE FUNCTION
    def handle(self):
        # STRIP EXTRA STUFF AND MAKE IT LOWERCASE
        data = self.request[0]
        # FIGURE OUT WHO THIS IS FROM - GET JUST THE IP
        sender = self.client_address[0]
        # GET THE SOCKET THAT IS LOCAL TO THE HANDLER
        sock = self.request[1]

        # FIGURE OUT IF THE DATA IS A PING
        # NOTE: THIS LOOKS GOOFY, BUT CLIENT HANDLER WILL BE PASSED
        # INTO CLIENT SERVER AND CAN ACCESS THE PARENT CLASS MEMBER VARIABLES
        if data == self.server.PING:
            # SEND THE IP INTO THE SERVER FUNCTION TO SET CONNECTED
            logger.info("PING RECEIVED FROM: {0}".format(sender))
            logger.info("SENDING PONG TO: {0}".format(self.client_address))
            sock.sendto(self.server.PONG, self.client_address)

        # FIGURE OUT IF DATA IS A START
        # SO WE CAN START THE LOCAL TASKS
        if data == self.server.START:
            # FIGURE OUT IF WE'VE RUN BEFORE AND IF SO, RESET
            if self.server.get_tasks_completed():
                self.server.reset()
            # START THE TASKY
            logger.info("START RECEIVED FROM: {0}".format(sender))
            mystr = "client {0} starting".format(self.server.config["ID"])
            sock.sendto(str.encode(mystr), self.client_address)
            self.server.tasky.start()


class Client(socketserver.UDPServer):
    """
    Client
     - This code handles client side things
     - Runs any tasks the client is responsible for 
    """

    # WE KINDA WANT TO BE A DAEMON
    daemon_threads = True
    # FASTER BINDING
    allow_reuse_address = True

    # STUFF FOR DETERMINING CONNECTION
    PING = str.encode("ping")
    PONG = str.encode("pong")
    START = str.encode("start")

    def __init__(self, server_address, RequestHandlerClass, config, debug=False):
        socketserver.UDPServer.__init__(self, server_address, RequestHandlerClass)
        # STORE OUR CONFIG SO WE CAN KEEP TRACK OF THINGS
        self.config = config
        self.debug = debug
        self.done_with_tasks = False
        # CREATE THE TASKER INSTANCE FOR THE CONTROLLER
        # WE WON'T START UNTIL ALL CLIENTS HAVE CONNECTED
        self.tasky = tasker.Tasker(self.config["TASKS"], debug=self.debug)

    def get_tasks_completed(self):
        return self.done_with_tasks

    def reset(self):
        # FUNCTION TO RESET THE CLIENT FOR ANOTHER GO
        logger.info("RESET")
        self.done_with_tasks = False
        self.tasky = tasker.Tasker(self.config["TASKS"], debug=self.debug)

    # THIS IS AN OVERLOADED FUNCTION
    def service_actions(self):
        # CHECK FOR TASKY RUNNING
        # IF NOT, AUTO SHUTDOWN
        if not self.tasky.is_running() and not self.done_with_tasks:
            logger.info("TASKS COMPLETE")
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
    parser = argparse.ArgumentParser(description='Escape Room Client Script', argument_default=argparse.SUPPRESS)
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
    logger.debug("ADDRESS: {0}".format(address))

    # INSTANTIATE CLASSES
    client = Client(address, ClientHandler, config, debug=args.debug)

    # RUN FOREVER
    logger.info("STARTING CLIENT")
    try:
        client.serve_forever()

        while not client.get_tasks_completed():
            time.sleep(1)

        logger.info("SHUTTING DOWN CLIENT")
        client.shutdown()
    except KeyboardInterrupt:
        client.shutdown()
    finally:
        # WANT THIS PRINT TO PUSH THINGS DOWN TO A NEW LINE
        print("")
        logger.info("EXITING")

if __name__ == "__main__":
    main()

