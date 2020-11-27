#!/opt/anaconda/bin/python

import sys
import os
import cioppy
import paramiko
from datetime import date

ciop = cioppy.Cioppy()

sys.path.append(os.environ['_CIOP_APPLICATION_PATH'] + '/util')
from util import log_input

today = date.today()
base_folder_name = '/NextGeoss/' + today.isoformat()
folder_name = base_folder_name + '/' + ciop.getparam('foldername')
host='dikke.itc.utwente.nl'
port=22
transport=paramiko.Transport((host,port))
username='nextgeoss'
password = ciop.getparam('storname')
transport.connect(username=username,password=password)  # gives: CryptographyDeprecationWarning
sftp=paramiko.SFTPClient.from_transport(transport)
# First create basefolder
try:
    sftp.chdir(base_folder_name)
except IOError:
    ciop.log("INFO", "Creating base folder ^{}^".format(base_folder_name))
    sftp.mkdir(base_folder_name)
    sftp.chdir(base_folder_name)

# then create sub folder
try:
    sftp.chdir(folder_name)
except IOError:
    ciop.log("INFO", "Creating data folder ^{}^".format(folder_name))
    sftp.mkdir(folder_name)
    sftp.chdir(folder_name)

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    fdata = input.strip()
    _, name = os.path.split(fdata)   # extract name for destination
    ciop.log("INFO", "Transferring: ^{}^".format(name))
    try:
        sftp.put(fdata,name)
        os.remove(fdata)
    except Exception:
        ciop.log("ERROR", "Transfer of ^{}^ failed".format(name))
    
if sftp: sftp.close()
if transport: transport.close()
