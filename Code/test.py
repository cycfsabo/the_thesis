import os
from ostack import openstack_client
from k8s import k8s_client
from prometheus import prometheus_client
import time, threading
import datetime
from threading import Lock
lock = Lock()

authen_op = openstack_client.authentication()
last_time_scale_up = datetime.datetime.utcnow()
last_created_server = ''

INSTANCE_PREFIX = "worker-node-"

def scale_up(required_resource: dict):
    # TODO: check and aquire scale lock
    name_server = openstack_client.create_server(authen_op, name=INSTANCE_PREFIX, vcpus=required_resource['cpu'], ram=1224, disk=15)
    #k8s_client.add_label(name_server,'type','run-app')    
    # TODO: release scale lock after success
    return name_server

def scale_down(server_info, name_filter=INSTANCE_PREFIX):
#    server_info = openstack_client.scale_down_instance(authen_op)
    # TODO: check and aquire scale lock

    # TODO: handle filter instance to scale down with prefix
    if server_info:
        print('Start scaling down...')
        instance_name = server_info['name']
        instance_id = server_info['id']
        # TODO: handle all namespace (except kube-system, monitoring)
        namespace = 'default'

#cordon node in k8s cluster
        if k8s_client.cordon_node(instance_name,'true') == True:
            print(instance_name+' cordoned')
        else:
            print('Something is wrong ???')

#list all pods running on this instance
#        pods = k8s_client.list_pods_on_node(instance_name,namespace)

#evict all pods running on this instance
#        if pods:
#            for pod in pods:
#                print('evict pod' + pod['podname'] + " " + k8s_client.evict_pod(pod['podname'],namespace)['status'])
#        else:
#            print('The number of pods is 0')

#shutdown this instance
#        time.sleep(10)
        openstack_client.stop_instance(authen_op,instance_id)
        print(instance_name+' is stopped')
    # TODO: release scale lock after success


def get_loads(type="cpu",interval=10, step=10,namespaces=["default","mosquitto"]):
    """
    return timeseries_load: list(map({time: load}))
    """
    #loads = prometheus_client.get_cpu_time_series_data(interval,step)
    loads = prometheus_client.get_average_resource_request_data_by_minute(interval=interval,step=step,namespaces=namespaces)
    return loads

def predict(loads):
    """
    predict required resource based on loads in namespaces (`default`,`mosquitto`)
    return required_resource map({"cpu": "", "mem": ""})
    """
    spec = dict()
    spec["cpu"] = "1"
    spec["mem"] = "1224"
    return spec

def has_pending_pods(namespaces=["default","mosquitto"]):
    # TODO: get pending pods
    for ns in namespaces:
        if k8s_client.check_pending_pods(ns) == True:
            #print(ns)
            return True
    return False


#print(has_pending_pods())

def node_has_pod(instance_name, namespaces=["default","mosquitto"]):
#    list all pods running on this instance
    count = 0
    for ns in namespaces:
        if len(k8s_client.list_pods_on_node(instance_name,ns)) > 0:
            count = count + 1
    return count > 0

def list_free_servers():
    free_servers = []
    servers_list = openstack_client.list_servers(authen_op)
    for sv in servers_list:
        if node_has_pod(sv,namespaces=["default","mosquitto"]) == False:
            free_servers.append(sv)
    return free_servers









def main_checker():
    lock.acquire()
    try:
        # check each interval to perform action, i.e. scale up/down
        # step, interval unit = second
        global last_created_server
        global last_time_scale_up 
        loads = get_loads(interval=5, step=60)
        print(loads)
        print('has pending pod ?')
        print(has_pending_pods())
        print(last_created_server + ' is ready ?')
        print(k8s_client.is_node_ready(last_created_server))
        if has_pending_pods():
            last_time_scale_up = datetime.datetime.utcnow()

        if has_pending_pods() and k8s_client.is_node_ready(last_created_server):
            print(last_created_server)
            required_resource = predict(loads)
            name_server = scale_up(required_resource)
            
            print(f"Scaled up: Server = {name_server}")
            #if k8s_client.is_node_ready(last_created_server):
            #last_time_scale_up = datetime.datetime.utcnow()
            last_created_server = ''
            last_created_server += name_server 
            
        print('Last scaling up time:')
        print(last_time_scale_up)
             
            
        free_servers = list_free_servers()
        
        print("free servers:")
        print(free_servers)
        if len(free_servers) > 0 and last_created_server != '':
            SCALE_DOWN_WAIT_TIME = 600
            print("Time remaining:")
            print(600 - (datetime.datetime.utcnow() - last_time_scale_up).total_seconds())
            if (datetime.datetime.utcnow() - last_time_scale_up).total_seconds() > SCALE_DOWN_WAIT_TIME:
                for sv in free_servers:
                    print("Delete " + sv)
                    k8s_client.delete_node(sv)
                    server_id = openstack_client.get_server_id_by_name(authen_op,sv)
                    openstack_client.delete_server(authen_op,server_id)
    finally:
        lock.release()




def test():
    MAIN_CHECK_INTERVAL = 10
    main_checker_thread = threading.Timer(MAIN_CHECK_INTERVAL, test)
    main_checker_thread.start()
    main_checker()
    main_checker_thread.join()

def main():
    # TODO: update interval values to appropriate values
    test()




#print(get_loads(interval=240,step=480))

if __name__ == "__main__":
    main()