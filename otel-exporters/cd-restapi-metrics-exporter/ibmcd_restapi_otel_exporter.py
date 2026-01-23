#!/usr/bin/env python3

import base64
import time
import argparse
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import start_http_server
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEBUG=False
INTERVAL=60
LOCALPORT=9402

# Global variable to hold signon data
signon_data = None

# Setup OpenTelemetry
reader = PrometheusMetricReader()
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Create a meter
meter = metrics.get_meter(__name__)

# Create metrics
ibm_cd_hold_total = meter.create_up_down_counter(
    name='ibm_cd_processes_hold_total',
    description='Total processes in HOLD state',
    unit='1'
)

ibm_cd_wait_total = meter.create_up_down_counter(
    name='ibm_cd_processes_wait_total',
    description='Total processes in WAIT state',
    unit='1'
)

ibm_cd_timer_total = meter.create_up_down_counter(
    name='ibm_cd_processes_timer_total',
    description='Total processes in TIMER state',
    unit='1'
)

ibm_cd_exec_total = meter.create_up_down_counter(
    name='ibm_cd_processes_exec_total',
    description='Total processes in EXEC state',
    unit='1'
)

ibm_cd_scrape_errors = meter.create_counter(
    name='ibm_cd_scrape_errors_total',
    description='Total errors when collecting IBM Connect:Direct metrics',
    unit='1'
)

# Store current values for counters
current_values = {
    'hold': 0,
    'wait': 0,
    'timer': 0,
    'exec': 0
}


def signon(cdws_config):
    url = f'{cdws_config["cdws_server"]}/cdwebconsole/svc/signon'

    # Encode the credentials (username:password) in Base64 format.
    # The plain credentials are first converted to bytes using .encode(),
    # as Base64 encoding operates on byte data instead of string data.
    plain_credentials = f"{cdws_config['cd_username']}:{cdws_config['cd_password']}"
    encoded_credentials = base64.b64encode(plain_credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {encoded_credentials}",
        "X-XSRF-TOKEN": "Y2hlY2tpdA==",  # do not change, fixed for the first time
        "Cache-Control": "no-cache"
    }

    jsonBody = {
        "ipAddress": cdws_config["cd_ipaddress"],
        "port": int(cdws_config["cd_port"]),
        "protocol": cdws_config["cd_protocol"]  # Change to "TLS1.2" or "TLS1.3" as needed
    }

    try:
        response = requests.post(url, headers=headers, json=jsonBody, verify=False)
    except ConnectTimeout:
        print('[ERROR] signon: Connection timeout')
        return None
    except ReadTimeout:
        print('[ERROR] signon: Read timeout')
        return None
    except Exception as e:
        print(f'[ERROR] signon: Exception - {e}')
        return None

    if (response.status_code != 200):
        print('[ERROR] signon: Failed = ', response.json())
        return None

    print('[INFO] signon: OK')
    return response.headers


def signout(cdws_config, signon_data):
    url = f'{cdws_config["cdws_server"]}/cdwebconsole/svc/signout'
    headers = {
        "Accept": "application/json", "Content-Type": "application/json; charset=utf-8",
        "X-XSRF-TOKEN": signon_data["_csrf"], "Authorization": signon_data["authorization"]
    }
    # , "Cookie": signon_data["set-cookie"]
    jsonBody = {'userAccessToken': signon_data}

    try:
        response = requests.delete(url=url, headers=headers, json=jsonBody, verify=False)
    except ConnectTimeout:
        return False
    except ReadTimeout:
        return False
    except Exception:
        return False
    
    if response.ok:
        print("[INFO] signout: OK ")
    else:
        print("[ERROR] signout: Failed = " + response.text)


def tcq_metrics(cdws_config, signon_data):
    headers = {
        "Accept": "application/json", "Content-Type": "application/json; charset=utf-8",
        "X-XSRF-TOKEN": signon_data["_csrf"], "Authorization": signon_data["authorization"], "Cookie": signon_data["set-cookie"]
    }
    url = f"{cdws_config['cdws_server']}/cdwebconsole/svc/processcontrolcriterias?queue=all"
    try:
        response = requests.get(url=url, headers=headers, timeout=(30, 30), verify=False)

        if (response.status_code != 200):
            print('[ERROR] tcq_metrics: Failed = ', response.json())
            return False

    except ConnectTimeout:
        print('[ERROR] tcq_metrics: Connection timeout')
        return False
    except ReadTimeout:
        print('[ERROR] tcq_metrics: Read timeout')
        return False
    except Exception as e:
        print(f'[ERROR] tcq_metrics: Exception - {e}')
        return False
    
    if response.ok:
        return response.json()
    return False


