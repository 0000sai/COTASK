## Project Overview

In this project, we will develop a CI/CD pipeline for micro services applications with blue/green deployment on kubernetes cluster.

---

## Setup the Enviroment

* Environment used is Ubuntu18 in cloud9.
* Jenkins with Blue Ocean Plugin & Pipeline-AWS Plugin.
* Docker
* AWS Cli
* Eksctl
* Kubectl

### Install Jenkins:

* `wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -`
* `sudo sh -c 'echo deb https://pkg.jenkins.io/debian-stable binary/ >> /etc/apt/sources.list'`
* `sudo apt-get update`
* `wget https://pkg.jenkins.io/debian-stable/binary/jenkins_2.204.6_all.deb`
* `sudo apt install ./jenkins_2.204.6_all.deb -y`
* `sudo systemctl start jenkins`
* `sudo systemctl enable jenkins`
* `sudo systemctl status jenkins`

### Install Eksctl:

* `curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp`
* `sudo mv /tmp/eksctl /usr/local/bin`
* `eksctl version`

### Install kubectl: [Refer](https://kubernetes.io/docs/tasks/tools/install-kubectl/#kubectl-install-0) for other operating system
#### Install via native package management:
* `sudo apt-get update && sudo apt-get install -y apt-transport-https gnupg2`
* `curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -`
* `echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee -a /etc/apt/sources.list.d/kubernetes.list`
* `sudo apt-get update`
* `sudo apt-get install -y kubectl`
#### Install via other package management:
* `snap install kubectl --classic`
* `kubectl version --client`

### About files:
* `create_kubernetes_cluster.sh` : To create kubernetes cluster and update-kubeconfig.
* `Jenkinsfile` : Jenkins pipeline steps.
* `Dockerfile`  : Docker file to create nginx image.
* `blue-replication-controller.yaml` : Create a replication controller for blue pod.
* `blue-service.yaml` : Create a blue service for blue controller.
* `green-replication-controller.yaml` : Create a replication controller for green pod.
* `green-service.yaml` : Create a blue service for green controller.

### To deploy:
1. Run: `create_kubernetes_cluster.sh`
2. Run Jenkins Pipeline.

https://github.com/vrmohanbabu/blue-green-deploy-on-kubernetes-cluster/tree/master




