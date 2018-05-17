#!/opt/anaconda/bin/python

import sys
import os

import cioppy

ciop = cioppy.Cioppy()

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    # Logs the inputs received from the previous node. Since it is configured
    # as 'aggregator' (see application.xml), it collects the inputs of all the
    # instances of the previous node.
    log_input(input)

    url_list = ciop.search(end_point = input, output_fields = "enclosure", params = dict())
    for v in url_list:
        url = v.values()[0]
        #ciop.copy(url, ciop.tmp_dir)

res = ciop.copy("file:///data/S2A_MSIL2A_20180501T105031_N0207_R051_T31UEU_20180501T144449.zip", ciop.tmp_dir)
ciop.log("INFO", res)
