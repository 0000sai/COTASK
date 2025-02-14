1
sudo certbot certonly --manual --preferred-challenges=dns --key-type rsa \
    --email pinapathruni.saikiran@gmail.com --server https://acme-v02.api.letsencrypt.org/directory \
    --agree-tos -d *.cloudvishwakarma.in

# Certificate is saved at: /etc/letsencrypt/live/cloudvishwakarma.in/fullchain.pem
# Key is saved at:         /etc/letsencrypt/live/cloudvishwakarma.in/privkey.pem

+++++IF ISSUE+++++

free -m
top
#DRY-RUN
certbot certonly --dry-run --manual --preferred-challenges=dns --key-type rsa \
    --email pinapathruni.saikiran@gmail.com --server https://acme-v02.api.letsencrypt.org/directory \
    --agree-tos -d *.cloudvishwakarma.in

+++++IF ISSUE+++++

2
apt update && apt install -y unzip net-tools

3
wget https://releases.hashicorp.com/vault/1.13.2/vault_1.13.2_linux_amd64.zip
unzip vault_1.13.2_linux_amd64.zip
cp vault /usr/bin/vault
mkdir -p /etc/vault
mkdir -p /var/lib/vault/data
vault version

4
nano config.hcl
cp config.hcl /etc/vault/config.hcl

5
nano /etc/systemd/system/vault.service

6
sudo systemctl daemon-reload
sudo systemctl stop vault
sudo systemctl start vault
sudo systemctl enable vault
sudo systemctl status vault --no-pager

7 #VAULT STATUS FROM CLI
ps -ef | grep -i vault | grep -v grep

8
export VAULT_ADDR=https://kmsvault.cloudvishwakarma.in:8200
echo "export VAULT_ADDR=https://kmsvault.cloudvishwakarma.in:8200" >>~/.bashrc

vault status

9
vault operator init | tee -a /etc/vault/init.file

10
vault operator init | tee -a /etc/vault/init.file
