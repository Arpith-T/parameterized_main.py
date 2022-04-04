import os
import requests
import json
import time
from multiprocessing import Pool
import random
import subprocess
from influxdb import InfluxDBClient
from dateutil import parser
from datetime import datetime, timedelta

# LATENCY = int(os.getenv("LATENCY"))
# DURATION = int(os.getenv("DURATION"))
# app_string = os.getenv("CF_Microservice")
# try:
#     app_list = app_string.split(',')
# except: pass
#
# Chaos_Action = os.getenv("Chaos_Action")
# PASSWORD = os.getenv("PASSWORD")
# tenant_name = os.getenv("TENANT")
# BuildDetail = os.getenv("BuildReport")
WAIT_TIME = int(os.getenv("WAIT_TIME"))

LATENCY = 1000
DURATION = 60
app_list = []
Chaos_Action = "DELAY"
# Chaos_Action = "KILL"
# Chaos_Action = "SCALE"
PASSWORD = "Prisminfra529#5"
tenant_name = "mc103"
BuildDetail = "Test_BuildReport"
IAAS = "AWS"
Performed_By = "test123"
# az = os.getenv("AZ")

worker_list = []

def aciat001_trm_token():
    url = "https://aciat001.authentication.sap.hana.ondemand.com/oauth/token?grant_type=client_credentials"

    payload = {}
    files = {}
    headers = {
        'Authorization': 'Basic c2ItaXQhYjc2NDg6ZmIyMGZmYzktMDFjNy00ZTY2LTk2ODAtMjk3YzU3ZWY0ZTYzJEduMEtEeFYtd2Q4NTNTWTNJVXBjeElOSWU3UzhpRjZhZ3Jsdll0aXdhTE09'
    }

    response = requests.request("GET", url, headers=headers, data=payload, files=files)

    # print(response.text)
    # print("\n")
    # print(type(response.text))
    res_in_dict = json.loads(response.text)
    return res_in_dict["access_token"]

def worker_name():
    trm_token = aciat001_trm_token()

    # tenant_name = "mc101"

    url = f"https://it-aciat001-trm.cfapps.sap.hana.ondemand.com/api/trm/v1/tenants/{tenant_name}/" \
          f"workersets/itw-{tenant_name}-0"

    payload = {}
    headers = {
        'Authorization': f'Bearer {trm_token}',
        'Cookie': 'JTENANTSESSIONID_kr19bxkapa=hXwfyso6e1%2FiD%2BzG%2FmTvccGsC%2F0%2F2O89fpaXQYYhBOU%3D'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    tenant_info = json.loads(response.text)

    worker = tenant_info["workerApps"][0]["name"]

    print(f"The worker selected is - {worker}")
    return worker

if tenant_name == "":
    print("No Tenant selected for chaos action")
    app_array = app_list  # when no worker is selected, only MTMS should be executed
    print(app_array)
else:
    try:
        worker = worker_name()

        worker_list.append(worker)

        print(worker_list)


        app_array = app_list + worker_list

        print(app_array)
    except:
        print("No worker selected")
        pass
try:
    app_array = app_list + worker_list
except: app_array = worker_list  # when there are no MTMS entered only worker list needs to be taken and executed

# def convert_utc_ist(utc):
#     # utc = '2022-03-08T07:00:21.971538Z'  # or any date string of differing formats.
#     utc_time = parser.parse(utc)
#     # print(utc_time)
#     hours = 5.30
#     hours_added = datetime.timedelta(hours=hours)
#     ist_time = utc_time + hours_added
#     # print(ist_time)
#     return ist_time

def utc_to_ist(utc):
    timestamp = datetime.strptime(utc, '%Y-%m-%dT%H:%M:%S')
    # print(utc)
    IST = timestamp + timedelta(hours=5, minutes=30)
    # print(IST)
    return IST

def cf_oauth_token():
    url = "https://uaa.cf.sap.hana.ondemand.com/oauth/token"

    payload = f"grant_type=password&client_id=cf&client_secret=&username=prism@global.corp.sap&password={PASSWORD}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'JTENANTSESSIONID_kr19bxkapa=FPtRDK1dM3D1lD56pq9oAq9mvHn19ohxqXjClhqrbLI%3D; JSESSIONID=MzllOWRjMmMtZTFjNC00OTJiLTk2NDctMDFmMzQ2MjhiMzgz; __VCAP_ID__=5d5db63a-a273-474d-42af-3ebbfa1ae677'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    access_token = json.loads(response.text)["access_token"]

    return access_token

def get_app_guid(token, app):
    url = f"https://api.cf.sap.hana.ondemand.com/v3/apps?page=1&per_page=1000&space_guids=2c92d3e7-a833-4fbf-89e2-917c07cea220&names={app}"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}',
        'Cookie': 'JTENANTSESSIONID_kr19bxkapa=FPtRDK1dM3D1lD56pq9oAq9mvHn19ohxqXjClhqrbLI%3D'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    guid = json.loads(response.text)["resources"][0]["guid"]

    return guid

