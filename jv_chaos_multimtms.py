import os
import requests
import json
import time
# from multiprocessing import Pool
import multiprocessing as mp
import random
import subprocess
from influxdb import InfluxDBClient
from dateutil import parser
from datetime import datetime, timedelta
from itertools import repeat

IAAS = os.getenv("IAAS")
LATENCY = int(os.getenv("LATENCY"))
LOSS_PERCENTAGE = int(os.getenv("LOSS_PERCENTAGE"))
DURATION = int(os.getenv("DURATION"))
recurring_every = int(os.getenv("recurring_every"))
app_string = os.getenv("CF_Microservice")
try:
    app_list = app_string.split(',')
except:
    pass

Chaos_Action = os.getenv("Chaos_Action")
PASSWORD = os.getenv("PASSWORD")
tenant_name = os.getenv("TENANT")
BuildDetail = os.getenv("BuildReport")
WAIT_TIME = int(os.getenv("WAIT_TIME"))



worker_list = []
uuid_list = []
list_of_executions = []
list_of_guids = []

### multiprocessing with all the cores #####
# Refer - https://stackoverflow.com/questions/19086106/how-to-utilize-all-cores-with-python-multiprocessing
def init_worker(mps, fps, cut):
    global memorizedPaths, filepaths, cutoff
    global DG

    print("process initializing", mp.current_process())
    memorizedPaths, filepaths, cutoff = mps, fps, cut
    DG = 1##nx.read_gml("KeggComplete.gml", relabel = True)

def work(item):
    _all_simple_paths_graph(DG, cutoff, item, memorizedPaths, filepaths)

def _all_simple_paths_graph(DG, cutoff, item, memorizedPaths, filepaths):
    pass # print "doing " + str(item)

################################

def read_config():
    with open('config.json') as f:
        conf = json.load(f)
    return conf


config = read_config()

chaos_url = json.dumps(config[IAAS]['chaos_url']).strip('\"')
chaos_auth = json.dumps(config[IAAS]['chaos_auth']).strip('\"')
cf_oauth_url = json.dumps(config[IAAS]['cf_oauth_url']).strip('\"')
user = json.dumps(config[IAAS]['user']).strip('\"')
cf_base_url = json.dumps(config[IAAS]['cf_base_url']).strip('\"')
space_id = json.dumps(config[IAAS]['space_id']).strip('\"')
trm_url = json.dumps(config[IAAS]['trm_url']).strip('\"')
trm_oauth_url = json.dumps(config[IAAS]['trm_oauth_url']).strip('\"')
trm_basic_auth = json.dumps(config[IAAS]['trm_basic_auth']).strip('\"')
influx_db = json.dumps(config[IAAS]['influx_db']).strip('\"')
db_store = json.dumps(config[IAAS]['db_store']).strip('\"')


def trm_token():
    url = f"{trm_oauth_url}?grant_type=client_credentials"

    payload = {}
    files = {}
    headers = {
        "Authorization": f"Basic {trm_basic_auth}"
    }

    response = requests.request("GET", url, headers=headers, data=payload, files=files)

    # print(response.text)
    # print("\n")
    # print(type(response.text))
    res_in_dict = json.loads(response.text)
    return res_in_dict["access_token"]


def worker_name():
    trm_tokenid = trm_token()

    # tenant_name = "mc101"

    url = f"{trm_url}{tenant_name}/" \
          f"workersets/itw-{tenant_name}-0"

    payload = {}
    headers = {
        'Authorization': f'Bearer {trm_tokenid}'
        # 'Cookie': 'JTENANTSESSIONID_kr19bxkapa=hXwfyso6e1%2FiD%2BzG%2FmTvccGsC%2F0%2F2O89fpaXQYYhBOU%3D'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    tenant_info = json.loads(response.text)

    worker = tenant_info["workerApps"][0]["name"]

    print(f"The worker selected is - {worker}")
    return worker


def utc_to_ist(utc):
    timestamp = datetime.strptime(utc, '%Y-%m-%dT%H:%M:%S')
    # print(utc)
    IST = timestamp + timedelta(hours=5, minutes=30)
    # print(IST)
    return IST


def cf_oauth_token():
    url = f"{cf_oauth_url}/oauth/token"

    payload = f"grant_type=password&client_id=cf&client_secret=&username={user}&password={PASSWORD}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        # 'Cookie': 'JTENANTSESSIONID_kr19bxkapa=FPtRDK1dM3D1lD56pq9oAq9mvHn19ohxqXjClhqrbLI%3D; JSESSIONID=MzllOWRjMmMtZTFjNC00OTJiLTk2NDctMDFmMzQ2MjhiMzgz; __VCAP_ID__=5d5db63a-a273-474d-42af-3ebbfa1ae677'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    access_token = json.loads(response.text)["access_token"]

    return access_token


token = cf_oauth_token()


def get_app_guid(token, app):
    url = f"{cf_base_url}/v3/apps?page=1&per_page=1000&space_guids={space_id}&names={app}"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}'
        # 'Cookie': 'JTENANTSESSIONID_kr19bxkapa=FPtRDK1dM3D1lD56pq9oAq9mvHn19ohxqXjClhqrbLI%3D'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    guid = json.loads(response.text)["resources"][0]["guid"]

    return guid


