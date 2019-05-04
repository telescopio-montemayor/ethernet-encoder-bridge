# ethernet-encoder-bridge

Small utility to translate lx200 and Stellarium commands into calls to <https://github.com/telescopio-montemayor/ethernet-encoder-servo>


## Installation

Under a virtualenv do:

```
    pip install -e .
```

in order to fetch all the dependencies and install it as *ethernet-encoder-bridge*


## Usage


```
$ ethernet-encoder-bridge --help
usage: ethernet-encoder-bridge [-h] [--encoder-server ENCODER_SERVER]
                               [--ra-axis-id RA_AXIS_ID]
                               [--dec-axis-id DEC_AXIS_ID] [--port PORT]
                               [--stellarium-port STELLARIUM_PORT]
                               [--web-port WEB_PORT] [--host HOST]
                               [--store-path STORE_PATH]
                               [--store-format {json,yaml}]
                               [--state-save-interval STATE_SAVE_INTERVAL]
                               [--verbose]

Bridge between ethernet-encoder-servo and LX200/Stellarium protocol

optional arguments:
  -h, --help            show this help message and exit
  --encoder-server ENCODER_SERVER
                        ethernet encoder server url (http://localhost:5000)
  --ra-axis-id RA_AXIS_ID
                        Id of axis to map to Right Ascencion (RA)
  --dec-axis-id DEC_AXIS_ID
                        Id of axis to map to Declination (DEC)
  --port PORT           TCP port for the LX200 server (7634)
  --stellarium-port STELLARIUM_PORT
                        TCP port for the Stellarium server (10001)
  --web-port WEB_PORT   TCP port for the status server (8081)
  --host HOST           Host for all the servers (127.0.0.1)
  --store-path STORE_PATH
                        Path to load and save scope status store
  --store-format {json,yaml}
                        Output format for store, default: JSON
  --state-save-interval STATE_SAVE_INTERVAL
                        Interval in milliseconds between state saving (1000)
  --verbose
```