def get_zone():
    z1 = []
    z2 = []
    z3 = []
    zone_list = ["z1", "z2", "z3"]
    app_zones = []
    app_dict = {}  # https://stackoverflow.com/questions/23999801/creating-multiple-lists
    token = cf_oauth_token()
    # app_list = ["it-op-rest", "it-app"]

    # print(f"No of apps selected is - {len(app_list)}")

    for app in app_array:

        app_dict["zones_of_" + app] = []  # https://stackoverflow.com/questions/23999801/creating-multiple-lists
        guid = get_app_guid(token, app)

        url = f"https://chaosmonkey.cf.sap.hana.ondemand.com/api/v1/apps/{guid}/mapping"

        payload = {}

        headers = {
            'Authorization': 'Basic c2Jzc18rcGJnbmlvdjRpbGQxbGwydmp4dHVlbjl1dm90eXp6a3ZjdW1yenJtdG9jMXZnYmx6OWJlam11eDJtbGs2dXFncXYwPTphYV9EdFdCckRYL2ttdmY4cG5lR2diVHB4RDhHYTg9'
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        # print(response.json())

        # print(f"No. of instances - {len(response.json()['mapping'])}")

        app_z = response.json()

        # print(app_z["mapping"]["0"]["name"])

        for zone in range(0, len(response.json()["mapping"])):
            i = str(zone)

            # print(response.json()["mapping"][i]["name"])

            azs = response.json()["mapping"][i]["name"]

            # app_zones.append(azs)

            app_dict["zones_of_" + app].append(azs)

    # print(app_zones)

    print(app_dict)

    # TODO - list all the apps availble in the zones

    # for app in app_list:
    #     if "z1" in app_dict["zones_of_" + app]:
    #         z1.append(app)
    #     else:
    #         continue
    #     if "z2" in app_dict["zones_of_" + app]:
    #         z2.append(app)
    #     else:
    #         continue
    #     if "z3" in app_dict["zones_of_" + app]:
    #         z3.append(app)
    #
    # print(f"\n{z1}\n{z2}\n{z3}\n")

    for app in app_array:
        if "z1" in app_dict["zones_of_" + app]:
            z1.append(app)
    for app in app_array:
        if "z2" in app_dict["zones_of_" + app]:
            z2.append(app)
    for app in app_array:
        if "z3" in app_dict["zones_of_" + app]:
            z3.append(app)

    print(f"\nz1={z1}\nz2={z2}\nz3={z3}\n")

    # # TODO - REMOVING DUPLICATES - https://stackoverflow.com/questions/7961363/removing-duplicates-in-lists
    #
    # print("The final list after removing the duplicates, if any is as below- \n")
    # print(f"z1 = {list(dict.fromkeys(z1))}")
    # print(f"z2 = {list(dict.fromkeys(z2))}")
    # print(f"z3 = {list(dict.fromkeys(z3))}")
    #
    #
    # z1 = list(dict.fromkeys(z1))
    # z2 = list(dict.fromkeys(z2))
    # z3 = list(dict.fromkeys(z3))

    # TODO - Selecting the zone where all MTMS are present.

    if len(z1) == len(app_array):
        print("we will select 'z1' for chaos action")
        zone_to_be_used = "z1"
        return zone_to_be_used
    elif len(z2) == len(app_array):
        print("we will select 'z2' for chaos action")
        zone_to_be_used = "z2"
        return zone_to_be_used
    elif len(z3) == len(app_array):
        print("we will select 'z3' for chaos action")
        zone_to_be_used = "z3"
        return zone_to_be_used
    else:
        zone_to_be_used = random.choice(zone_list)
        print(zone_to_be_used)
        return zone_to_be_used

def crash(CF_Microservice):
    url = "https://chaosmonkey.cf.sap.hana.ondemand.com/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 50,
            "azs": [
                get_zone()
            ]
        },
        "kind": "KILL",
        "repeatability": "ONCE"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic c2Jzc18rcGJnbmlvdjRpbGQxbGwydmp4dHVlbjl1dm90eXp6a3ZjdW1yenJtdG9jMXZnYmx6OWJlam11eDJtbGs2dXFncXYwPTphYV9EdFdCckRYL2ttdmY4cG5lR2diVHB4RDhHYTg9'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))

def app_scaling(CF_Microservice):
    no_of_apps = len(app_list)
    print(f"you have selected {no_of_apps} apps to scale down.They are - {app_list}")

    subprocess.run(f'cf login -a https://api.cf.sap.hana.ondemand.com -o "CPI-Global-Canary_aciat001"  -s prov_eu10_aciat001 -u prism@global.corp.sap -p {PASSWORD}')

    for CF_Microservice in app_list:
        if CF_Microservice == "it-km-rest":
            print("\n")
            subprocess.run(f'cf us {CF_Microservice} it-scale-km')
            time.sleep(5)
            subprocess.run(f'cf scale {CF_Microservice} -i 2')
            print(f"scale down of {CF_Microservice} is done")
        elif CF_Microservice == "it-runtime-api":
            print("\n")
            subprocess.run(f'cf us {CF_Microservice} it-scale-runtime-api')
            time.sleep(5)
            subprocess.run(f'cf scale {CF_Microservice} -i 2')
            print(f"scale down of {CF_Microservice} is done")
        else:
            subprocess.run(f'cf scale {CF_Microservice} -i 2')
            print(f"scale down of {CF_Microservice} is done")

    time.sleep(DURATION)

    for CF_Microservice in app_list:
        subprocess.run(f'cf scale {CF_Microservice} -i 3')
        print(f"scale up of {CF_Microservice} is done")

