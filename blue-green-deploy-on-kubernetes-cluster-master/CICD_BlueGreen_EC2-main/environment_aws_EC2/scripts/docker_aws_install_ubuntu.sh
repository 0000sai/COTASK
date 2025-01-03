#!/bin/bash
# sleep until instance is ready
until [[ -f /var/lib/cloud/instance/boot-finished ]]; do
  sleep 1
done

# update system and install docker
sudo apt update -y
sudo apt install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart docker

# install Trivy and all dependencies
sudo apt update -y
wget https://github.com/aquasecurity/trivy/releases/download/v0.40.0/trivy_0.40.0_Linux-64bit.deb
sudo dpkg -i trivy_0.40.0_Linux-64bit.deb

# install unzip
sudo apt install unzip -y

# install awssli
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

