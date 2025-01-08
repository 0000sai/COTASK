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
-------------------------------------------------------- Jenkins ECS and EKS dev pod qa EXp-----------------------------------------------
pipeline {
    agent any
    
    environment {
        AWS_ACCOUNT_ID = credentials('AWS_ACCOUNT_ID')
        AWS_REGION = 'us-west-2'
        ECR_REPO = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/my-app"
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        VERSION = "v${BUILD_NUMBER}"
    }
    
    stages {
        stage('Code Analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarQubeScanner'
                    withSonarQubeEnv('SonarQube') {
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=my-app \
                            -Dsonar.sources=. \
                            -Dsonar.host.url=http://sonarqube:9000 \
                            -Dsonar.login=${SONAR_TOKEN}
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build & Push') {
            steps {
                script {
                    sh "docker build -t ${ECR_REPO}:${VERSION} ."
                    sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    sh "docker push ${ECR_REPO}:${VERSION}"
                }
            }
        }

        stage('Deploy to Dev') {
            when { branch 'develop' }
            steps {
                script {
                    sh """
                        aws ecs update-service \
                            --cluster dev-cluster \
                            --service my-app-dev \
                            --force-new-deployment \
                            --task-definition my-app-dev:${VERSION}
                    """
                    sh """
                        kubectl --context=dev apply -f k8s/dev/
                        kubectl --context=dev set image deployment/my-app \
                            my-app=${ECR_REPO}:${VERSION}
                    """
                }
            }
        }

        stage('Deploy to QA') {
            when { branch 'qa' }
            environment {
                NAMESPACE = 'qa'
            }
            steps {
                script {
                    sh """
                        aws ecs create-service \
                            --cluster qa-cluster \
                            --service my-app-qa-green \
                            --task-definition my-app-qa:${VERSION}
                    """
                    sh """
                        kubectl --context=qa -n ${NAMESPACE} apply -f k8s/qa/
                        kubectl --context=qa -n ${NAMESPACE} set image deployment/my-app-green \
                            my-app=${ECR_REPO}:${VERSION}
                    """
                    sh """
                        kubectl --context=qa -n ${NAMESPACE} rollout status deployment/my-app-green
                        aws ecs wait services-stable --cluster qa-cluster --services my-app-qa-green
                    """
                    sh """
                        kubectl --context=qa -n ${NAMESPACE} patch service my-app -p \
                            '{"spec":{"selector":{"version":"green"}}}'
                        kubectl --context=qa -n ${NAMESPACE} scale deployment my-app-blue --replicas=0
                        aws ecs update-service --cluster qa-cluster --service my-app-qa-blue --desired-count 0
                    """
                }
            }
        }

        stage('Deploy to Prod') {
            when { branch 'main' }
            environment {
                NAMESPACE = 'prod'
            }
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    input message: 'Approve Production Deployment?'
                }
                script {
                    sh """
                        aws ecs create-service \
                            --cluster prod-cluster \
                            --service my-app-prod-green \
                            --task-definition my-app-prod:${VERSION}
                    """
                    sh """
                        kubectl --context=prod -n ${NAMESPACE} apply -f k8s/prod/
                        kubectl --context=prod -n ${NAMESPACE} set image deployment/my-app-green \
                            my-app=${ECR_REPO}:${VERSION}
                    """
                    sh """
                        kubectl --context=prod -n ${NAMESPACE} rollout status deployment/my-app-green
                        aws ecs wait services-stable --cluster prod-cluster --services my-app-prod-green
                    """
                    sh """
                        kubectl --context=prod -n ${NAMESPACE} patch service my-app -p \
                            '{"spec":{"selector":{"version":"green"}}}'
                        aws ecs update-service --cluster prod-cluster --service my-app-prod-blue --desired-count 0
                    """
                }
            }
        }
    }

    post {
        failure {
            script {
                if (env.BRANCH_NAME in ['qa', 'main']) {
                    sh """
                        kubectl --context=${BRANCH_NAME} -n ${NAMESPACE} patch service my-app -p \
                            '{"spec":{"selector":{"version":"blue"}}}'
                        kubectl --context=${BRANCH_NAME} -n ${NAMESPACE} scale deployment/my-app-blue --replicas=2
                        aws ecs update-service \
                            --cluster ${BRANCH_NAME}-cluster \
                            --service my-app-${BRANCH_NAME}-blue \
                            --desired-count 2
                    """
                }
            }
        }
        always {
            cleanWs()
        }
    }
}





