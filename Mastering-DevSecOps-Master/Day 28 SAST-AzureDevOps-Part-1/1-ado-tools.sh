sudo apt update && apt install -y unzip jq net-tools
apt install openjdk-17-jdk -y
apt install maven -y && curl https://get.docker.com | bash
usermod -a -G docker adminsai

# aws cli install
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# azurecli ubuntu install
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# terraform.io and packer.io copy the link and install in /usr/local/bin

cd /usr/local/bin
wget https://releases.hashicorp.com/terraform/1.10.3/terraform_1.10.3_linux_amd64.zip
unzip

# packer.io
wget https://releases.hashicorp.com/packer/1.11.2/packer_1.11.2_linux_amd64.zip
unzip

# document.ansible.com  Select ubuntu and download the file accordingly
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install ansible

cd /etc/ansible
cp ansible.cfg ansible.cfg_backup
ansible-config init --disabled >ansible.cfg
nano ansible.cfg

ctrl w  host_key_checking = False

# Install trivy https://github.com/aquasecurity/trivy/releases/download/v0.41.0/trivy_0.41.0_Linux-64bit.deb

cd /usr/local/bin
Wget https://github.com/aquasecurity/trivy/releases/download/v0.41.0/trivy_0.41.0_Linux-64bit.deb
dpkg -i trivy file
Trivy

reboot the system for configurations.


