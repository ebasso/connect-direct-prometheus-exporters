#!/usr/bin/env python3

import base64
import time
import argparse
from prometheus_client import start_http_server, Gauge, Counter
from prometheus_client.core import CollectorRegistry
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout

DEBUG=True

# Global variable to hold signon data
signon_data = None

# Creates the registry
registry = CollectorRegistry()

# Defines the metrics
ibm_cd_hold_total = Gauge(
    'ibm_cd_processes_hold_total',
    'Total processes in HOLD state',
    registry=registry
)

ibm_cd_wait_total = Gauge(
    'ibm_cd_processes_wait_total',
    'Total processes in WAIT state',
    registry=registry
)

ibm_cd_timer_total = Gauge(
    'ibm_cd_processes_timer_total',
    'Total processes in TIMER state',
    registry=registry
)

ibm_cd_exec_total = Gauge(
    'ibm_cd_processes_exec_total',
    'Total processes in EXEC state',
    registry=registry
)

ibm_cd_process_count = Gauge(
    'ibm_cd_process_count',
    'Count of specific processes in HOLD or WAIT',
    ['process_name'],
    registry=registry
)

ibm_cd_scrape_errors = Counter(
    'ibm_cd_scrape_errors_total',
    'Total errors when collecting IBM Connect:Direct metrics',
    registry=registry
)



def signon(cdws_config):
    url = f'{cdws_config["server"]}/cdwebconsole/svc/signon'
    plain_credentials = cdws_config["user"] + ":" + cdws_config["password"]
    encoded_credentials = base64.b64encode(plain_credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json; charset=utf-8",
        "X-XSRF-TOKEN": "Y2hlY2tpdA==",  # do not change, fixed for the first time
        "Cache-Control": "no-cache"
    }

    json = {
        "ipAddress": cdws_config["node_ipaddress"],
        "port": int(cdws_config["node_port"]),
        "protocol": cdws_config["node_protocol"]  # Change to "TLS1.2" or "TLS1.3" as needed
    }

    response = requests.post(url, headers=headers, json=json, verify=False)

    if (response.status_code != 200):
        print('signon: Failed = ', response.json())
        return None

    print('signon: OK')

    # self.authorization = response.headers.get('Authorization')
    # self.cookie = response.headers.get('Set-Cookie')
    # if self.cookie:
    #     cookies = self.cookie.split(';')
    #     for cookie in cookies:
    #         if cookie.strip().startswith('XSRF-TOKEN='):
    #             self.x_xsrf_token = cookie.split('=')[1]
    #             break


def signout(cdws_config, signon_data):
    url = f'{cdws_config["server"]}/cdwebconsole/svc/signout'
    headers = {
        "Accept": "application/json", "Content-Type": "application/json", "X-XSRF-TOKEN": signon_data["_csrf"],
        "Authorization": signon_data["authorization"], "Cookie": signon_data["set-cookie"]
    }
    json = {'userAccessToken': signon_data}

    response = requests.delete(url=url, headers=headers, json=json, verify=False)
    if response.ok:
        print("signout: OK ")
    else:
        print("signout: Failed = " + response.text)


def tcq_metrics(cdws_config, signon_data):
    headers = {
        "Accept": "application/json", "Content-Type": "application/json", "X-XSRF-TOKEN": signon_data["_csrf"],
        "Authorization": signon_data["authorization"], "Cookie": signon_data["set-cookie"]
    }
    url = f"{cdws_config['server']}/cdwebconsole/svc/processcontrolcriteria?queue=ALL"
    try:
        response = requests.get(url=url, headers=headers,
                                timeout=(30, 30), verify=False)
    except ConnectTimeout:
        return False
    except ReadTimeout:
        return False
    except Exception:
        return False
    if response.ok:
        return response.text
    return False


def collect_metrics(cdws_config, signon_data):
    """Collects IBM Connect:Direct metrics and updates Prometheus metrics"""
    try:
        selpro_output = tcq_metrics(cdws_config, signon_data)
        if selpro_output is False:
            raise Exception("Failed to retrieve TCQ metrics")

        if DEBUG:
            print(f"[DEBUG] selpro_output: \n[{selpro_output}]\n")
        
        # Counts HOLD occurrences
        count_hold = selpro_output.count('HOLD')
        ibm_cd_hold_total.set(count_hold)
        print(f"[INFO] Processes in HOLD: {count_hold}")

        # Counts WAIT occurrences
        count_wait = selpro_output.count('WAIT')
        ibm_cd_wait_total.set(count_wait)
        print(f"[INFO] Processes in WAIT: {count_wait}")

        # Counts TIMER occurrences
        count_timer = selpro_output.count('TIMER')
        ibm_cd_timer_total.set(count_timer)
        print(f"[INFO] Processes in TIMER: {count_timer}")

        # Counts EXEC occurrences
        count_exec = selpro_output.count('EXEC')
        ibm_cd_exec_total.set(count_exec)
        print(f"[INFO] Processes in EXEC: {count_exec}")
            
    except Exception as e:
        print(f"[ERROR] Failed to collect metrics: {e}")
        ibm_cd_scrape_errors.inc()

def main():
    """Starts the Prometheus exporter"""
    parser = argparse.ArgumentParser(description="IBM Connect:Direct Prometheus Exporter")
    parser.add_argument('--cdws_server', required=True, help='IBM Connect:Direct Web Services server URL. Sample: https://localhost:9443')
    parser.add_argument('--cdws_user', required=True, help='IBM Connect:Direct Web Services username')
    parser.add_argument('--cdws_pw', required=True, help='IBM Connect:Direct Web Services password')
    parser.add_argument('--node', required=True, help='IBM Connect:Direct Web Services node')
    parser.add_argument('--node_ipaddress', required=True, help='IBM Connect:Direct Web Services node')
    parser.add_argument('--node_port', default="1363", help='IBM Connect:Direct Web Services node')
    parser.add_argument('--node_protocol', default="TLS1.3", help='IBM Connect:Direct Web Services node')

    parser.add_argument('--port', type=int, default=9400, help='Port to listen on')
    parser.add_argument('--interval', type=int, default=60, help='Scrape interval in seconds')
    args = parser.parse_args()

    port = args.port
    interval = args.interval
    cdws_config = {
        "server": args.cdws_server,
        "user": args.cdws_user,
        "password": args.cdws_pw,
        "node": args.node,
        "node_ipaddress": args.node_ipaddress,
        "node_port": args.node_port,
        "node_protocol": args.node_protocol
    }

    print(f"[INFO] Starting IBM Connect:Direct Prometheus Exporter on port {port}")
    print(f"[INFO] Collection interval: {interval} seconds")
    print(f"[INFO] CDWS server: {cdws_config['server']}")
    print(f"[INFO] CDWS user: {cdws_config['user']}")
    
    if not cdws_config['server']:
        print("[ERROR] Connect:Direct Web Services server URL is required")
        exit(1)
    
    # Starts the Prometheus HTTP server
    start_http_server(port, registry=registry)
    
    signon_data = signon(cdws_config)
    if signon_data is None:
        raise Exception("Signon failed")
    # Infinite loop to collect metrics
    while True:
        print(f"\n[INFO] Collecting metrics at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        collect_metrics(cdws_config, signon_data)
        time.sleep(interval)

    signout(cdws_config, signon_data)

if __name__ == '__main__':
    main()