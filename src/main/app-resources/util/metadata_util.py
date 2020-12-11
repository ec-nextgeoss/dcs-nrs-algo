import os
import re
from zipfile import ZipFile
import uuid
from datetime import datetime, date
from zipfile import ZipFile
from lxml import etree as etree_lxml
from pyproj import CRS
from pyproj import Transformer
import paramiko
import requests
import json

def findXPath(tree, xpath, namespaces) :
    """Find xpath key in XML document and return its value
       or the value of the first child

       Parameters:
         tree (lxml object) : xml document to scan
         xpath (string): uniquely specified xpath.
         namespaces (list): list of all namespaces within the XML document.

       Returns:
         string: value of the xpath key, or empty string if not found.

    """
    items = tree.xpath(xpath, namespaces = namespaces)
    if len(items) > 0 :
        fid = items[0]
        chs = fid.getchildren()
        value = fid.text
        return value
    return ""

def updateXPath(tree, xpath, newvalue, namespaces) :
    items = tree.xpath(xpath, namespaces = namespaces)
    if len(items) > 0 :
        fid = items[0]
        chs = fid.getchildren()
        fid.text = newvalue
        return True
    return False

def acceptXML(filter, filename):
    return re.match(filter, os.path.basename(filename))

def extractTileMetadata(sentinel_zip):
    zf = ZipFile(sentinel_zip, 'r')
    fil_xml = re.compile(r'MTD_TL[.]xml')
    
    # only get the metadata for the tiles (not the product metadata)
    # modern sentinel tiles only have one tile, so expect only one file
    xml = [x for x in zf.namelist() if acceptXML(fil_xml, x)][0]
    
    data = zf.read(xml)
    tree = etree_lxml.fromstring(data)
    namespaces = tree.nsmap
    
    # collect the needed items (fixed at 20m resolution)
    tile_str = findXPath(tree, '//n1:General_Info/*[starts-with(name(),\'TILE_ID\')]', namespaces)
    tse = re.search(r'S2A_.*(T\d{2}\w{3})_.*', tile_str)
    if tse :
        tile_id = tse.group(1)
    else :
        tile_id = ''
    tile_name = 'Leaf Area Index ' + tile_id

    dataID = findXPath(tree, '//n1:General_Info/*[contains(name(),\'DATASTRIP_ID\')]', namespaces)  # for sensing period
    sense_time = findXPath(tree, '//SENSING_TIME', namespaces)    # ISO 8601 formatted date time
    proj_name = findXPath(tree, '//HORIZONTAL_CS_NAME', namespaces)  
    proj_epsg = findXPath(tree, '//HORIZONTAL_CS_CODE', namespaces)  # formatted as EPSG:<crs code>
    nrcols = int(tree.xpath("//Size[@resolution='20']/NCOLS", namespaces = namespaces)[0].text)
    nrrows = int(tree.xpath("//Size[@resolution='20']/NROWS", namespaces = namespaces)[0].text)
    left = int(tree.xpath("//Geoposition[@resolution='20']/ULX", namespaces = namespaces)[0].text)
    top = int(tree.xpath("//Geoposition[@resolution='20']/ULY", namespaces = namespaces)[0].text)
    
    # get begin and end date of sensing
    pat = re.compile('.*_(\d{4})(\d{2})(\d{2})T.*(\d{4})(\d{2})(\d{2})T')
    match = re.match(pat, dataID)
    if match:
        beginpos = '{}-{}-{}'.format(match[1], match[2], match[3])
        endpos   = '{}-{}-{}'.format(match[4], match[5], match[6])
    else:
        beginpos = ''
        endpos = ''

    # determine geographic spatial extent by reprojecting
    inProj = CRS(proj_epsg)
    outProj = CRS('epsg:4326')
    transformer = Transformer.from_crs(inProj, outProj)
    # transform all corners
    tl = transformer.transform(left              , top)
    tr = transformer.transform(left + nrcols * 20, top)
    br = transformer.transform(left + nrcols * 20, top - nrrows * 20)
    bl = transformer.transform(left              , top - nrrows * 20)
    extent = [tl, tr, br, bl]
    lowlat = min([x[0] for x in extent])
    highlat = max([x[0] for x in extent])
    lowlon = min([x[1] for x in extent])
    highlon = max([x[1] for x in extent])
    
    # Add datestamp of production of metadata (now)
    stamp = datetime.utcnow().replace(microsecond=0).isoformat()
    
    # generate unique id for the fileIdentifier
    # Note: keep parentIdentifier unchanged
    guid = str(uuid.uuid1())
    
    # return with the xpath keys as used in the web-based metadata
    return {  '//gmd:southBoundLatitude/gco:Decimal':'%.7f' % lowlat
            , '//gmd:northBoundLatitude/gco:Decimal':'%.7f' % highlat
            , '//gmd:westBoundLongitude/gco:Decimal':'%.7f' % lowlon
            , '//gmd:eastBoundLongitude/gco:Decimal':'%.7f' % highlon
            , '//gmd:title/gco:CharacterString':tile_name
            , '//gmd:code/gco:CharacterString':proj_name.split('/')[0].strip()   # fe: WGS84
            , '//gco:Date':sense_time.split('T')[0]          # format: 2016-06-03, for date stamp
            , '//gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition':beginpos   # format: 2016-06-03
            , '//gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition':endpos      # format: 2016-06-03
            , '//gmd:dateStamp/gco:DateTime':stamp           # format: 2016-06-03T14:14:01
            , '//gmd:fileIdentifier/gco:CharacterString':guid   # fe: 93234fee-e937-11ea-81ea-c8d9d23643d9 (RFC 4122)
           }
 
