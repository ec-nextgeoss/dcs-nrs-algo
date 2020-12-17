#!/opt/anaconda/bin/python

import sys
import os
import cioppy
import paramiko
from datetime import date

ciop = cioppy.Cioppy()

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input
import metadata_util as mu

# Get a share link from the ITC storage.
# The ITC folder stucture is: <base_folder_name>/<user folder>, with the
# base_folder_name equal to: /NextGeoss/<date>.
# the user_folder is specified by the client (software) (automatically generated based on a guid)
# Example folder: /NextGeoss/2019-11-11/gadh3jkk
def getSharelink(base_folder_name):
    username = 'nextgeoss'
    password = ciop.getparam('storname')
    folder_name = ciop.getparam('foldername')

    sid = mu.shareLaiProductLogin(username, password)
    print(sid)
    link = ''
    if sid != 'invalid':
        link = mu.shareLaiProduct(folder_name, base_folder_name, sid)
        print(link)

    mu.shareLaiProductLogout(sid)

    return link

def getConnection() :
    host = 'dikke.itc.utwente.nl'
    port = 22
    transport = paramiko.Transport((host,port))
    username = 'nextgeoss'
    password = ciop.getparam('storname')
    transport.connect(username = username, password = password)  # gives: CryptographyDeprecationWarning
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    return sftp

def createFolder(sftp, base) :
    # First create basefolder
    try:
        sftp.chdir(base)
    except IOError:
        ciop.log("INFO", "Creating base folder {}".format(base))
        sftp.mkdir(base)
        sftp.chdir(base)

    # then create sub folder
    folder = base + '/' + ciop.getparam('foldername')
    try:
        sftp.chdir(folder)
    except IOError:
        ciop.log("INFO", "Creating data folder {}".format(folder))
        sftp.mkdir(folder)
        sftp.chdir(folder)

def transferFile(sftp, filename) :
    _, destname = os.path.split(filename)   # extract name for destination
    
    ciop.log("INFO", "Transferring: {}".format(destname))
    try:
        sftp.put(filename, destname)
        os.remove(filename)
    except Exception:
        ciop.log("ERROR", "Transfer of {} failed".format(destname))



# initialize connection
sftp = getConnection()

# create destination folder
today = date.today()
base_folder_name = '/NextGeoss/' + today.isoformat()
createFolder(sftp, base_folder_name)    # create new destination folder and change to it

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
# Each line contains two filenames taht are separated by a semi-colon
# - tne datafile name
# - the accompanying metadata file name
for input in sys.stdin:
    datastr = input.strip()
    parts = datastr.split(';')
    laidata = parts[0]
    
    transferFile(sftp, laidata)

    # check if there is indeed a metadata file, and send it if so
    # but before that update the metadata file to include a data sharing link
    if len(parts) > 1:
        metadata = parts[1]
        
        # determine share link:
        # share the folder in which the files will end up
        share_link = getSharelink(base_folder_name)
        ciop.log("INFO", "Link={}".format(share_link))
        meta_dict = {'//gmd:linkage/gmd:URL' : share_link}

        # update the metadata file with the shared link info
        tempmeta = '/tmp/metainput.xml'
        os.rename(metadata, tempmeta)       # rename the existing metadata ...
        mu.updateMetadata(tempmeta, metadata, meta_dict)    #  ... so we can reuse the original name as final
        ciop.log("INFO", "Metadata updated and written to file")
        
        transferFile(sftp, metadata)

    
if sftp: sftp.close()
