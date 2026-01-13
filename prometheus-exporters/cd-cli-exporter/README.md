### Python CLI Exporter

Log in with a user that has access to the Connect:Direct application:

```bash
su - cdnode02

git clone <repository-url>

cd connect-direct-prometheus-exporters

cd exporters/cd-cli-exporter
```

Inside the `exporters/cd-cli-exporter` directory:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt

python3.11 ibmcd_cli_exporter.py --base-path "/home/cdnode02" --port 9400 
```

Metrics are available at: http://localhost:9400/metrics

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
