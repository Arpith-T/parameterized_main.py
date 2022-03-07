import os
import requests
import json
import time
from multiprocessing import Pool
import random


# LATENCY = int(os.getenv("LATENCY"))
# DURATION = int(os.getenv("DURATION"))
# app_string = os.getenv("CF_Microservice")
# app_list = app_string.split(',')
# Chaos_Action = os.getenv("Chaos_Action")
# PASSWORD = os.getenv("PASSWORD")
# az = os.getenv("AZ")

LATENCY = 1000
DURATION = 30
app_list = ["it-gb", "it-km-rest", "it-op-rest", "it-co", "it-app"]
# Chaos_Action = "DELAY"
Chaos_Action = "KILL"
PASSWORD = "Prisminfra529#5"




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

    for app in app_list:

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

    for app in app_list:
        if "z1" in app_dict["zones_of_" + app]:
            z1.append(app)
    for app in app_list:
        if "z2" in app_dict["zones_of_" + app]:
            z2.append(app)
    for app in app_list:
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

    if len(z1) == len(app_list):
        print("we will select 'z1' for chaos action")
        zone_to_be_used = "z1"
        return zone_to_be_used
    elif len(z2) == len(app_list):
        print("we will select 'z2' for chaos action")
        zone_to_be_used = "z2"
        return zone_to_be_used
    elif len(z3) == len(app_list):
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


def app_state(token, app, guid):
    url = f"https://api.cf.sap.hana.ondemand.com/v3/processes/{guid}/stats"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print(response.json())

    number_of_instances = len(response.json()["resources"])

    print(f"Number of instances in '{app}' is  - '{number_of_instances}'")

    for i in range(0, number_of_instances):
        print(
            f"Instance - {response.json()['resources'][i]['index']} of {app} is {response.json()['resources'][i]['state']}")

if __name__ == '__main__':
    # app_list = ["it-gb", "it-km-rest", "it-op-rest", "it-co", "it-app"]

    t1 = time.time()
    p = Pool()
    if Chaos_Action == "DELAY":
        result = p.map(delay, app_list)
        p.close()
        p.join()
    elif Chaos_Action == "KILL":
        result = p.map(crash, app_list)
        p.close()
        p.join()

    print("\n")
    print(f"this took: {time.time() - t1} ")
    time.sleep(120)
    token = cf_oauth_token()
    for app in app_list:
        guid = get_app_guid(token, app)
        execution_details(guid)
        app_state(token,app,guid)

