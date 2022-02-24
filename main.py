import os
import requests
import json
import time
from multiprocessing import Pool
import random

LATENCY = int(os.getenv("LATENCY"))
DURATION = int(os.getenv("DURATION"))
# az = os.getenv("AZ")
ZONE = os.getenv("ZONE")
app_string = os.getenv("CF_Microservice")
app_list = app_string.split(',')
Chaos_Action = os.getenv("Chaos_Action")
PASSWORD = os.getenv("PASSWORD")




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


def crash(CF_Microservice):
    url = "https://chaosmonkey.cf.sap.hana.ondemand.com/api/v1/tasks"

    payload = json.dumps({
        "app_name": CF_Microservice,
        "selector": {
            "percentage": 100,
            "azs": [
                ZONE
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
            "percentage": 100,

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
    time.sleep(60)
    token = cf_oauth_token()
    for app in app_list:
        guid = get_app_guid(token, app)
        execution_details(guid)
