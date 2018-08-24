#!/opt/anaconda/bin/python

import sys
import os
import re
import gdal
from zipfile import ZipFile

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
    bindex = 0
    for b in bands:
        src_ds = gdal.Open('/vsizip/%s/%s' %(sentinel_zip, bands[bindex]))
        dst_filename = ciop.tmp_dir + '/' + outname[bindex]

        fileformat = "GTiff"
        driver = gdal.GetDriverByName(fileformat)
        dst_ds = driver.CreateCopy(dst_filename, src_ds, strict=0)

        bindex += 1
        src_ds = None
        dst_ds = None

    parts = os.path.splitext(os.path.basename(sentinel_zip))
    prod_name = parts[0] + '_lai.tif'
    return prod_name

# Calculate LAI with uncalibrated Sentinel2 input data. This means that the scale factor of 10000 needs to be handled here
def calc_LAI(prod_name):
    # define the input bands
    outname = ['Blue.tif', 'Red.tif', 'NIR.tif']

    # get the names of the blue, red and nir data
    fnblue = ciop.tmp_dir + '/' + outname[0]
    fnred = ciop.tmp_dir + '/' + outname[1]
    fnnir = ciop.tmp_dir + '/' + outname[2]
    laifile = ciop.tmp_dir + '/' + prod_name

#   expr_cal is the expression expecting calibrated Sentinel2 input with reflectances instead of DN's
#   expr_cal = '/opt/anaconda/bin/gdal_calc.py --type=Float32 --NoDataValue=-0 --calc="3.618 * (2.5 * (C - B) / (1 + C + 6 * B - 7.5 * A)) - 0.118" -A ' + fnblue + " -B " + fnred + " -C " + fnnir + " --outfile=" + laifile

#   expr_nocal is the expression expecting uncalibrated Sentinel2 input, so DN's in the range between 0 and 10000
    expr_nocal = '/opt/anaconda/bin/gdal_calc.py --type=Float32 --NoDataValue=-0 --calc="3.618 * (2.5 * (C - B) / (10000 + C + 6 * B - 7.5 * A)) - 0.118" -A ' + fnblue + " -B " + fnred + " -C " + fnnir + " --outfile=" + laifile

    ciop.log("INFO",expr_nocal)
    os.system(expr_nocal)

    # Of course keep LAI
    lailist = []
    lailist.append(laifile)
    return lailist

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
        ciop.log("INFO", url)
        res = ciop.copy(url, ciop.tmp_dir, extract=False)
        prod_name = extract_R_B_NIR(res)
        ciop.log("INFO", prod_name)
        lairesult = calc_LAI(prod_name)
        for curlai in lairesult:
            ciop.publish (curlai, metalink=True)