# guid = get_app_guid()

def mapping(guid, app):
    url = f"{chaos_url}/api/v1/apps/{guid}/mapping"

    payload = {}
    headers = {
        'Authorization': f'Basic {chaos_auth}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(f"\nfor '{app}'\n{response.json()}")


def instance_state(token, app, guid, instance_impacted):
    global instance_status
    url = f"{cf_base_url}/v3/processes/{guid}/stats"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print(response.json())
    try:
        number_of_instances = len(response.json()["resources"])
        print(f"Number of instances in '{app}' is  - '{number_of_instances}'")
    except:
        pass
    try:
        instance_status = response.json()['resources'][instance_impacted]['state']
    except:
        pass

    return instance_status


def execution_len(guid):
    url = f"{chaos_url}/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': f'Basic {chaos_auth}'
    }

    response = requests.request("GET", url, headers=headers, data=payload).json()
    executions = ((len(response)))
    # print(f"Already existing executions are -{executions}")

    return executions


def execution_data(guid, app):
    url = f"{chaos_url}/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': f'Basic {chaos_auth}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print(response.json()[0])  # prints the latest execution

    executions = response.json()[0]

    executions["MTMS"] = app

    print(f"\nfor {app} - \n{executions}")

    execution_status = executions["apps"][0]["status"]

    instance_impacted = executions["apps"][0]["instance"]
    instance_state(token, app, guid, instance_impacted)

    if execution_status == "FINISHED" or execution_status == "RUNNING":
        t1 = time.time()

        while instance_state(token, app, guid, instance_impacted) != "RUNNING":

            infra_client = InfluxDBClient(f'{influx_db}', 8086, f'{db_store}')

            infra_client.switch_database(f'{db_store}')
            chaos_details = [
                {
                    "measurement": "MultiMTMS_Recurring_kill",
                    "tags": {
                        "CFMicroservice": executions["MTMS"],
                        "chaos_action": executions["kind"],
                        "az": executions["selector"]["azs"][0],
                        "IndexValue": executions["apps"][0]["instance"],
                        "Execution_status": executions["apps"][0]["status"],
                        "InstanceStartTime": utc_to_ist(executions["start_date"].split(".")[0]),
                        "BuildDetail": BuildDetail,
                        "IAAS": IAAS,
                        # "Performed_By": Performed_By

                    },
                    "fields": {
                        # "execution_data": str(executions),
                        "chaos": 1  # we will need to figure out as to what we need to add here and use it better
                    }
                }
            ]
            # print(chaos_details)

            if infra_client.write_points(chaos_details, protocol='json'):
                print("Chaos Data Insertion success")
                pass
            else:
                print("Chaos Data Insertion Failed")
                print(chaos_details)

        print("Instance is RUNNING")
        finish_time = time.localtime()
        converted_finish_time = time.strftime("%H:%M:%S", finish_time)
        print(f"The uptime is {converted_finish_time}")
        infra_client = InfluxDBClient(f'{influx_db}', 8086, f'{db_store}')

        infra_client.switch_database(f'{db_store}')
        chaos_details = [
            {
                "measurement": "MultiMTMS_Recurring_kill",
                "tags": {
                    "CFMicroservice": executions["MTMS"],
                    "chaos_action": executions["kind"],
                    "az": executions["selector"]["azs"][0],
                    "IndexValue": executions["apps"][0]["instance"],
                    "Execution_status": executions["apps"][0]["status"],
                    "InstanceStartTime": utc_to_ist(executions["start_date"].split(".")[0]),
                    "EndTime": converted_finish_time,
                    "BuildDetail": BuildDetail,
                    "IAAS": IAAS,
                    # "Performed_By": Performed_By

                },
                "fields": {
                    "execution_data": str(executions),
                    "chaos": 1  # we will need to figure out as to what we need to add here and use it better
                }
            }
        ]

        if infra_client.write_points(chaos_details, protocol='json'):
            print("Chaos Data Insertion success")
            pass
        else:
            print("Chaos Data Insertion Failed")
            print(chaos_details)

        t2 = time.time()
        RTO = t2 - t1
        print(f"RTO time - {RTO}")
    else:
        print("Execution failed")
        infra_client = InfluxDBClient(f'{influx_db}', 8086, f'{db_store}')

        infra_client.switch_database(f'{db_store}')
        chaos_details = [
            {
                "measurement": "MultiMTMS_Recurring_kill",
                "tags": {
                    "CFMicroservice": executions["MTMS"],
                    "chaos_action": executions["kind"],
                    "az": executions["selector"]["azs"][0],
                    "IndexValue": executions["apps"][0]["instance"],
                    "Execution_status": executions["apps"][0]["status"],
                    "InstanceStartTime": utc_to_ist(executions["start_date"].split(".")[0]),
                    "BuildDetail": BuildDetail,
                    "IAAS": IAAS,
                    # "Performed_By": Performed_By

                },
                "fields": {
                    "execution_data": str(executions),
                    "chaos": 1  # we will need to figure out as to what we need to add here and use it better
                }
            }
        ]
        # print(chaos_details)

        if infra_client.write_points(chaos_details, protocol='json'):
            print("Chaos Data Insertion success")
            pass
        else:
            print("Chaos Data Insertion Failed")
            print(chaos_details)

    print("Instance is RUNNING")

    # print(f"\n{executions}")
    #
    # try:
    #     print(f"no - of executions for '{app} -'{len(executions)}'")
    # except: pass
    #
    # return executions

    # execution_status = response.json()[0]["apps"][0]["status"]

    # print(execution_status)

    # if execution_status == "FAILED":
    #     print(f"No instance of {app} exists in {ZONE}")
    #     print(f"The current mapping of instances are as below:\n{mapping()}")
    #     return execution_status
    # else:
    #     time.sleep(360)
    #     return execution_status


