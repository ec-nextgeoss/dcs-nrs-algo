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
folder_name = '/NextGeoss/' + today.isoformat()
host='dikke.itc.utwente.nl'
port=22
transport=paramiko.Transport((host,port))
username='nextgeoss'
#password = os.environ.get('SFTP_PASSWORD')
password = ciop.getparam('storname')
ciop.log("INFO", "storname=|{}|".format(password))
transport.connect(username=username,password=password)  # gives: CryptographyDeprecationWarning
sftp=paramiko.SFTPClient.from_transport(transport)
try:
    sftp.chdir(folder_name)
except IOError:
    sftp.mkdir(folder_name)
    sftp.chdir(folder_name)

# Input references come from STDIN (standard input) and they are retrieved
# line-by-line.
for input in sys.stdin:
    fdata = input.strip()
    ciop.log("INFO", "input=^{}^".format(fdata))
    _, name = os.path.split(fdata)   # extract name for destination
    ciop.log("INFO", "fname=^{}^".format(name))
    sftp.put(fdata,name)
    os.remove(fdata)
    
sftp.close()
transport.close()
