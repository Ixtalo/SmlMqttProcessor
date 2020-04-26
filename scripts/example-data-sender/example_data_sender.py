#!/usr//bin/env python

import os
import sys
from time import sleep

FILENAME = '../../example_data/ISKRA_MT691_eHZ-MS2020.txt'

__script_dir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(__script_dir, FILENAME)) as fin:
    while True:
        for line in fin:
            if line.startswith('1-0:96.50.1*1#ISK#'):
                #sys.stdout.write(line)
                print(line.strip())
                print(fin.readline().strip())
                print(fin.readline().strip())
                print(fin.readline().strip())
                print(fin.readline().strip())
            sys.stdout.flush()
            sleep(1.0)

        fin.seek(0)