def delete_task(uuid, app):
    url = f"{chaos_url}/api/v1/tasks/{uuid}"

    payload = {}
    headers = {
        'Authorization': f'Basic {chaos_auth}'
    }

    response = requests.request("DELETE", url, headers=headers, data=payload)

    print(response.status_code)

    if response.status_code == 200:
        print(f"\ntask - {uuid} for {app} deleted successfully")
    else:
        print(f"\nplease check the task {uuid} for {app}- in the dashboard and cleanup")

    return response.status_code


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

        url = f"{chaos_url}/api/v1/apps/{guid}/mapping"

        payload = {}

        headers = {
            'Authorization': f"Basic {chaos_auth}"
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


def execution_details(guid):
    url = f"{chaos_url}/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': f"Basic {chaos_auth}"
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    result = json.loads(response.text)[0]

    print(json.dumps(result, indent=2))


def execution_details_plus_push_to_influx(app, guid, chaos_field):
    # guid = get_app_guid(token, app)

    url = f"{chaos_url}/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': f"Basic {chaos_auth}"
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    result = json.loads(response.text)[0]

    # print(json.dumps(result, indent=2))

    # data = response.json()
    infra_client = InfluxDBClient(f'{influx_db}', 8086, f'{db_store}')

    infra_client.switch_database(f'{db_store}')

    chaos_action_performed = result["kind"]
    # print(f"\nchaos action performed - {chaos_action_performed}")
    az_impacted = result["selector"]["azs"][0]
    # print(f"az impacted - {az_impacted}")
    app_impacted = app
    instance_impacted = result["apps"][0]["instance"]
    # print(f"instance impacted - {instance_impacted}")
    start_of_chaos_action = result["start_date"].split(".")[0]
    # print(start_of_chaos_action)
    test_time = datetime.strptime(start_of_chaos_action, '%Y-%m-%dT%H:%M:%S')
    # print(test_time)
    # end_of_chaos_action = result["end_date"].split(".")[0]
    end_of_chaos_action = str(test_time + timedelta(hours=5, minutes=30, seconds=DURATION))
    # print(end_of_chaos_action)

    chaos_details = [
        {
            "measurement": "InstanceCrashDetails",
            "tags": {
                "CFMicroservice": app_impacted,
                "chaos_action": chaos_action_performed,
                "az": az_impacted,
                "IndexValue": instance_impacted,
                "InstanceStartTime": utc_to_ist(start_of_chaos_action),
                # "InstanceEndTime": utc_to_ist(end_of_chaos_action),
                "InstanceEndTime": end_of_chaos_action,
                "BuildDetail": BuildDetail,
                "IAAS": IAAS,
                # "Performed_By": Performed_By

            },
            "fields": {
                "chaos": chaos_field  # we will need to figure out as to what we need to add here and use it better
            }
        }
    ]
    # print(chaos_details)

    if infra_client.write_points(chaos_details, protocol='json'):
        print("Chaos Data Insertion success")
        pass
    else:
        print("Chaos Data Insertion Failed")
        print(chaos_details)


def app_state(token, app, guid):
    url = f"{cf_base_url}/v3/processes/{guid}/stats"

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


def crash(CF_Microservice, ZONE):
    url = f"{chaos_url}/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 50,
            "azs": [
                ZONE
            ]
        },
        "kind": "KILL",
        "repeatability": "ONCE"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Basic {chaos_auth}"
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))


