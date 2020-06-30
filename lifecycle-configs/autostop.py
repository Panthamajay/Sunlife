import requests
from datetime import datetime
import getopt, sys
import urllib3
import boto3
import json

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


x = datetime.now()
print("CURRENT Time is : ",x)
H_now=x.hour
M_now=x.minute
S_now=x.second

OUT_HOUR=12
OUT_MIN=40
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


H_sec=(H_now - OUT_HOUR)*3600
M_sec=(M_now - OUT_MIN)*60
Sec=(S_now - OUT_SEC)
Total_sec = H_sec + M_sec + Sec
if  Total_sec > time : 
    # This is hitting Jupyter's sessions API: https://github.com/jupyter/jupyter/wiki/Jupyter-Notebook-Server-API#Sessions-API
    response = requests.get('https://localhost:'+port+'/api/sessions', verify=False)
    data = response.json()
    print("DATA is:",data)
    if len(data) > 0:
        print("ëntered into len func")
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