def collect_metrics(cdws_config, signon_data):
    """Collects IBM Connect:Direct metrics and updates OpenTelemetry metrics"""
    global current_values
    
    try:
        selpro_output = tcq_metrics(cdws_config, signon_data)
        if selpro_output is False:
            raise Exception("Failed to retrieve TCQ metrics")

        if DEBUG:
            print(f"[DEBUG] selpro_output: \n[{selpro_output}]\n")

        count_hold = 0
        count_exec = 0
        count_wait = 0
        count_timer = 0

        # Flatten the nested list structure
        for item in selpro_output:
            if isinstance(item, dict):
                queue_value = item.get('queue', '')

                if queue_value == 'HOLD':
                    count_hold += 1
                elif queue_value == 'EXEC':
                    count_exec += 1
                elif queue_value == 'WAIT':
                    count_wait += 1
                elif queue_value == 'TIMER':
                    count_timer += 1

        # Update UpDownCounters with delta values
        ibm_cd_hold_total.add(count_hold - current_values['hold'])
        current_values['hold'] = count_hold
        print(f"[INFO] Processes in HOLD: {count_hold}")

        ibm_cd_wait_total.add(count_wait - current_values['wait'])
        current_values['wait'] = count_wait
        print(f"[INFO] Processes in WAIT: {count_wait}")

        ibm_cd_timer_total.add(count_timer - current_values['timer'])
        current_values['timer'] = count_timer
        print(f"[INFO] Processes in TIMER: {count_timer}")

        ibm_cd_exec_total.add(count_exec - current_values['exec'])
        current_values['exec'] = count_exec
        print(f"[INFO] Processes in EXEC: {count_exec}")
        
        return True
            
    except Exception as e:
        print(f"[ERROR] Failed to collect metrics: {e}")
        ibm_cd_scrape_errors.add(1)
        return False


def main():
    global DEBUG  # Declares DEBUG as global to modify it inside the function

    """Starts the Prometheus exporter"""
    parser = argparse.ArgumentParser(description="IBM Connect:Direct Prometheus Exporter")
    parser.add_argument('--cdws_server', required=True, help='IBM Connect:Direct Web Services server URL. Sample: https://localhost:9443')

    parser.add_argument('--cd_ipaddress', required=True, help='IBM Connect:Direct Web Services node')
    parser.add_argument('--cd_user', required=True, help='IBM Connect:Direct Web Services username')
    parser.add_argument('--cd_pw', required=True, help='IBM Connect:Direct Web Services password')

    parser.add_argument('--cd_port', default="1363", help='IBM Connect:Direct Web Services node')
    parser.add_argument('--cd_protocol', default="TLS1.3", help='C:D Web Services node')
    parser.add_argument('--port', type=int, default=LOCALPORT, help='Port to listen on')
    parser.add_argument('--interval', type=int, default=INTERVAL, help='Scrape interval in seconds')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    

    args = parser.parse_args()

    port = args.port
    interval = args.interval
    cdws_config = {
        "cdws_server": args.cdws_server,
        "cd_username": args.cd_user,
        "cd_password": args.cd_pw,
        "cd_ipaddress": args.cd_ipaddress,
        "cd_port": args.cd_port,
        "cd_protocol": args.cd_protocol
    }
    DEBUG = args.debug

    print(f"[INFO] Starting IBM Connect:Direct Prometheus Exporter on port {port}")
    print(f"[INFO] Collection interval: {interval} seconds")
    print(f"[INFO] CDWS server: {cdws_config['cdws_server']}")
    print(f"[INFO] C:D IP address: {cdws_config['cd_ipaddress']}")
    print(f"[INFO] C:D username: {cdws_config['cd_username']}")
    print(f"[INFO] C:D port: {cdws_config['cd_port']}")
    print(f"[INFO] C:D protocol: {cdws_config['cd_protocol']}")

    signon_data = signon(cdws_config)
    if signon_data is None:
        raise Exception("Initial signon failed")
    
    # Starts the Prometheus HTTP server
    print(f"[INFO] Starting Prometheus HTTP server on port {port}")
    start_http_server(port)

    # Infinite loop to collect metrics
    while True:
        print(f"\n[INFO] Collecting metrics at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Try to collect metrics
        success = collect_metrics(cdws_config, signon_data)
        
        # If collection failed, try to re-login
        if not success:
            print("[WARN] Metric collection failed, attempting to re-login...")
            
            # Try to login again
            signon_data = signon(cdws_config)
            if signon_data is None:
                print("[ERROR] Re-login failed, will retry in next interval")
            else:
                print("[INFO] Re-login successful")
        
        time.sleep(interval)
    
    signout(cdws_config, signon_data)

if __name__ == '__main__':
    main()