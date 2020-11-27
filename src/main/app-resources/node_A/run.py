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
    cloudcover = ciop.getparam('cloud_cover')
    boundingarea = ciop.getparam('bounding_area')
    prod_type = ciop.getparam('type')
    # for test
    password = ciop.getparam('storname')
    ciop.log("INFO", "storname=|{}|".format(password))
    # for test
    log_input('searching with:')
    log_input(start)
    log_input(stop)
    log_input(cloudcover)
    log_input(boundingarea)
    log_input(prod_type)
#    search_params = dict([('start',start),('stop', stop), ('geom', boundingarea), ('pt', prod_type), ('cc', cloudcover)]) 
    search_params = dict([('start',start),('stop', stop), ('geom', boundingarea), ('pt', prod_type)]) 
    search_result = ciop.search(end_point="https://catalog.terradue.com/sentinel2/search", params=search_params, output_fields='self')
   
    for elem in search_result:
        ciop.log("INFO", elem.values()[0])
        ciop.publish(sources=elem.values()[0] + '\n', mode = 'silent')
