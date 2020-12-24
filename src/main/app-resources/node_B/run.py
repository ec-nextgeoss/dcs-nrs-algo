#!/opt/anaconda/bin/python

import sys
import os
import re
from datetime import date
import gdal
from osgeo.gdalconst import *
import numpy as np
from zipfile import ZipFile

import cioppy

ciop = cioppy.Cioppy()

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input
import metadata_util as mu

# workaround to get GDAL to read Sentinel2 L2A products as well
# this works by accessing the bands from the zipfile directly
# The sentinel zip image is opened and the R, B, NIR bands are loaded;
# the original zipfile can then be removed
def extract_R_B_NIR(sentinel_zip) :
    ciop.log("INFO", "Start loading data")
    ## vsizip bugfix
    os.environ['CPL_ZIP_ENCODING'] = 'UTF-8'

    outname = ['Blue.tif', 'Red.tif', 'NIR.tif']
    tileREXP = re.compile(r'.*B(02|04|8A)_20m.*.jp2$')
    zf = ZipFile(sentinel_zip, 'r')
    bands = [x for x in zf.namelist() if re.match(tileREXP,x)]
    bands.sort()    #make sure the bands are in order 2 (blue), 4 (Red), 8a (NIR); the loop relies on this

    # Read the data from the selected bands
    bdata = []
    proj = None
    georef = None
    for b in bands:
        ds = gdal.Open('/vsizip/%s/%s' %(sentinel_zip, b))
        data = ds.ReadAsArray()
        ciop.log("INFO", "Loaded band {}".format(b))
        bdata.append(data)
        ciop.log("INFO", "data size {},{}".format(data.shape[0], data.shape[1]))

        if proj == None:
            ciop.log("INFO", "Getting projection")
            proj = ds.GetProjection()
        if georef == None:
            ciop.log("INFO", "Getting transform")
            georef = ds.GetGeoTransform()

        ds = None

    parts = os.path.splitext(os.path.basename(sentinel_zip))
    prod_name = parts[0] + '_lai.tif'

    ciop.log("INFO", "Succesfully loaded product bands for {}".format(prod_name))

    return prod_name, bdata, proj, georef

# Calculate the LAI in memory.
# data contains B2, B4, B8a (in that order); the data has not yet been scaled
def calc_LAI_mem(laifile, data, proj, georef):
    ciop.log("INFO", "Checks for data out of range started")
    
    bdata = data[0]
    rdata = data[1]
    ndata = data[2]
    
    # check if the data is in a valid range
    rcheck = np.logical_and ( rdata > 0, rdata < 10000)
    bcheck = np.logical_and ( bdata > 0, bdata < 10000)
    ncheck = np.logical_and ( ndata > 0, ndata < 10000)
    check = rcheck * bcheck * ncheck
    
    # make some space by removing non-needed large arrays
    del [rcheck, bcheck, ncheck]

    ciop.log("INFO", "Calculation started")
    # numpy calculates with doubles, so after turn them into floats
    lai_raw = np.where(check, (((((ndata - rdata) * 2.5 * 3.618) / (10000. + ndata + rdata * 6 - bdata * 7.5))) - 0.118), -999.)
    vcheck = np.logical_and ( lai_raw > -1, lai_raw < 20)
    lai = np.where(vcheck, lai_raw, -999.)
    
    ciop.log("INFO", "Calculation finished")
    lai = lai.astype(np.float32)
    
    ciop.log("INFO", "Start saving LAI")
    # Now write the lai to tiff
    fileformat = "GTiff"
    driver = gdal.GetDriverByName(fileformat)
    ciop.log("INFO", "Tiff driver selected")
    ciop.log("INFO", "Create tiff")
    dst_ds = driver.Create(laifile, bdata.shape[0], bdata.shape[1], 1, GDT_Float32)

    ciop.log("INFO", "Fill values")
    dst_band = dst_ds.GetRasterBand(1)
    dst_band.SetNoDataValue(-999.)
    dst_band.WriteArray(lai)

    ciop.log("INFO", "Set projection info")
    dst_ds.SetGeoTransform(georef)
    dst_ds.SetProjection(proj)

    ciop.log("INFO", "Saving LAI finished")

    return laifile


# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    # Logs the inputs received from the previous node. Since it is configured
    # as 'aggregator' (see application.xml), it collects the inputs of all the
    # instances of the previous node.
    log_input(input)
    ciop.log("INFO", "Running python {}".format(sys.version))

    try:
        template_path = os.path.dirname(os.path.realpath(__file__))
        template = template_path + "/" + "nextgeoss_template.xml"
            
        url_list = ciop.search(end_point = input, output_fields = "enclosure", params = dict())
        for v in url_list:
            url = v.values()[0]
            ciop.log("INFO", "Copying tile: {}".format(url))
            sentinel_zip = ciop.copy(url, ciop.tmp_dir, extract=False)
            ciop.log("INFO", "Copying tile finished")
            
            prod_name, bdata, proj, georef = extract_R_B_NIR(sentinel_zip)

            # determine output file names for LAI and metadata
            laifile = '/tmp/' + prod_name       # the LAI product filename
            parts = os.path.splitext(laifile)
            lai_meta_name = parts[0] + '.xml'   # the metadata file for the LAI product
            ciop.log("INFO", "Metadataname: {}".format(lai_meta_name))
            
            meta_dict = mu.extractTileMetadata(sentinel_zip)
            ciop.log("INFO", "Extracting metadata from tile finished")

            mu.updateMetadata(template, lai_meta_name, meta_dict)
            ciop.log("INFO", "Metadata written to file")
            
            lairesult = calc_LAI_mem(laifile, bdata, proj, georef)
            lairesult = lairesult + ';' + lai_meta_name

            pub = ciop.publish (lairesult + '\n', mode = 'silent')
    except:
        print("Unexpected error:", sys.exc_info()[0:2])
        ciop.log("INFO", "empty search result, skipping")
