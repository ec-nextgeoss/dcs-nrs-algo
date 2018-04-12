#!/opt/anaconda/bin/python

import sys
import os

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    # Logs the inputs received from the previous node. Since it is configured
    # as 'aggregator' (see application.xml), it collects the inputs of all the
    # instances of the previous node.
    log_input(input)