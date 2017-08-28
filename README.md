## Master/Client Readme

This framework allows 1 master and many clients to connect and be controlled.

Requires:
* Python3
* SBC GPIO Library (Future Capability)

## Master
The master is responsible for controlling all clients.  It can also run it's own tasks.

### Master Control Usage:

    ```bash
    usage: master_control.py [-h] [--config file] [--debug DEBUG] [--verbose]
    
    Escape Room Master Script
    
    optional arguments:
      -h, --help            show this help message and exit
      --config file         JSON Configuration File (defaults to config.json)
      --debug DEBUG, -d DEBUG
                            Debug capability: For simulating Tasker
      --verbose, -v         Set the logging level, nothing is Warnings and
                            Critical, -v is Info, -vv is Debug
    ```

#### Example

    ```bash
    python3 master_control.py --config master_config.json
    ```

### Master JSON Config

The Master JSON config contains a list of all clients and any tasks the master needs to perform

    ```json
    {
    "CONFIG" : "MASTER",
    "PORT" : 10005,
    "PING TIMER" : 60,
    "START OPTION" : "AUTO",
    "CLIENTS" : [
     {
      "ID" : 5,
      "IP" : "127.0.0.1",
      "PORT" : 10006
     }
    ],
    "TASKS" : [
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
    }
    ```

#### Port
Port to listen to responses on

#### Ping Timer
Interval in seconds to ensure client connected

#### Start Option
How the tasks should be started: Auto/Web/GPIO
Auto - Once all clients connect, all tasks are started
Web - Web control on port 8080 of the master controller
GPIO - hasn't been implemented

#### Client List JSON
The client list contains a dictionary of the ID, IP Address, and the Port to communicate with

## Client

The client is designed to be something that is told to start running tasks. This code has the ability to reset itself when complete and wait for another start command from the master.

### Client Usage

    ```bash
    usage: client.py [-h] [--config file] [--debug DEBUG] [--verbose]

    Escape Room Client Script

    optional arguments:
      -h, --help            show this help message and exit
      --config file         JSON Configuration File (defaults to config.json)
      --debug DEBUG, -d DEBUG
                            Debug capability: For simulating Tasker
      --verbose, -v         Set the logging level, nothing is Warnings and
                            Critical, -v is Info, -vv is Debug
    ```

#### Example

    ```bash
    python3 client.py --config client_1_config.json
    ```

### Client JSON Config

    ```json
    {
    "CONFIG" : "THING_1",
    "ID" : 5,
    "PORT" : 10006,
    "TASKS" : [
      {
      "TYPE" : "TASK",
      "DELTA TIME FROM START" : 5.5,
      "TIME UNITS" : "SECONDS",
      "COMMAND" : "testvid.mp4"
      },
      {
      "TYPE" : "TASK",
      "DELTA TIME FROM START" : 10.23,
      "TIME UNITS" : "SECONDS",
      "COMMAND" : "some_audio.mp3"
      },
      {
      "TYPE" : "STOP",
      "DELTA TIME FROM START" : 15.23,
      "TIME UNITS" : "SECONDS",
      "COMMAND" : ""
      }
    ]
    }
    ```

#### Port
Port to listen to commands on

#### ID
Identifier of the client, needs to be in client list in the Master config JSON file

## Task List JSON
The Task List is common between the Master and Client JSON Configurations. This list contains dictionary elements for defining tasks.

The last item in the list needs to be a stop type.

#### Type
Type of task: Task/Stop
The Stop task tells the code this is the last item in the list.  For the Master Controller, the stop task should always end after the last client command.

#### Delta Time From Start
Time after start where task should be run

#### Time Units
Unit of measure for the delta time from start.
Allowable Options: Microseconds, Milliseconds, Seconds, Minutes, Hours

#### Command
Space delimited command with full paths to be run, this is run through `shlex` to create proper cli flow for `subprocess.Popen`.
If the task type is "Stop", this field can be empty


## Current Issues

1. Have to hit Ctrl-C to kill the scripts

