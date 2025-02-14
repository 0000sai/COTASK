Create T2-xl
create Simplerecord for Jfrog with publicIP
sudo apt update && apt install -y openjdk-17-jdk && sudo apt update && apt install -y maven

clone same in local from powershell and push to azuredevops repo

clone petclinicapp https://github.com/saikiranpi/springboot-petclinic.git on linux and make sure you ssh keys

mvn clean install deploy

-----
now lets deploy jfrog for storing our artifacts

cd /usr/local/bin
wget -O jfrog-deb-installer.tar.gz "https://releases.jfrog.io/artifactory/jfrog-prox/org/artifactory/pro/deb/jfrog-platform-trial-prox/[RELEASE]/jfrog-platform-trial-prox-[RELEASE]-deb.tar.gz"
tar -xvzf jfrog-deb-installer.tar.gz
sudo apt install jq -y && sudo apt install net-tools -y
cd jfrog-platform-trial-pro*
# sudo chown -R postgres:postgres /var/opt/jfrog/postgres/data
# sudo chmod -R 700 /var/opt/jfrog/postgres/data
sudo ./install.sh
sudo systemctl start artifactory.service
sudo systemctl start xray.service

You need license trail license
copy antifactory license and paste it the key  next  next next
we need maven repo here - >jfrog >http://jfrog.cloudvishwakarma.in
finish


http://localhost:8082/


generate settings in the mainfile under settings.xml and change the jfrog
username and password
snapshot as true
change the Jfrog URL accordingly
paste the settings.yml under /root/.m2/settings/xml
stay in petapp dir and run "mvn clean install deploy"

################################################################################
java -jar target/*.jar

mvn versions:set -DnewVersion=1.0.0
mvn clean install deploy
