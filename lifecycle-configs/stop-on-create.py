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

print("Time is : ",x)

def get_notebook_name():
    log_path = '/opt/ml/metadata/resource-metadata.json'
    with open(log_path, 'r') as logs:
        _logs = json.load(logs)
    return _logs['ResourceName']



print('Closing idle notebook')
client = boto3.client('sagemaker')
client.stop_notebook_instance(
    NotebookInstanceName=get_notebook_name()
   )