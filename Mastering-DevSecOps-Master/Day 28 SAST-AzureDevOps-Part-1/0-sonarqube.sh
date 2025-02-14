# 1. Set Up PostgreSQL Instance for SonarQube

sudo mkdir -p /var/lib/postgresql/sonarqube
sudo chown postgres:postgres /var/lib/postgresql/sonarqube
sudo su - postgres
/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/sonarqube

# 2. Configure PostgreSQL
Edit postgresql.conf:

sudo nano /var/lib/postgresql/sonarqube/postgresql.conf

Add:

listen_addresses = 'localhost'
port = 5433
unix_socket_directories = '/var/run/postgresql'

Edit pg_hba.conf:
sudo nano /var/lib/postgresql/sonarqube/pg_hba.conf

Add:

local all postgres trust
local all all md5
host all all 127.0.0.1/32 md5
host all all ::1/128 md5

# 3. Create and Start PostgreSQL Service

sudo nano /etc/systemd/system/postgresql-sonarqube.service

Add service content:

[Unit]
Description=PostgreSQL for SonarQube
After=network.target

[Service]
Type=forking
User=postgres
Group=postgres
ExecStart=/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/sonarqube -l /var/log/postgresql/postgresql-sonarqube.log start
ExecStop=/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/sonarqube stop
TimeoutSec=300

[Install]
WantedBy=multi-user.target

Start service:

sudo systemctl daemon-reload
sudo systemctl start postgresql-sonarqube
sudo systemctl enable postgresql-sonarqube

# 4. Create Database and User

psql -p 5433 -U postgres

CREATE USER sonar WITH ENCRYPTED PASSWORD 'my_strong_password'
CREATE DATABASE sonarqube OWNER sonar
GRANT ALL PRIVILEGES ON DATABASE sonarqube to sonar
\q

# 5. Install SonarQube

sudo apt-get install zip -y
cd /opt
sudo wget https://binaries.sonarsource.com/Distribution/sonarqube/sonarqube-9.7.1.62043.zip
sudo unzip sonarqube-9.7.1.62043.zip
sudo mv sonarqube-9.7.1.62043 sonarqube
rm -rf sonarqube-9.7.1.62043.zip

# 6. Configure SonarQube User and Permissions

sudo groupadd sonar
sudo useradd -d /opt/sonarqube -g sonar sonar
sudo chown sonar:sonar /opt/sonarqube -R

Edit sonar.properties:

sudo nano /opt/sonarqube/conf/sonar.properties

Add:
properties
sonar.jdbc.username=sonar
sonar.jdbc.password=my_strong_password
sonar.jdbc.url=jdbc:postgresql://localhost:5433/sonarqube

# 7. System Configuration
Create SonarQube service:

sudo nano /etc/systemd/system/sonar.service

Add:

[Unit]
Description=SonarQube service
After=syslog.target network.target

[Service]
Type=forking
ExecStart=/opt/sonarqube/bin/linux-x86-64/sonar.sh start
ExecStop=/opt/sonarqube/bin/linux-x86-64/sonar.sh stop
User=sonar
Group=sonar
Restart=always
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target

Configure system limits:

sudo nano /etc/sysctl.conf

Add:

vm.max_map_count=262144
fs.file-max=65536

Configure user limits:

sudo nano /etc/security/limits.conf

Add:

sonar soft nofile 65536
sonar hard nofile 65536
sonar soft nproc 4096
sonar hard nproc 4096

# 8. Start SonarQube

sudo sysctl -p
sudo systemctl daemon-reload
sudo systemctl start sonar
sudo systemctl enable sonar

# 9. Access SonarQube
- Wait 5 minutes
- Access: http://your-server:9000
- Login: admin/admin



