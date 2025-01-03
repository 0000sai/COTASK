pipeline {
	agent any
	stages {
		stage('Lint HTML') {
			steps {
				sh 'tidy -q -e *.html'
			}
		}
		stage('Build Docker Image') {
			steps {
				withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'DockerID', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD']]){
					sh '''
						docker build -t vrmohanbabu/blue_green_kubernetes .
					'''
				}
			}
		}
		stage('Upload Image To Dockerhub') {
			steps {
				withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'DockerID', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD']]){
					sh '''
						docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
						docker push vrmohanbabu/blue_green_kubernetes
					'''
				}
			}
		}
		stage('Set kubectl use-context') {
			steps {
				withAWS(region:'us-west-2', credentials:'aws-cli') {
					sh '''
						kubectl config use-context arn:aws:eks:us-west-2:528472731478:cluster/kubernetescluster
					'''
				}
			}
		}
		stage('Blue replication controller') {
			steps {
				withAWS(region:'us-west-2', credentials:'aws-cli') {
					sh '''
						kubectl apply -f ./blue-replication-controller.yaml
					'''
				}
			}
		}
		stage('Green replication controller') {
			steps {
				withAWS(region:'us-west-2', credentials:'aws-cli') {
					sh '''
						kubectl apply -f ./green-replication-controller.yaml
					'''
				}
			}
		}
		stage('Create the service in kubernetes cluster traffic to blue controller') {
			steps {
				withAWS(region:'us-west-2', credentials:'aws-cli') {
					sh '''
						kubectl apply -f ./blue-service.yaml
					'''
				}
			}
		}
		stage('User approve to continue') {
            steps {
                input "Ready to change redirect traffic to green?"
            }
        }
		stage('Create the service in kubernetes cluster traffic to green controller') {
			steps {
				withAWS(region:'us-west-2', credentials:'aws-cli') {
					sh '''
						kubectl apply -f ./green-service.yaml
					'''
				}
			}
		}

	}
}