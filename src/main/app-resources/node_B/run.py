#!/opt/anaconda/bin/python

import sys
import os

import cioppy

ciop = cioppy.Cioppy()

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input

# workaround to get GDAL to read Sentinel2 L2A products as well
# this works by accessing the bands from the zipfile directly
# The sentinel zip image is opened and the R, B, NIR bands are copied to
# separate tif files; the original zipfile can then be removed
def extract_R_B_NIR(sentinel_zip) :
    ## vsizip bugfix
    os.environ['CPL_ZIP_ENCODING'] = 'UTF-8'

    outname = ['Blue.tif', 'Red.tif', 'NIR.tif']
    tileREXP = re.compile(r'.*B(02|04|8A)_20m.*.jp2$')
    zf = ZipFile(sentinel_zip, 'r')
    bands = [x for x in zf.namelist() if re.match(tileREXP,x)]
    bands.sort()    #make sure the bands are in order 2 (blue), 4 (Red), 8a (NIR); the loop relies on this

    # convert the needed bands to tiff
    for b in bands:
        src_ds = gdal.Open('/vsizip/%s/%s' %(sentinel_zip, bands[b]))
        dst_filename = ciop.tmp_dir + '/' + outname[b]

        fileformat = "GTiff"
        driver = gdal.GetDriverByName(fileformat)
        dst_ds = driver.CreateCopy(dst_filename, src_ds, strict=0)

        src_ds = None
        dst_ds = None

    #cleanup
    #if os.path.isfile(sentinel_zip):
    #    os.remove(sentinel_zip)

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
