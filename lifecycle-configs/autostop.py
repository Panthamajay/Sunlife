import requests
from datetime import datetime
import getopt, sys
import urllib3
import boto3
import json
import pytz

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Usage
usageInfo = """Usage:
This scripts checks if a notebook is idle for X seconds if it does, it'll stop the notebook:
python autostop.py --time <time_in_seconds> [--port <jupyter_port>] [--ignore-connections]
Type "python autostop.py -h" for available options.
"""
# Help info
helpInfo = """-t, --time
    Auto stop time in seconds
-p, --port
    jupyter port
-c --ignore-connections
    Stop notebook once idle, ignore connected users
-h, --help
    Help information
"""
flag=0

now = datetime.now()
print("CURRENT Time is : ",now)


# This contains the local timezone i.e , UTC
local= pytz.timezone('UTC')

#replace function is used to convert time naive datatime object 'now' into a timezone aware object.
now = now.replace(tzinfo = local)
# prints a timezone aware datetime
print("DEFAULT time with timezone is :",now)


# astimezone is used to convert datetime from one timezone to another
#tz = pytz.timezone('America/Toronto')
tz = pytz.timezone('Asia/Kolkata')
now = now.astimezone(tz)
#print ("EST time is:",now)
print ("IST time is:",now)

H_now=now.hour
M_now=now.minute
S_now=now.second

print("H_now is :",H_now)

IN_HOUR=9
IN_MIN=00
IN_SEC=00


OUT_HOUR=17
OUT_MIN=00
OUT_SEC=00

# Read in command-line parameters
idle = True
port = '8443'
ignore_connections = False
try:
    opts, args = getopt.getopt(sys.argv[1:], "ht:p:c", ["help","time=","port=","ignore-connections"])
    if len(opts) == 0:
        raise getopt.GetoptError("No input parameters!")
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(helpInfo)
            exit(0)
        if opt in ("-t", "--time"):
            time = int(arg)
        if opt in ("-p", "--port"):
            port = str(arg)
        if opt in ("-c", "--ignore-connections"):
            ignore_connections = True
except getopt.GetoptError:
    print(usageInfo)
    exit(1)

# Missing configuration notification
missingConfiguration = False
if not time:
    print("Missing '-t' or '--time'")
    missingConfiguration = True
if missingConfiguration:
    exit(2)


def is_idle(last_activity):
    last_activity = datetime.strptime(last_activity,"%Y-%m-%dT%H:%M:%S.%fz")
    if (datetime.now() - last_activity).total_seconds() > time:
        print('Notebook is idle. Last activity time = ', last_activity)
        return True
    else:
        print('Notebook is not idle. Last activity time = ', last_activity)
        return False


def get_notebook_name():
    log_path = '/opt/ml/metadata/resource-metadata.json'
    with open(log_path, 'r') as logs:
        _logs = json.load(logs)
    return _logs['ResourceName']



if H_now>OUT_HOUR and H_now<24:
    H_sec=(H_now - OUT_HOUR)*3600
    M_sec=(M_now - OUT_MIN)*60
    Sec=(S_now - OUT_SEC)
    Total_night_sec = H_sec + M_sec + Sec
    print("Total night sec is :",Total_night_sec)
    if Total_night_sec >= time:
        flag=1 
elif H_now>=0 & H_now<=IN_HOUR:
    H_sec=(IN_HOUR - H_now)*3600
    M_sec=(IN_MIN - M_now)*60
    Sec=(IN_SEC - S_now)
    Total_mrng_sec = H_sec + M_sec + Sec
    print("time (in sec) to enter into start time of business hours is : ",Total_mrng_sec)
    if Total_mrng_sec>=-60:
        flag=1

#we are interested in stopping the instance if it is idle for 'x' time outside the business hours.
if  flag==1: 
    # This is hitting Jupyter's sessions API: https://github.com/jupyter/jupyter/wiki/Jupyter-Notebook-Server-API#Sessions-API
    response = requests.get('https://localhost:'+port+'/api/sessions', verify=False)
    data = response.json()
    print("DATA is:",data)
    if len(data) > 0:
        for notebook in data:
            # Idleness is defined by Jupyter
            # https://github.com/jupyter/notebook/issues/4634
            print("detail INFO :",notebook)
            if notebook['kernel']['execution_state'] == 'idle':
                if not ignore_connections:
                    if notebook['kernel']['connections'] == 0:
                        if not is_idle(notebook['kernel']['last_activity']):
                            idle = False
                    else:
                        idle = False
                else:
                    if not is_idle(notebook['kernel']['last_activity']):
                        idle = False
            else:
                print('NOTE Notebook is not idle:', notebook['kernel']['execution_state'])
                idle = False
    else:
        client = boto3.client('sagemaker')
        uptime = client.describe_notebook_instance(
            NotebookInstanceName=get_notebook_name()
        )['LastModifiedTime']
        if not is_idle(uptime.strftime("%Y-%m-%dT%H:%M:%S.%fz")):
            idle = False
    
    if idle:
        print('Closing idle notebook')
        client = boto3.client('sagemaker')
        client.stop_notebook_instance(
            NotebookInstanceName=get_notebook_name()
        )
    else:
        print('Notebook not idle. Pass.')