def app_scaling(CF_Microservice):
    no_of_apps = len(app_list)
    print(f"you have selected {no_of_apps} apps to scale down.They are - {app_list}")

    subprocess.run(
        f'cf login -a https://api.cf.sap.hana.ondemand.com -o "CPI-Global-Canary_aciat001"  -s prov_eu10_aciat001 -u prism@global.corp.sap -p {PASSWORD}')

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


def delay(CF_Microservice, guid, ZONE):

    no_of_execution = (execution_len(guid))
    expected_executions = no_of_execution + 1

    url = f"{chaos_url}/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 50,

            "azs": [
                ZONE
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
        'Authorization': f"Basic {chaos_auth}"
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))

    # guid = get_app_guid(token, CF_Microservice)
    #
    # print(f"The guid for '{CF_Microservice}' is '{guid}'")
    #
    # time.sleep(DURATION + 90)

    while no_of_execution != expected_executions:
        # print("No other executions found")
        no_of_execution = execution_len(guid)
        time.sleep(5)

    # execution_details_plus_push_to_influx(CF_Microservice, guid, LATENCY)
    # app_state(token, CF_Microservice, guid)

    start_time = time.time()

    while time.time() < (start_time + DURATION):
        begin_time = time.time()
        execution_details_plus_push_to_influx(CF_Microservice, guid, LATENCY)



def loss(CF_Microservice, guid, ZONE):

    no_of_execution = (execution_len(guid))
    expected_executions = no_of_execution + 1

    url = f"{chaos_url}/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 50,

            "azs": [
                ZONE
            ]
        },
        "kind": "LOSS",
        "config": {
            "percentage_loss": LOSS_PERCENTAGE
        },
        "repeatability": "ONCE",
        "duration": DURATION
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Basic {chaos_auth}"
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))

    while no_of_execution != expected_executions:
        # print("No other executions found")
        no_of_execution = execution_len(guid)
        time.sleep(5)

    # execution_details_plus_push_to_influx(CF_Microservice, guid, LATENCY)
    # app_state(token, CF_Microservice, guid)

    start_time = time.time()

    while time.time() < (start_time + DURATION):
        begin_time = time.time()
        execution_details_plus_push_to_influx(CF_Microservice, guid, LOSS_PERCENTAGE)


def recurring_kill(CF_Microservice, guid, ZONE):
    # guid = get_app_guid(token, app)
    # mapping(guid, app)
    no_of_execution = (execution_len(guid))
    expected_executions = no_of_execution + 1

    # utc_time = datetime.utcnow()
    # print(f"the utc time now is - {utc_time}")
    url = f"{chaos_url}/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 50,
            "azs": [
                ZONE
            ]
        },
        "cron": f"*/{recurring_every} * * * *",
        "kind": "KILL",
        "repeatability": "RECURRING"
    })
    headers = {
        'Authorization': f'Basic {chaos_auth}',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))

    uuid = response.json()["uuid"]

    print(uuid)

    uuid_list.append(uuid)

    while no_of_execution != expected_executions:
        # print("No other executions found")
        no_of_execution = execution_len(guid)
        time.sleep(5)

    start_time = time.time()

    while time.time() < (start_time + DURATION):
        begin_time = time.time()
        execution_data(guid, CF_Microservice)
        end_time = time.time()
        total_exec_time = end_time - begin_time
        print(f"Total Execution time is - {total_exec_time}")
        # print("App state - IMMEDIATELY post execution -")
        # app_state(token, CF_Microservice, guid)
        # time.sleep(sleep_time)
        # print(f"App state {sleep_time}sec post execution -")
        # app_state(token, CF_Microservice, guid)
        time.sleep(((recurring_every * 60) + 2) - total_exec_time)
        # mapping(guid, CF_Microservice)

    delete_task(uuid, CF_Microservice)

    print("The final mapping of all the instances are are below - \n")
    mapping(guid, CF_Microservice)