def delay(CF_Microservice):
    url = "https://chaosmonkey.cf.sap.hana.ondemand.com/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 50,

            "azs": [
                get_zone()
            ]
        },
        "kind": "DELAY",
        "config": {
            "latency": LATENCY
        },
        "repeatability": "ONCE",
        "duration": DURATION
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic c2Jzc18rcGJnbmlvdjRpbGQxbGwydmp4dHVlbjl1dm90eXp6a3ZjdW1yenJtdG9jMXZnYmx6OWJlam11eDJtbGs2dXFncXYwPTphYV9EdFdCckRYL2ttdmY4cG5lR2diVHB4RDhHYTg9'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))

def execution_details(guid):
    url = f"https://chaosmonkey.cf.sap.hana.ondemand.com/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': 'Basic c2Jzc18rcGJnbmlvdjRpbGQxbGwydmp4dHVlbjl1dm90eXp6a3ZjdW1yenJtdG9jMXZnYmx6OWJlam11eDJtbGs2dXFncXYwPTphYV9EdFdCckRYL2ttdmY4cG5lR2diVHB4RDhHYTg9'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    result = json.loads(response.text)[0]

    print(json.dumps(result, indent=2))

def execution_details_plus_push_to_influx(app, guid):

    # guid = get_app_guid(token, app)

    url = f"https://chaosmonkey.cf.sap.hana.ondemand.com/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': 'Basic c2Jzc18rcGJnbmlvdjRpbGQxbGwydmp4dHVlbjl1dm90eXp6a3ZjdW1yenJtdG9jMXZnYmx6OWJlam11eDJtbGs2dXFncXYwPTphYV9EdFdCckRYL2ttdmY4cG5lR2diVHB4RDhHYTg9'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    result = json.loads(response.text)[0]

    print(json.dumps(result, indent=2))

    # data = response.json()
    infra_client = InfluxDBClient('hci-rit-prism-sel.cpis.c.eu-de-2.cloud.sap', 8086, 'arpdb')

    infra_client.switch_database('arpdb')

    chaos_action_performed = result["kind"]
    print(f"\nchaos action performed - {chaos_action_performed}")
    az_impacted = result["selector"]["azs"][0]
    print(f"az impacted - {az_impacted}")
    app_impacted = app
    instance_impacted = result["apps"][0]["instance"]
    print(f"instance impacted - {instance_impacted}")
    start_of_chaos_action = result["start_date"].split(".")[0]
    end_of_chaos_action = result["end_date"].split(".")[0]

    chaos_details = [
        {
            "measurement": "InstanceCrashDetails",
            "tags": {
                "CFMicroservice": app_impacted,
                "chaos_action": chaos_action_performed,
                "az": az_impacted,
                "IndexValue": instance_impacted,
                "InstanceStartTime": utc_to_ist(start_of_chaos_action),
                "InstanceEndTime": utc_to_ist(end_of_chaos_action),
                "BuildDetail": BuildDetail,
                "IAAS": IAAS,
                "Performed_By": Performed_By

            },
            "fields": {
                "chaos": 1  # we will need to figure out as to what we need to add here and use it better
            }
        }
    ]
    print(chaos_details)

    if infra_client.write_points(chaos_details, protocol='json'):
        print("Chaos Data Insertion success")
        pass
    else:
        print("Chaos Data Insertion Failed")
        print(chaos_details)

def app_state(token, app, guid):
    url = f"https://api.cf.sap.hana.ondemand.com/v3/processes/{guid}/stats"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print(response.json())
    try:
        number_of_instances = len(response.json()["resources"])
    except:
        pass

    print(f"Number of instances in '{app}' is  - '{number_of_instances}'")

    for i in range(0, number_of_instances):
        print(
            f"Instance - {response.json()['resources'][i]['index']} of {app} is {response.json()['resources'][i]['state']}")

if __name__ == '__main__':

    time.sleep(60)
    # time.sleep(WAIT_TIME)

    t1 = time.time()

    if Chaos_Action == "DELAY":
        p = Pool()
        result = p.map(delay, app_array)
        p.close()
        p.join()
    elif Chaos_Action == "KILL":
        p = Pool()
        result = p.map(crash, app_array)
        p.close()
        p.join()
    elif Chaos_Action == "SCALE":
        p = Pool()
        result = p.map(app_scaling, app_array)
        p.close()
        p.join()

    print("\n")
    print(f"this took: {time.time() - t1} ")
    time.sleep(DURATION + 90)
    # time.sleep(DURATION)
    token = cf_oauth_token()
    for app in app_array:
        guid = get_app_guid(token, app)
        # execution_details(guid)
        execution_details_plus_push_to_influx(app,guid)
        app_state(token,app,guid)

