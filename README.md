# IBM Connect:Direct OpenTelemetry and Prometheus Exporters

This repository contains **OpenTelemetry and Prometheus exporters** for monitoring **IBM Connect:Direct** processes. Exporters are implemented in **Java** and **Python** (using CLI and HTTP), providing metrics for OpenTelemetry/Prometheus and visualization in Grafana.

> Goal: Collect and expose metrics such as process runs, exit codes, execution duration, errors, and health indicators from IBM Connect:Direct.

---

## Repository Structure
```
connect-direct-observability-exporters/
│
├── README.md
├── LICENSE
├── .gitignore
│
├── otel-exporters/                  # OpenTelemetry exporters
│   ├── cd-cli-metrics-exporter/     # Uses Connect:Direct CLI commands
│   ├── cd-restapi-metrics-exporter/ # Uses Connect:Direct WebServices HTTP requests
│   ├── cd-java-metrics-exporter/    # Uses Connect:Direct Java APIs
│
├── prometheus-exporters/.        # Prometheus exporters
│   ├── cd-cli-exporter/          # Uses Connect:Direct CLI commands
│   ├── cd-restapi-exporter/      # Uses Connect:Direct WebServices HTTP requests
│   ├── cd-java-exporter/         # Uses Connect:Direct Java APIs
│
├── docs/
│   ├── cd-cli-exporter.md
│   ├── cd-restapi-exporter.md
│   ├── cd-java-exporter.md
│   └── prometheus-setup.md
│
├── examples/
│   ├── prometheus.yml
│   ├── docker-compose.yml
│   └── grafana-dashboard.json
```
---


## Planned Exporters

### Python (CLI)
- Executes Connect:Direct commands via CLI and exposes metrics via HTTP (Prometheus client) or Pushgateway.
- Useful when Java API is not available or CLI automation is preferred.

### Python (HTTP Requests)
- Collects metrics via Connect:Direct WebServices HTTP/REST endpoints.
- Flexible alternative when CLI or SDK is not accessible.

### Java (CD protocol)
- Collects metrics via Connect:Direct Java API and exposes metrics via HTTP (Prometheus client).
- Useful when CLI automation or Connect:Direct WebServices is not available.


## 🚀 How to Run (Overview)

**Prerequisites**:
- Prometheus (for metric collection)
- Grafana (optional, for dashboards)
- Docker (optional, for easier deployment)
- Access to Connect:Direct (network, credentials, and permissions)
- Connect:Direct Java API JAR (`CDJAI.jar`) if using Java exporters


### Python CLI Exporter
```bash
# Inside exporters/cd-cli-exporter
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt

python3.11 ibmcd_cli_exporter.py --base-path "/home/cdnode02" --port 9400 
# Metrics available at: http://localhost:9400/metrics
```

### Java Exporter
```bash
# Build (Maven) inside exporters/cd-java-exporter
mvn -q -DskipTests package

# Run (ensure CDJAI.jar is in classpath)
java -jar target/cd-exporter.jar --ipaddress=192.168.1.3 --user=admin --password=password123 --port=1363 --protocol=TCPIP
# Metrics available at: http://localhost:9402/metrics
```

---

## 📅 Roadmap
- [x] Python CLI Prometheus exporter.
- [x] Python REST API Prometheus exporter.
- [x] Java Prometheus exporter.
- [ ] Python CLI OpenTelemetry exporter.
- [ ] Python REST API OpenTelemetry exporter.
- [ ] Java OpenTelemetry exporter.
- [ ] Grafana dashboard in `examples/grafana-dashboard.json`.
- [ ] Troubleshooting guide for network/auth issues.

---

## License
Licensed under **Apache License 2.0** (or your choice). See `LICENSE`.

---

## 📫 Support
Open an issue with:
- Connect:Direct version
- Environment details (OS, network, Java/Python)
- Logs and expected vs actual behavior