if __name__ == '__main__':

    config = read_config()

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
    except:
        app_array = worker_list  # when there are no MTMS entered only worker list needs to be taken and executed

    # time.sleep(60)
    # time.sleep(WAIT_TIME)
    ZONE = get_zone()

    t1 = time.time()

    if Chaos_Action == "DELAY":
        p1 = mp.Pool()
        guid_list = p1.starmap(get_app_guid, zip(repeat(token),
                                                 app_array))
        print(guid_list)
        p1.close()
        p1.join()

        time.sleep(WAIT_TIME)

        m = mp.Manager()
        memorizedPaths = m.dict()
        filepaths = m.dict()
        cutoff = 1  ##
        # use all available CPUs
        p = mp.Pool(initializer=init_worker, initargs=(memorizedPaths,
                                                       filepaths,
                                                       cutoff))
        degreelist = range(1)  ##
        for _ in p.imap_unordered(work, degreelist, chunksize=5000):
            result = p.starmap(delay, zip(app_array, guid_list, repeat(ZONE)))
        p.close()
        p.join()

    elif Chaos_Action == "KILL":
        time.sleep(WAIT_TIME)
        p = mp.Pool()
        result = p.starmap(crash, zip(app_array, repeat(ZONE)))
        p.close()
        p.join()
    elif Chaos_Action == "SCALE":
        time.sleep(WAIT_TIME)
        p = mp.Pool()
        result = p.map(app_scaling, app_array)
        p.close()
        p.join()

    elif Chaos_Action == "LOSS":
        p1 = mp.Pool()
        guid_list = p1.starmap(get_app_guid, zip(repeat(token),
                                                 app_array))
        print(guid_list)
        p1.close()
        p1.join()

        time.sleep(WAIT_TIME)

        m = mp.Manager()
        memorizedPaths = m.dict()
        filepaths = m.dict()
        cutoff = 1  ##
        # use all available CPUs
        p = mp.Pool(initializer=init_worker, initargs=(memorizedPaths,
                                                       filepaths,
                                                       cutoff))
        degreelist = range(1)  ##
        for _ in p.imap_unordered(work, degreelist, chunksize=5000):
            result = p.starmap(loss, zip(app_array, guid_list, repeat(ZONE)))
        p.close()
        p.join()


    elif Chaos_Action == "RECURRING_KILL":
        p1 = mp.Pool()
        guid_list = p1.starmap(get_app_guid, zip(repeat(token),
                                                 app_array))  # https://stackoverflow.com/questions/5442910/how-to-use-multiprocessing-pool-map-with-multiple-arguments
        print(guid_list)
        p1.close()
        p1.join()

        # p2 = Pool()
        # mapping_pool = p2.starmap(mapping, zip(guid_list, app_array))
        # p2.close()
        # p2.join()
        #
        # p3 = Pool()
        # app_state_pool = p3.starmap(app_state, zip(repeat(token), app_array, guid_list))
        # p3.close()
        # p3.join()

        # ZONE = get_zone()

        # p4 = Pool()
        # result = p4.starmap(recurring_kill, zip(app_array, guid_list, repeat(ZONE)))
        # p4.close()
        # p4.join()

        m = mp.Manager()
        memorizedPaths = m.dict()
        filepaths = m.dict()
        cutoff = 1  ##
        # use all available CPUs
        p = mp.Pool(initializer=init_worker, initargs=(memorizedPaths,
                                                       filepaths,
                                                       cutoff))
        degreelist = range(1)  ##
        for _ in p.imap_unordered(work, degreelist, chunksize=5000):
            result = p.starmap(recurring_kill, zip(app_array, guid_list, repeat(ZONE)))
        p.close()
        p.join()

