# IBM Connect:Direct Prometheus Exporter

Prometheus exporter for IBM Connect:Direct that collects and exposes metrics about process states.

## Prerequisites

- Java 17 or higher
- Maven 3.6 or higher
- IBM Connect:Direct Java API
- Access to IBM Connect:Direct node

## Metrics Exposed

| Metric Name | Type | Description |
|-------------|------|-------------|
| `ibm_cd_processes_hold_total` | Gauge | Total processes in HOLD state |
| `ibm_cd_processes_wait_total` | Gauge | Total processes in WAIT state |
| `ibm_cd_processes_timer_total` | Gauge | Total processes in TIMER state |
| `ibm_cd_processes_exec_total` | Gauge | Total processes in EXEC state |
| `ibm_cd_process_count{process_name="..."}` | Gauge | Count of specific processes in HOLD or WAIT |
| `ibm_cd_scrape_errors_total` | Counter | Total errors when collecting metrics |

## Build Instructions

### 1. Compile the project

```bash
cd exporters/cd-java-exporter

mvn clean compile
```

To import the library `lib/CDJAI.jar` in your Maven project, you can use the following command:

```bash
mvn install:install-file -Dfile=lib/CDJAI.jar -DgroupId=com.ibm -DartifactId=cdjai -Dversion=1.0 -Dpackaging=jar
```

### 2. Package as executable JAR

```bash
# Option 1: Create fat JAR with all dependencies (recommended)
mvn clean compile package
```

This creates: target/cd-exporter.jar

## Running the Exporter

### Required Parameters

The exporter requires 4 mandatory parameters:

```bash
java -jar target/cd-exporter.jar -cp lib/CDjai.jar --ipaddress=<IP ADDRESS> --port=<1363> --user=<NODEUSER> --password=<NODEPASSWORD>
```

### Optional Parameters

```bash
java -jar target/cd-exporter.jar --ipaddress=<IP ADDRESS> --port=<1363> --user=<NODEUSER> --password=<NODEPASSWORD> --protocol=TLS1.2 --http-port=[HTTP_PORT] --scrape-interval=[SCRAPE_INTERVAL]
```

| Parameter | Description                 | Default |
|-----------|-----------------------------|---------|
| ipaddress | Connect:Direct hostname/IP  | Required |
| port      | Node API port               | Required |
| user      | Username for authentication | Required |
| password  | Password for authentication | Required |
| http-port | HTTP port for Prometheus metrics | 9402 |
| scrape-interval | Interval in seconds between metric collections | 60 |

### Examples

#### Basic usage (default port 9402, interval 60s)
```bash
java -jar target/cd-exporter.jar --ipaddress=192.168.1.3 --user=admin --password=password123 --port=1363 --protocol=TCPIP
```

#### Custom HTTP port and scrape interval
```bash
java -jar target/cd-exporter.jar --ipaddress=192.168.1.3 --user=admin --password=password123 --port=1363 --protocol=TCPIP --http-port=9402 --scrape-interval=30
```

#### Connecting to a C:D node with TLS enabled

Creating a trustore and import Connect:Direct certificate

```bash
keytool -importcert -alias cdnode02-cdinternal -file cdinternal.cer -keystore ./truststore.jks -storetype JKS -storepass changeit --noprompt
```

Running

```bash
java -Djavax.net.ssl.trustStore=./truststore.jks -Djavax.net.ssl.trustStorePassword=changeit -jar target/cd-exporter.jar --ipaddress=192.168.1.3 --user=admin --password=password123 --port=1363 --protocol=TLS12
```


## Accessing Metrics

Once the exporter is running, metrics are available at:

```
http://localhost:9402/metrics
```

Example output:
```
# HELP ibm_cd_processes_hold_total Total processes in HOLD state
# TYPE ibm_cd_processes_hold_total gauge
ibm_cd_processes_hold_total 15.0

# HELP ibm_cd_processes_wait_total Total processes in WAIT state
# TYPE ibm_cd_processes_wait_total gauge
ibm_cd_processes_wait_total 8.0

# HELP ibm_cd_processes_timer_total Total processes in TIMER state
# TYPE ibm_cd_processes_timer_total gauge
ibm_cd_processes_timer_total 3.0

# HELP ibm_cd_processes_exec_total Total processes in EXEC state
# TYPE ibm_cd_processes_exec_total gauge
ibm_cd_processes_exec_total 2.0

# HELP ibm_cd_scrape_errors_total Total errors when collecting IBM Connect:Direct metrics
# TYPE ibm_cd_scrape_errors_total counter
ibm_cd_scrape_errors_total 0.0
```

## Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'ibm-connect-direct'
    static_configs:
      - targets: ['localhost:9402']
        labels:
          node: 'cd-node01'
          environment: 'production'
```

## Running as a Service

### Systemd Service (Linux)

Create `/etc/systemd/system/cd-exporter.service`:

```ini
[Unit]
Description=IBM Connect:Direct Prometheus Exporter
After=network.target

[Service]
Type=simple
User=cduser
ExecStart=/usr/bin/java -jar target/cd-exporter.jar --ipaddress=192.168.1.3 --user=admin --password=password123 --port=1363 --protocol=TCPIP
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cd-exporter
sudo systemctl start cd-exporter
sudo systemctl status cd-exporter
```

### Docker

Build and run:
```bash
docker build -t cd-exporter .
docker run -d -p 9402:9402 -v /host/path/to/truststore.jks:/app/truststore.jks -e CD_NODE_IP=192.168.1.2  -e CD_USER=admin -e CD_PASSWORD=<USER PASSWORD>
```

## Troubleshooting

### Check if exporter is running
```bash
curl http://localhost:9402/metrics
```

### Common Issues

1. **Authentication failed**
   - Verify NODE, NODEAPIPORT, NODEUSER, and NODEPASSWORD are correct
   - Check Connect:Direct node is accessible

2. **Port already in use**
   - Change HTTP_PORT parameter to a different port
   - Check if another process is using port 9402

## Development

### Project Structure
```
cd-exporter/
├── pom.xml
├── README.md
└── src/
    └── main/
        └── java/
            └── CDExporter.java
```

## License

This project is provided as-is for monitoring IBM Connect:Direct instances.

## Support

For issues or questions, please refer to your organization's support channels.