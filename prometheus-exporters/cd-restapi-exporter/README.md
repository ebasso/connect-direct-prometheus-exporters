### Python C:D WebServices Exporter

Log in with a user that has access to the Connect:Direct application:

```bash
git clone <repository-url>

cd connect-direct-prometheus-exporters

cd prometheus-exporters/cd-restapi-exporter
```

Inside the `prometheus-exporters/cd-restapi-exporter` directory:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt

python3.11 ibmcd_restapi_exporter.py --cdws_server <CDWS URL> --cdws_user <CDWS User> --cdws_pw <password>  --node_ipaddress --node_port --node_protocol
```

where 

| Parameter    | Description                | Default value                  |  Values |
|--------------|----------------------------|--------------------------------|---------|
| cdws_server  | C:D WebServices server URL | Sample: https://localhost:9443 | 
| cd_ipaddress | C:D Ip Address             | | |
| cd_user      | C:D username               | | |
| cd_pw        | C:D password               | | |
| cd_port      | C:D port                   | 1363 | |
| cd_protocol  | C:D protocol               | TLS1.3            | TCPIP, TLS1.2, TLS1.3 |


Metrics are available at: http://localhost:9402/

### Testing

To test the exporter, submit processes to another CDNODE that is currently stopped. These processes will be listed with a TIMER/WAIT status.

Open a new terminal and log in to Connect:Direct:

```bash
export CDHOME=/home/cdadmin02

export NDMAPICFG=$CDHOME/cdunix/ndm/cfg/cliapi/ndmapi.cfg

cd $CDHOME/cdunix/ndm/bin

./direct
```

Submit the processes:

```bash
submit file=/home/cdadmin02/scripts/copy-cd2-cd3.cdp;

submit file=/home/cdadmin02/scripts/copy-cd2-cd4.cdp;

quit;
```
