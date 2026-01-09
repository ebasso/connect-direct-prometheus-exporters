# IBM Connect:Direct Prometheus Exporters

This repository contains **Prometheus exporters** for monitoring **IBM Connect:Direct** processes. Exporters are implemented in **Java** and **Python** (using CLI and HTTP), providing metrics for Prometheus and visualization in Grafana.

> Goal: Collect and expose metrics such as process runs, exit codes, execution duration, errors, and health indicators from IBM Connect:Direct.

---

## Repository Structure

connect-direct-prometheus-exporters/
│
├── README.md
├── LICENSE
├── .gitignore
│
├── exporters/
│   ├── cd-java-exporter/
│   ├── cd-java-pushgateway/     # Pushgateway exporter for short-lived jobs
│   ├── cd-cli-exporter/         # Uses Connect:Direct CLI commands
│   ├── cd-http-exporter/        # Uses HTTP requests (if applicable)
│
├── docs/
│   ├── architecture.md
│   ├── cd-restapi-exporter.md
│   ├── cli-exporter.md
│   ├── java-exporter.md
│   └── prometheus-setup.md
│
├── examples/
│   ├── prometheus.yml
│   ├── docker-compose.yml
│   └── grafana-dashboard.json

---

## Planned Exporters

### Python (CLI)
- Executes Connect:Direct commands via CLI and exposes metrics via HTTP (Flask + Prometheus client) or Pushgateway.
- Useful when Java API is not available or CLI automation is preferred.

### Python (HTTP Requests)
- Collects metrics via HTTP/REST endpoints (if available).
- Flexible alternative when CLI or SDK is not accessible.

### Java (CD protocol)
- Long-running service exposing `/metrics` using **Prometheus Java client**.
- Metrics:
  - `cdprocess_runs_total{status="success|failure"}`
  - `cdprocess_up`
  - `cdprocess_last_exit_code`
  - `cdprocess_duration_seconds` (histogram)
  - `cdprocess_errors_total{exception="<type>"}`
  - `cdprocess_last_process_number`
  - `cdprocess_last_run_timestamp_seconds`
- Configuration via **environment variables** (no secrets in code).

### Java (Pushgateway)
- For short-lived jobs: pushes metrics to **Prometheus Pushgateway** after execution.
- Ideal for scheduled tasks without an active HTTP endpoint.


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
# Build (Maven) inside exporters/java/cd-java-exporter
mvn -q -DskipTests package

# Run (ensure CDJAI.jar is in classpath)
java -cp "target/cd-java-exporter-1.0.0.jar:./lib/CDJAI.jar" CDExporter
# Metrics available at: http://localhost:9402/metrics
```

---

## 📅 Roadmap
- [x] Python CLI exporter.
- [ ] Python REST API exporter.
- [ ] Java exporter.
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
