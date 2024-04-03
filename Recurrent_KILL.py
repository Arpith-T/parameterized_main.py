import requests
import json
import time
from influxdb import InfluxDBClient
from multiprocessing import Pool

chaos_url = "https://chaosmonkey.cf.eu21.hana.ondemand.com"
app = "it-co"
# app_array = ["it-co", "it-gb"]
ZONE = "z1"
chaos_action = "KILL"
cf_oauth_url = "uaa.cf.eu21.hana.ondemand.com"
password = "***"
user = "prism@global.corp.sap"
# cf_base_url = "api.cf.sap.hana.ondemand.com"
cf_base_url = "api.cf.eu21.hana.ondemand.com"
space_id = "ab1eef62-e8f3-4590-8a0b-eb3a932f4b47"


def cf_token(cf_oauth_url):
    url = f"https://{cf_oauth_url}/oauth/token"

    payload = f"grant_type=password&client_id=cf&client_secret=&username={user}&password={password}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'JSESSIONID=OGRjZWE1ZTctYTBmYi00NDkyLWFhMDYtYmYxNWFhMzcyMDNl; __VCAP_ID__=0c66b875-6cc3-4244-7c39-a126d48ad65a'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    access_token = json.loads(response.text)["access_token"]
    # print(access_token)
    return access_token


token = cf_token(cf_oauth_url)


def get_app_guid(token, app):
    url = f"https://{cf_base_url}/v3/apps?page=1&per_page=1000&space_guids={space_id}&names={app}"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}',
        'Cookie': 'JTENANTSESSIONID_kr19bxkapa=FPtRDK1dM3D1lD56pq9oAq9mvHn19ohxqXjClhqrbLI%3D'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    guid = json.loads(response.text)["resources"][0]["guid"]

    return guid

guid = get_app_guid(token,app)


def mapping():

    url = f"{chaos_url}/api/v1/apps/{guid}/mapping"

    payload = {}
    headers = {
        'Authorization': 'Basic c2Jzc19sMHNweGZ2ZGVmaGQ4ZDNnNTl0emVieDFrdGZraWNhM3Fkc2pxaWVuYmNteDJtdmpscmllc2Vrb3RjaGY4aHZ3bXp3PTphYV9UQTdMRFgvdjU1a3pLZElSUW1KTjh6bzRXaEU9'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(f"\n{response.json()}")


def recurring_kill():
    url = f"{chaos_url}/api/v1/tasks"

    payload = json.dumps({
        "app_name": app,
        "selector": {
            "percentage": 50,
            "azs": [
                ZONE
            ]
        },
        "cron": "*/5 * * * *",
        "kind": chaos_action,
        "repeatability": "RECURRING"
    })
    headers = {
        'Authorization': 'Basic c2Jzc19sMHNweGZ2ZGVmaGQ4ZDNnNTl0emVieDFrdGZraWNhM3Fkc2pxaWVuYmNteDJtdmpscmllc2Vrb3RjaGY4aHZ3bXp3PTphYV9UQTdMRFgvdjU1a3pLZElSUW1KTjh6bzRXaEU9',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = json.loads(response.text)

    print(json.dumps(result, indent=4))

    uuid = response.json()["uuid"]

    return uuid



def execution_data():
    url = f"{chaos_url}/api/v1/apps/{guid}/executions"

    payload = {}
    headers = {
        'Authorization': 'Basic c2Jzc19sMHNweGZ2ZGVmaGQ4ZDNnNTl0emVieDFrdGZraWNhM3Fkc2pxaWVuYmNteDJtdmpscmllc2Vrb3RjaGY4aHZ3bXp3PTphYV9UQTdMRFgvdjU1a3pLZElSUW1KTjh6bzRXaEU9'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.json()[0]) # prints the latest execution

    execution_status = response.json()[0]["apps"][0]["status"]

    # print(execution_status)

    if execution_status == "FAILED":
        print(f"No instance of {app} exists in {ZONE}")
        print(f"The current mapping of instances are as below:\n{mapping()}")
        return execution_status
    else:
        time.sleep(360)
        return execution_status


def delete_task(uuid):
    print()
    url = f"{chaos_url}/api/v1/tasks/{uuid}"

    payload = {}
    headers = {
        'Authorization': 'Basic c2Jzc19sMHNweGZ2ZGVmaGQ4ZDNnNTl0emVieDFrdGZraWNhM3Fkc2pxaWVuYmNteDJtdmpscmllc2Vrb3RjaGY4aHZ3bXp3PTphYV9UQTdMRFgvdjU1a3pLZElSUW1KTjh6bzRXaEU9'
    }

    response = requests.request("DELETE", url, headers=headers, data=payload)

    print(response.status_code)

    return response.status_code

# if __name__ == "__main__":
mapping()
start_time = time.time()
# p = Pool()
uuid = recurring_kill() # lets not worry about getting the uuid for now
# result = p.map(recurring_kill, app_array)
"""Note - even though the KILL task gets created the execution of it will happen in the multiples of 5 only since we have provided recurring every 5 mins. Ex - if a task gets created at 9.30AM the 1st execution of it will happen only at 9.35 and next at 9.40, ex-2 - if created at 9.33,the 1st execution will happen at 9.35"""
# p.close()
# p.join()



time.sleep(332)


# for app in app_array:
#     guid = get_app_guid(token, app)
execution = 1
for execution in range(1,4):
    print(f"This is exeuction no - {execution}\n")
    execution_data()
    execution += 1
    if execution <= 3:
        time.sleep(360)
        mapping()
    else:
        mapping()
        pass


print("chaos activity completed. proceed to delete the task")
if delete_task(uuid) == 200:
    print(f"The recurrent kill task is aborted after {execution-1} executions")



# execution_status = "FINISHED"
# while execution_status == "FINISHED":
#     execution_status = ""
#     if time.time() < (start_time + (20*60)):
#         execution_data()
#         execution_status = execution_data()

# print("chaos activity completed. proceed to delete the task")
# if execution_status == "FAILED":
#     time.sleep(30)
#     delete_task(uuid)



# def main():
#     recurring_kill()
#
#
# if __name__ == "__main__":
#     cf_token(cf_base_url)
