#!/opt/anaconda/bin/python

import sys
import os

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input
from util import pass_next_node

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    # Log the input
    log_input(input)
    # Just pass the input reference to the next node
    pass_next_node(input)
