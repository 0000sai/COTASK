sudo apt update && apt install -y unzip jq net-tools
apt install openjdk-17-jdk -y
apt install maven -y && curl https://get.docker.com | bash
useradd -G docker adminsai
usermod -aG docker adminsai

# aws cli install
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# # azurecli ubuntu install
# curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

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

# Create one ansible user.
sudo useradd -m -s /bin/bash ansibleadmin
sudo mkdir -p /home/ansibleadmin/.ssh
sudo chown -R ansibleadmin:ansibleadmin /home/ansibleadmin/.ssh
sudo chmod 700 /home/ansibleadmin/.ssh
sudo touch /home/ansibleadmin/.ssh/authorized_keys
sudo chown ansibleadmin:ansibleadmin /home/ansibleadmin/.ssh/authorized_keys
sudo chmod 600 /home/ansibleadmin/.ssh/authorized_keys
sudo usermod -aG sudo ansibleadmin
echo 'ansibleadmin ALL=(ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers
echo 'ssh-rsa key here' | sudo tee /home/ansibleadmin/.ssh/authorized_keys
usermod -aG root ansibleadmin
usermod -aG docker ansibleadmin

# Install trivy https://github.com/aquasecurity/trivy/releases/download/v0.41.0/trivy_0.41.0_Linux-64bit.deb

cd /usr/local/bin
Wget https://github.com/aquasecurity/trivy/releases/download/v0.41.0/trivy_0.41.0_Linux-64bit.deb
dpkg -i trivy file
Trivy

#################################

# 1 reboot the system for configurations, Once it is up then take AMI image and wait till the image has been created. Then install jenkins.
# 2 Create DNS Record for Jenkins Jfrog and Sonarqube, Turn the sonar jfrog instance.

#################################

#jenkins installation

# Add Jenkins GPG key
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc >/dev/null

# Add Jenkins repository to sources list
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | sudo tee /etc/apt/sources.list.d/jenkins.list >/dev/null

# Update package list
sudo apt-get update

# (Optional) Check available Jenkins versions
sudo apt-cache madison jenkins | grep -i 2.426.2

# Install the specific Jenkins version
sudo apt-get install jenkins=2.426.2 -y

######################################################################################################################

Login and install all neccessary plugins

PLugins

- AWS Steps Plugin
- Docker Plugin
- SonarQube Scanner Version 2.15 and configure it in Jenins Configure System.
- Blue Ocean
- Multibranch Scan Webhook Trigger
- Slack Notification
- Ansible

Once done, reboot the jenkins server

Then update the SSL certificate following below.

#######################################################################################################################

# SSL Certificate
snap install --classic certbot

certbot certonly --manual --preferred-challenges=dns --key-type rsa \
    --email pinapathruni.saikiran@gmail.com --server https://acme-v02.api.letsencrypt.org/directory \
    --agree-tos -d "*.cloudvishwakarma.in"

#get into the  /etc/letsencrypt/live/clodvishwakarma.in/ Then run below, Because it needs to pick the crts.

openssl pkcs12 -inkey privkey.pem -in cert.pem -export -out certificate.p12

# password : India@123

#Now convert into JKS certificate,
keytool -importkeystore -srckeystore certificate.p12 -srcstoretype pkcs12 \
    -destkeystore jenkinsserver.jks -deststoretype JKS
# password : India@123

sudo cp jenkinsserver.jks /var/lib/jenkins/
sudo chown jenkins:jenkins /var/lib/jenkins/jenkinsserver.jks

nano /lib/systemd/system/Jenkins.service

Environment="JENKINS_PORT=8080"
Environment="JENKINS_PORT=8080"
Environment="JENKINS_HTTPS_PORT=8443"
Environment="JENKINS_HTTPS_KEYSTORE=/var/lib/jenkins/jenkinsserver.jks"
Environment="JENKINS_HTTPS_KEYSTORE_PASSWORD=India@123"
AmbientCapabilities=CAP_NET_BIND_SERVICE

echo 'JENKINS_ARGS="$JENKINS_ARGS --httpsPort=8443 --httpPort=-1 --httpsPrivateKey=/etc/letsencrypt/live/cloudvishwakarma.in/privkey.pem --httpsCertificate=/etc/letsencrypt/live/cloudvishwakarma.in/fullchain.pem"' >>/etc/default/jenkins

sudo usermod -aG docker jenkins
sudo usermod -aG root jenkins
sudo systemctl daemon-reload && sudo systemctl restart jenkins && sudo systemctl status jenkins