def updateMetadata(template, outname, perm_dict):
    metatree = etree_lxml.parse(template)
    namespaces = metatree.getroot().nsmap
    for key in perm_dict.keys():
        updateXPath(metatree, key, perm_dict[key], namespaces)
    
    metatree.write(outname, encoding = metatree.docinfo.encoding, xml_declaration = True)

def createMetadata(zipfile):
    parts = os.path.splitext(zipfile)
    lai_meta_name = parts[0] + '.xml'        # name of the new metadata file
    meta_dict = extractTileMetadata(zipfile)      # all metadata from the data tile

    template = 'nextgeoss_template.xml'
    outname = 'temp.xml'
    updateMetadata(template, outname, meta_dict)
   
    return outname

def shareLaiProduct(laifile, location, sid):
    # location is the path without trailing separator, fe: /NextGeoss/2020-01-15
    path = location + '/' + os.path.basename(laifile)      # fe: /NextGeoss/2020-01-15/S2A_MSIL2A_20180508T104031_N0207_R008_T32ULC_20180508T175127_lai.tif
    share_url ='https://dikke.itc.utwente.nl:5001/webapi/entry.cgi'
    share_params = {  'api':'SYNO.FileStation.Sharing'
                    , 'version':'1'
                    , 'method':'create'
                    , 'path':path
                    , '_sid':sid }
    share = requests.get(share_url, params = share_params)
    res = json.loads(share.text)
    link = ''
    if res['success']:
        link = res['data']['links'][0]['url']
    
    return link
                
def shareLaiProductLogin(user, pwd):
    auth_query='https://dikke.itc.utwente.nl:5001/webapi/auth.cgi'
    auth_params={ 'api':'SYNO.API.Auth'
                 ,'version':'3'
                 ,'method':'login'
                 ,'account':user
                 ,'passwd':pwd
                 ,'session':'FileStation'
                 ,'format':'cookie'}
    au = requests.get(auth_query, params = auth_params)
    res = json.loads(au.text)
    sid = 'invalid'
    if res['success']:
        sid = res['data']['sid']        # get the session id
    
    return sid

def shareLaiProductLogout(sid):
    # finally logout again
    auth_query='https://dikke.itc.utwente.nl:5001/webapi/auth.cgi'
    logout_params = { 'api':'SYNO.API.Auth'
                     ,'version':'3'
                     ,'method':'logout'
                     ,'session':'FileStation'
                     ,'_sid':sid}
    au_lo = requests.get(auth_query, params = logout_params)
    res = json.loads(au_lo.text)
    return res['success']

# shortcut function to share a file or folder
# returns the share link if succesfull, empty string otherwise
def sharefile(laifile, location, user, pwd):
    sid = shareLaiProductLogin(user, pwd)
    link = ''
    if sid != 'invalid':
        link = shareLaiProduct(laifile, location, sid)
    
    shareLaiProductLogout(sid)
    
    return link

def updateMetadata(template, outname, perm_dict):
    metatree = etree_lxml.parse(template)
    namespaces = metatree.getroot().nsmap
    for key in perm_dict.keys():
        updateXPath(metatree, key, perm_dict[key], namespaces)
    
    metatree.write(outname, encoding = metatree.docinfo.encoding, xml_declaration = True)

# test function
def createMetadata(zipfile):
    parts = os.path.splitext(zipfile)
    lai_meta_name = parts[0] + '.xml'             # name of the new metadata file
    meta_dict = extractTileMetadata(zipfile)      # all metadata from the data tile

    template = 'nextgeoss_template.xml'
    outname = 'temp.xml'
    updateMetadata(template, outname, meta_dict)
   
    return outname