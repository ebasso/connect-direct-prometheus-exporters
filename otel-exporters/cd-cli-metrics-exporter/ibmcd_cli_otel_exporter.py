#!/usr/bin/env python3

import os
import subprocess
import time
import argparse
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import start_http_server

DEBUG = True

# Configure OpenTelemetry with Prometheus exporter
prometheus_reader = PrometheusMetricReader()
provider = MeterProvider(metric_readers=[prometheus_reader])
metrics.set_meter_provider(provider)

# Create a meter
meter = metrics.get_meter(__name__)

# Define metrics using OpenTelemetry
ibm_cd_hold_total = meter.create_observable_gauge(
    name='ibm_cd_processes_hold_total',
    description='Total processes in HOLD state',
    unit='1'
)

ibm_cd_wait_total = meter.create_observable_gauge(
    name='ibm_cd_processes_wait_total',
    description='Total processes in WAIT state',
    unit='1'
)

ibm_cd_timer_total = meter.create_observable_gauge(
    name='ibm_cd_processes_timer_total',
    description='Total processes in TIMER state',
    unit='1'
)

ibm_cd_exec_total = meter.create_observable_gauge(
    name='ibm_cd_processes_exec_total',
    description='Total processes in EXEC state',
    unit='1'
)

ibm_cd_scrape_errors = meter.create_counter(
    name='ibm_cd_scrape_errors_total',
    description='Total errors when collecting IBM Connect:Direct metrics',
    unit='1'
)

# Global variables to store metric values
metric_values = {
    'hold': 0,
    'wait': 0,
    'timer': 0,
    'exec': 0
}

def run_cmd(base_path):
    """Executes the selpro command and returns the output"""
    # Defines the environment variable
    os.environ['NDMAPICFG'] = f'{base_path}/cdunix/ndm/cfg/cliapi/ndmapi.cfg'
    
    # Ensure library paths are set (helps with missing libtirpc.so.1 and other shared libraries)
    lib_path = f'{base_path}/cdunix/ndm/lib'
    if os.path.isdir(lib_path):
        current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
        os.environ['LD_LIBRARY_PATH'] = f"{lib_path}:{current_ld_path}" if current_ld_path else lib_path

    try:
        process = subprocess.Popen(
            [f'{base_path}/cdunix/ndm/bin/direct', '-s'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        selpro_output, stderr = process.communicate(input='selpro;\n')
        
        if process.returncode == 127:
            raise Exception(f"Command not found or cannot execute binary (exit code 127). Check if libtirpc.so.1 is installed: {stderr}")
        elif process.returncode != 0:
            raise Exception(f"Command returned code {process.returncode}: {stderr}")
            
        return selpro_output
        
    except FileNotFoundError:
        raise Exception(f"Binary not found at {base_path}/cdunix/ndm/bin/direct")
    except OSError as e:
        raise Exception(f"OS Error executing command (missing library?): {e}")
    except subprocess.TimeoutExpired:
        process.kill()
        raise Exception("Timeout executing command")
    except Exception as e:
        raise Exception(f"Error executing command: {e}")

def collect_metrics(base_path):
    """Collects IBM Connect:Direct metrics and updates OpenTelemetry metrics"""
    global metric_values
    
    try:
        selpro_output = run_cmd(base_path)

        if DEBUG:
            print(f"[DEBUG] selpro_output: \n[{selpro_output}]\n")
        
        # Counts HOLD occurrences
        count_hold = selpro_output.count('HOLD')
        metric_values['hold'] = count_hold
        print(f"[INFO] Processes in HOLD: {count_hold}")

        # Counts WAIT occurrences
        count_wait = selpro_output.count('WAIT')
        metric_values['wait'] = count_wait
        print(f"[INFO] Processes in WAIT: {count_wait}")

        # Counts TIMER occurrences
        count_timer = selpro_output.count('TIMER')
        metric_values['timer'] = count_timer
        print(f"[INFO] Processes in TIMER: {count_timer}")

        # Counts EXEC occurrences
        count_exec = selpro_output.count('EXEC')
        metric_values['exec'] = count_exec
        print(f"[INFO] Processes in EXEC: {count_exec}")
            
    except Exception as e:
        print(f"[ERROR] Failed to collect metrics: {e}")
        ibm_cd_scrape_errors.add(1)

# Observable gauge callbacks
def hold_callback(options):
    yield metrics.Observation(metric_values['hold'])

def wait_callback(options):
    yield metrics.Observation(metric_values['wait'])

def timer_callback(options):
    yield metrics.Observation(metric_values['timer'])

def exec_callback(options):
    yield metrics.Observation(metric_values['exec'])

# Register callbacks for observable gauges
ibm_cd_hold_total = meter.create_observable_gauge(
    name='ibm_cd_processes_hold_total',
    callbacks=[hold_callback],
    description='Total processes in HOLD state',
    unit='1'
)

ibm_cd_wait_total = meter.create_observable_gauge(
    name='ibm_cd_processes_wait_total',
    callbacks=[wait_callback],
    description='Total processes in WAIT state',
    unit='1'
)

ibm_cd_timer_total = meter.create_observable_gauge(
    name='ibm_cd_processes_timer_total',
    callbacks=[timer_callback],
    description='Total processes in TIMER state',
    unit='1'
)

ibm_cd_exec_total = meter.create_observable_gauge(
    name='ibm_cd_processes_exec_total',
    callbacks=[exec_callback],
    description='Total processes in EXEC state',
    unit='1'
)

def main():
    """Starts the OpenTelemetry exporter"""
    parser = argparse.ArgumentParser(description="IBM Connect:Direct OpenTelemetry Exporter")
    parser.add_argument('--base-path', required=True, help='Base path for IBM Connect:Direct installation')
    parser.add_argument('--port', type=int, default=9400, help='Port to listen on')
    parser.add_argument('--interval', type=int, default=60, help='Scrape interval in seconds')
    args = parser.parse_args()

    port = args.port
    interval = args.interval
    base_path = args.base_path

    print(f"[INFO] Starting IBM Connect:Direct OpenTelemetry Exporter on port {port}")
    print(f"[INFO] Collection interval: {interval} seconds")
    print(f"[INFO] Base path: {base_path}")
    
    if not base_path:
        print("[ERROR] Base path is required")
        exit(1)
    
    # Start the Prometheus HTTP server for metrics exposition
    start_http_server(port)
    
    # Infinite loop to collect metrics
    while True:
        print(f"\n[INFO] Collecting metrics at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        collect_metrics(base_path)
        time.sleep(interval)

if __name__ == '__main__':
    main()
