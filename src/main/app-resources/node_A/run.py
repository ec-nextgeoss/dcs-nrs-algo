#!/opt/anaconda/bin/python

import sys
import os
import cioppy

ciop = cioppy.Cioppy()

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input
from util import pass_next_node

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    start = ciop.getparam('startdate')
    stop = ciop.getparam('enddate')
    boundingarea = ciop.getparam('bounding_area')
    prod_type = ciop.getparam('type')
    log_input('searching with:')
    log_input(start)
    log_input(stop)
    log_input(boundingarea)
    log_input(prod_type)
    search_params = dict([('start',start),('stop', stop), ('geom', boundingarea), ('pt', prod_type)]) 
    search_result = ciop.search(end_point="https://catalog.terradue.com/sentinel2/search", params=search_params)
    # Log the input
    log_input(input)
    # Just pass the input reference to the next node
    #pass_next_node(input)
    ciop.publish(sources=search_result, mode='silent')
