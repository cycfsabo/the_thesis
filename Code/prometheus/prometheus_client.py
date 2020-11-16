import json
import requests
from pyrfc3339 import generate, parse
import datetime
import pytz


#interval(minute)
#step(second)
prometheus_server = 'http://192.168.191.219:31941'
def get_period_time(interval):
    period = dict()
    start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=interval)
    start_time = generate(start_time.replace(tzinfo=pytz.utc))
    end_time = generate(datetime.datetime.utcnow().replace(tzinfo=pytz.utc))
    period['start'] = start_time
    period['end'] = end_time
    return period

def get_cpu_time_series_data(interval, step, namespaces=["default","mosquitto"]):
    period = get_period_time(interval)
    start = period['start']
    end = period['end']
    step = str(step)
    step += 's'
    range = '&start='+start+'&end='+ end +'&step='+step
#    query = 'sum(namespace:kube_pod_container_resource_requests_cpu_cores:sum)'
    query = '0'
    for i in namespaces:
        query += '--sum(namespace:kube_pod_container_resource_requests_cpu_cores:sum{namespace='+'"'+i+'"'+'})'
    
    query += range
#192.168.191.219 is monitoring-node's IP
    url = prometheus_server+'/api/v1/query_range?query='+query
    response = requests.get(url)
    response = json.loads(response.text)
    timeseries_data = response['data']['result'][0]['values']
    return timeseries_data

def get_memory_time_series_data(interval, step, namespaces=["default","mosquitto"]):
    period = get_period_time(interval)
    start = period['start']
    end = period['end']
    step = str(step)
    step += 's'
    range = '&start='+start+'&end='+ end +'&step='+step
    query = '0'
    for i in namespaces:
        query += '--sum(namespace:kube_pod_container_resource_requests_memory_bytes:sum{namespace='+'"'+i+'"'+'})'
    
    query += range
#192.168.191.219 is monitoring-node's IP
    url = prometheus_server+'/api/v1/query_range?query='+query
    response = requests.get(url)
    response = json.loads(response.text)
    timeseries_data = response['data']['result'][0]['values']
    return timeseries_data


def get_average_resource_request_data_by_minute(interval, step, namespaces=["default","mosquitto"]):
    resource_request = dict()
    resource_request['cpu'] = create_average_request_data_between_two_points(get_cpu_time_series_data(interval=interval, step=step, namespaces=namespaces))
    resource_request['memory'] = create_average_request_data_between_two_points(get_memory_time_series_data(interval=interval, step=step, namespaces=namespaces))
    return resource_request

# calculate average between 2 point.
# Unit can be 1 minute     
def create_average_request_data_between_two_points(data:list):
    new_data = []
    for i in range(1,len(data)):
	    new_data.append((float(data[i-1][1]) + float(data[i][1]))/2)
    return new_data


#print(get_cpu_time_series_data(interval=5,step=60))
#print(get_memory_time_series_data(interval=5,step=60))

#print(get_average_resource_request_data_by_minute(interval=5, step=60, namespaces=["default","mosquitto"]))