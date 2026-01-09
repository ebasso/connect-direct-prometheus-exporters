#!/usr/bin/env python3

import os
import subprocess
import time
import argparse
from prometheus_client import start_http_server, Gauge, Counter
from prometheus_client.core import CollectorRegistry

DEBUG=True

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
    """Collects IBM Connect:Direct metrics and updates Prometheus metrics"""
    try:
        selpro_output = run_cmd(base_path)

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
    parser.add_argument('--base-path', required=True, help='Base path for IBM Connect:Direct installation')
    parser.add_argument('--port', type=int, default=9400, help='Port to listen on')
    parser.add_argument('--interval', type=int, default=60, help='Scrape interval in seconds')
    args = parser.parse_args()

    port = args.port
    interval = args.interval
    base_path = args.base_path

    print(f"[INFO] Starting IBM Connect:Direct Prometheus Exporter on port {port}")
    print(f"[INFO] Collection interval: {interval} seconds")
    print(f"[INFO] Base path: {base_path}")
    
    if not base_path:
        print("[ERROR] Base path is required")
        exit(1)
    
    # Starts the Prometheus HTTP server
    start_http_server(port, registry=registry)
    
    # Infinite loop to collect metrics
    while True:
        print(f"\n[INFO] Collecting metrics at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        collect_metrics(base_path)
        time.sleep(interval)

if __name__ == '__main__':
    main()