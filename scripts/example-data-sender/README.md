# example-data-sender

Simple Python script to simulate libsml's sml_server textual, decoded output.
It can be used as input to `smltextmqttprocessor.py`.

## Usage
`python3 scripts/example-data-sender/example_data_sender.py | python3 smltextmqttprocessor.py --no-mqtt --debug config.local.ini -`

Output:
```
(venv) SmlMqttProcessor git:(master) ✗ python3 scripts/example-data-sender/example_data_sender.py | python3 smltextmqttprocessor.py --no-mqtt --debug config.local.ini -
2020-09-27 07:45:05 DEBUG    root       ---- ENABLING DEBUG OUTPUT!!! -------
2020-09-27 07:45:05 DEBUG    root       {'--debug': True,
 '--help': False,
 '--no-mqtt': True,
 '--quiet': False,
 '--verbose': False,
 '--version': False,
 '<config-file.ini>': 'config.local.ini',
 '<input>': '-'}
2020-09-27 07:45:05 INFO     root       Config file: /home/user/SmlMqttProcessor/config.local.ini
2020-09-27 07:45:05 INFO     root       Block size: 3
2020-09-27 07:45:05 INFO     root       <_io.TextIOWrapper name='<stdin>' mode='r' encoding='utf-8'>
2020-09-27 07:45:05 DEBUG    root       waiting for header line...
2020-09-27 07:45:05 DEBUG    root       header line found
2020-09-27 07:45:05 DEBUG    root       next header found
2020-09-27 07:45:05 DEBUG    root       data: {'actual': 26, 'total': 198927.3, 'time': 6825876}
2020-09-27 07:45:05 DEBUG    root       waiting for header line...
2020-09-27 07:45:05 DEBUG    root       header line found
2020-09-27 07:45:05 DEBUG    root       next header found
2020-09-27 07:45:05 DEBUG    root       data: {'actual': 27, 'total': 198927.4, 'time': 6825879}
2020-09-27 07:45:05 DEBUG    root       waiting for header line...
2020-09-27 07:45:05 DEBUG    root       header line found
2020-09-27 07:45:05 DEBUG    root       next header found
2020-09-27 07:45:05 DEBUG    root       data: {'actual': 27, 'total': 198927.4, 'time': 6825882}
2020-09-27 07:45:05 DEBUG    root       waiting for header line...
2020-09-27 07:45:05 DEBUG    root       header line found
2020-09-27 07:45:05 DEBUG    root       next header found
2020-09-27 07:45:05 DEBUG    root       data: {'actual': 27, 'total': 198927.4, 'time': 6825885}
NO-MQTT: {'total': [198927.3, 198927.4, 198927.4, 198927.4], 'actual': [26, 27, 27, 27], 'time': [6825876, 6825879, 6825882, 6825885]}
```
