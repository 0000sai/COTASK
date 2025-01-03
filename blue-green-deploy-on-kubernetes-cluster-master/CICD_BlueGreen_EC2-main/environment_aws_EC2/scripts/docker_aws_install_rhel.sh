#!/bin/bash
# sleep until instance is ready
until [[ -f /var/lib/cloud/instance/boot-finished ]]; do
  sleep 1
done

#update system and install docker
sudo yum install -y yum-utils
sudo yum-config-manager \
    --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io -y
sudo systemctl start docker.service
sudo systemctl enable docker.service
sudo groupadd docker
sudo usermod -aG docker ec2-user
sudo systemctl restart docker

# install trivy
rpm -ivh https://github.com/aquasecurity/trivy/releases/download/v0.40.0/trivy_0.40.0_Linux-64bit.rpm

#install unzip
sudo yum install unzip -y

#install awssli
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

