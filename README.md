# SmlMqttProcessor

Process Smart Message Language (SML) for Power Smart Meters.


## Requirements
* Python 3.5
    * Python version or code level must be compatible to the Python version on the target system, e.g., Python 3.5 for Raspbian Jessie!
* python3-pip
* wget


## How-To Run
1. Build `sml_server_time`, see [sml_server_time/README.md](sml_server_time/README.md).
2. Generate Python virtual environment allowing access to the system's Python packages:  
   `python -m virtualenv --python=python3.5 --system-site-packages venv`
3. Activate virtualenv:  
   `source ./venv/bin/activate`
4. Run in activated virtualenv to study CLI help:  
   `python smltextmqttprocessor.py --help`
5. Create local configuration file 
   `cp config.template.ini config.local.ini`
   and adjust to your settings.    
6. Run in activated virtualenv:  
   `./sml_server_time/sml_server_time /dev/ttyAMA0 | python smltextmqttprocessor.py config.local.ini -` 
