# Complete CI/CD Implementation Guide

## Table of Contents
1. [CI/CD Best Practices](#cicd-best-practices)
2. [Architecture Overview](#architecture-overview)
3. [Jenkins Pipeline](#jenkins-pipeline)
4. [GitLab CI/CD](#gitlab-cicd)
5. [GitHub Actions](#github-actions)
6. [Environment Management](#environment-management)
7. [Security Implementation](#security-implementation)
8. [Monitoring & Notifications](#monitoring--notifications)

## CI/CD Best Practices

### Core Principles
- **Fail Fast**: Catch issues early in the pipeline
- **Security First**: Integrate security scanning at every stage
- **Environment Parity**: Keep environments as similar as possible
- **Rollback Strategy**: Always have a rollback plan
- **Observability**: Comprehensive logging and monitoring
- **Secrets Management**: Never hardcode credentials

### Pipeline Stages
1. **Source** → Code commit triggers pipeline
2. **Build** → Compile, package, and create artifacts
3. **Test** → Unit tests, integration tests, security scans
4. **Package** → Container image creation and scanning
5. **Deploy** → Progressive deployment across environments
6. **Monitor** → Health checks and observability

## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   DEV POD   │    │     QA      │    │     UAT     │
│             │    │             │    │             │
│ Feature     │───▶│ Integration │───▶│ User Accept │
│ Testing     │    │ Testing     │    │ Testing     │
└─────────────┘    └─────────────┘    └─────────────┘
                                               │
                                               ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  STAGING    │    │ PRODUCTION  │    │   ROLLBACK  │
│             │    │             │    │             │
│ Final       │───▶│ Live        │◀──▶│ Emergency   │
│ Validation  │    │ Environment │    │ Recovery    │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Jenkins Pipeline

### Jenkinsfile (Declarative Pipeline)

```groovy
pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: docker
    image: docker:20.10-dind
    securityContext:
      privileged: true
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
  - name: kubectl
    image: bitnami/kubectl:latest
    command:
    - sleep
    args:
    - 99d
  - name: helm
    image: alpine/helm:latest
    command:
    - sleep
    args:
    - 99d
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
"""
        }
    }
    
    environment {
        DOCKER_REGISTRY = credentials('docker-registry')
        KUBECONFIG = credentials('kubeconfig')
        SONAR_TOKEN = credentials('sonar-token')
        SLACK_WEBHOOK = credentials('slack-webhook')
        APP_NAME = "${env.JOB_NAME.split('/')[0]}"
        BUILD_VERSION = "${env.BUILD_NUMBER}-${env.GIT_COMMIT.take(8)}"
        NAMESPACE_PREFIX = "app"
    }
    
    parameters {
        choice(
            name: 'DEPLOY_ENV',
            choices: ['dev', 'qa', 'uat', 'staging', 'production'],
            description: 'Target deployment environment'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip test execution'
        )
        booleanParam(
            name: 'FORCE_DEPLOY',
            defaultValue: false,
            description: 'Force deployment even if tests fail'
        )
    }
    
    stages {
        stage('Initialize') {
            steps {
                script {
                    // Environment-specific configurations
                    env.TARGET_NAMESPACE = "${NAMESPACE_PREFIX}-${params.DEPLOY_ENV}"
                    env.REPLICAS = getReplicaCount(params.DEPLOY_ENV)
                    env.RESOURCES = getResourceLimits(params.DEPLOY_ENV)
                }
                
                // Send build start notification
                sendSlackNotification('STARTED')
                
                // Checkout code
                checkout scm
                
                // Print build info
                sh '''
                    echo "=== BUILD INFORMATION ==="
                    echo "Application: ${APP_NAME}"
                    echo "Version: ${BUILD_VERSION}"
                    echo "Environment: ${DEPLOY_ENV}"
                    echo "Git Commit: ${GIT_COMMIT}"
                    echo "Git Branch: ${GIT_BRANCH}"
                    echo "========================="
                '''
            }
        }
        
        stage('Code Quality & Security') {
            parallel {
                stage('SonarQube Analysis') {
                    steps {
                        container('docker') {
                            script {
                                def scannerHome = tool 'SonarQubeScanner'
                                withSonarQubeEnv('SonarQube') {
                                    sh """
                                        ${scannerHome}/bin/sonar-scanner \
                                        -Dsonar.projectKey=${APP_NAME} \
                                        -Dsonar.projectName=${APP_NAME} \
                                        -Dsonar.projectVersion=${BUILD_VERSION} \
                                        -Dsonar.sources=. \
                                        -Dsonar.exclusions=**/*test*/**,**/*.test.js,**/node_modules/**,**/vendor/**
                                    """
                                }
                            }
                        }
                    }
                }
                
                stage('Security Scan') {
                    steps {
                        container('docker') {
                            sh '''
                                # Install security scanning tools
                                apk add --no-cache git
                                
                                # Secrets scanning with truffleHog
                                docker run --rm -v $(pwd):/pwd \
                                    trufflesecurity/trufflehog:latest \
                                    filesystem /pwd --no-verification --json > security-scan.json || true
                                
                                # Dependency vulnerability scanning
                                if [ -f "package.json" ]; then
                                    npm audit --json > npm-audit.json || true
                                elif [ -f "requirements.txt" ]; then
                                    pip install safety
                                    safety check --json > safety-check.json || true
                                elif [ -f "go.mod" ]; then
                                    go list -json -m all | nancy sleuth > nancy-scan.json || true
                                fi
                            '''
                        }
                    }
                }
            }
        }
        
        stage('Build & Test') {
            parallel {
                stage('Application Build') {
                    steps {
                        container('docker') {
                            script {
                                // Build application based on tech stack
                                if (fileExists('package.json')) {
                                    sh '''
                                        npm ci
                                        npm run build
                                    '''
                                } else if (fileExists('pom.xml')) {
                                    sh '''
                                        mvn clean compile package -DskipTests
                                    '''
                                } else if (fileExists('go.mod')) {
                                    sh '''
                                        go mod download
                                        go build -o app .
                                    '''
                                } else if (fileExists('requirements.txt')) {
                                    sh '''
                                        pip install -r requirements.txt
                                        python -m py_compile **/*.py
                                    '''
                                }
                            }
                        }
                    }
                }
                
                stage('Unit Tests') {
                    when {
                        not { params.SKIP_TESTS }
                    }
                    steps {
                        container('docker') {
                            script {
                                // Run tests based on tech stack
                                if (fileExists('package.json')) {
                                    sh '''
                                        npm test -- --coverage --watchAll=false
                                        npm run test:integration
                                    '''
                                } else if (fileExists('pom.xml')) {
                                    sh '''
                                        mvn test
                                    '''
                                } else if (fileExists('go.mod')) {
                                    sh '''
                                        go test -v -cover ./...
                                    '''
                                } else if (fileExists('requirements.txt')) {
                                    sh '''
                                        python -m pytest --cov=. --cov-report=xml
                                    '''
                                }
                            }
                        }
                    }
                    post {
                        always {
                            // Publish test results
                            publishTestResults testResultsPattern: '**/test-results.xml'
                            publishCoverageReports(
                                adapters: [
                                    createGenericCoverageAdapter('**/coverage.xml')
                                ]
                            )
                        }
                    }
                }
            }
        }
        
        stage('Docker Build & Scan') {
            steps {
                container('docker') {
                    script {
                        // Multi-stage Docker build
                        sh '''
                            docker build \
                                --build-arg BUILD_VERSION=${BUILD_VERSION} \
                                --build-arg GIT_COMMIT=${GIT_COMMIT} \
                                -t ${DOCKER_REGISTRY}/${APP_NAME}:${BUILD_VERSION} \
                                -t ${DOCKER_REGISTRY}/${APP_NAME}:latest \
                                .
                        '''
                        
                        // Container security scanning
                        sh '''
                            # Install trivy for container scanning
                            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
                            
                            # Scan the built image
                            trivy image --format json --output trivy-report.json \
                                ${DOCKER_REGISTRY}/${APP_NAME}:${BUILD_VERSION}
                            
                            # Check for critical vulnerabilities
                            CRITICAL_COUNT=$(cat trivy-report.json | jq '.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL") | length' | wc -l)
                            if [ "$CRITICAL_COUNT" -gt "0" ]; then
                                echo "WARNING: Found $CRITICAL_COUNT critical vulnerabilities"
                                # Set build as unstable but continue
                                exit 0
                            fi
                        '''
                        
                        // Push to registry
                        sh '''
                            echo $DOCKER_REGISTRY_PSW | docker login -u $DOCKER_REGISTRY_USR --password-stdin
                            docker push ${DOCKER_REGISTRY}/${APP_NAME}:${BUILD_VERSION}
                            docker push ${DOCKER_REGISTRY}/${APP_NAME}:latest
                        '''
                    }
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    def deploymentApproved = true
                    
                    // Require approval for production deployments
                    if (params.DEPLOY_ENV == 'production') {
                        deploymentApproved = false
                        try {
                            timeout(time: 10, unit: 'MINUTES') {
                                deploymentApproved = input(
                                    id: 'DeployApproval',
                                    message: 'Deploy to production?',
                                    parameters: [
                                        booleanParam(
                                            defaultValue: false,
                                            description: 'Confirm production deployment',
                                            name: 'APPROVED'
                                        )
                                    ]
                                )
                            }
                        } catch (err) {
                            deploymentApproved = false
                            currentBuild.result = 'ABORTED'
                            error('Production deployment not approved within timeout')
                        }
                    }
                    
                    if (deploymentApproved) {
                        container('helm') {
                            // Deploy using Helm
                            sh '''
                                # Add/update Helm repositories
                                helm repo add stable https://charts.helm.sh/stable
                                helm repo update
                                
                                # Create namespace if it doesn't exist
                                kubectl create namespace ${TARGET_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                
                                # Deploy application
                                helm upgrade --install ${APP_NAME} ./helm-charts/${APP_NAME} \
                                    --namespace ${TARGET_NAMESPACE} \
                                    --set image.repository=${DOCKER_REGISTRY}/${APP_NAME} \
                                    --set image.tag=${BUILD_VERSION} \
                                    --set replicaCount=${REPLICAS} \
                                    --set resources.limits.cpu=${RESOURCES} \
                                    --set resources.limits.memory=${RESOURCES} \
                                    --set environment=${DEPLOY_ENV} \
                                    --wait --timeout=300s
                            '''
                        }
                        
                        // Health check after deployment
                        container('kubectl') {
                            sh '''
                                # Wait for rollout to complete
                                kubectl rollout status deployment/${APP_NAME} -n ${TARGET_NAMESPACE} --timeout=300s
                                
                                # Verify pods are running
                                kubectl get pods -n ${TARGET_NAMESPACE} -l app=${APP_NAME}
                                
                                # Run health check
                                sleep 30
                                HEALTH_CHECK_URL="http://${APP_NAME}.${TARGET_NAMESPACE}.svc.cluster.local:8080/health"
                                if ! kubectl run health-check --rm -i --restart=Never --image=curlimages/curl -- curl -f $HEALTH_CHECK_URL; then
                                    echo "Health check failed!"
                                    exit 1
                                fi
                            '''
                        }
                    }
                }
            }
        }
        
        stage('Integration Tests') {
            when {
                anyOf {
                    expression { params.DEPLOY_ENV in ['qa', 'uat', 'staging'] }
                    expression { params.DEPLOY_ENV == 'production' && currentBuild.result != 'FAILURE' }
                }
            }
            parallel {
                stage('API Tests') {
                    steps {
                        container('docker') {
                            script {
                                // Run API tests using Newman (Postman CLI)
                                sh '''
                                    if [ -f "tests/api/postman_collection.json" ]; then
                                        docker run --rm -v $(pwd)/tests/api:/etc/newman \
                                            postman/newman run postman_collection.json \
                                            --environment postman_environment_${DEPLOY_ENV}.json \
                                            --reporters cli,json \
                                            --reporter-json-export newman-report.json
                                    fi
                                '''
                            }
                        }
                    }
                }
                
                stage('Performance Tests') {
                    when {
                        expression { params.DEPLOY_ENV in ['uat', 'staging'] }
                    }
                    steps {
                        container('docker') {
                            sh '''
                                # Run performance tests using k6
                                if [ -f "tests/performance/load-test.js" ]; then
                                    docker run --rm -v $(pwd)/tests/performance:/scripts \
                                        grafana/k6 run /scripts/load-test.js \
                                        --env BASE_URL=http://${APP_NAME}.${TARGET_NAMESPACE}.svc.cluster.local:8080
                                fi
                            '''
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            // Clean up
            sh 'docker system prune -f'
            
            // Archive artifacts
            archiveArtifacts artifacts: '**/*-report.*', allowEmptyArchive: true
            
            // Publish reports
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: '*.html',
                reportName: 'Test Reports'
            ])
        }
        
        success {
            sendSlackNotification('SUCCESS')
            
            // Trigger downstream jobs for next environment
            script {
                def nextEnv = getNextEnvironment(params.DEPLOY_ENV)
                if (nextEnv && params.DEPLOY_ENV != 'production') {
                    build job: env.JOB_NAME,
                          parameters: [
                              string(name: 'DEPLOY_ENV', value: nextEnv),
                              booleanParam(name: 'SKIP_TESTS', value: false)
                          ],
                          wait: false
                }
            }
        }
        
        failure {
            sendSlackNotification('FAILURE')
            
            // Auto-rollback for production
            script {
                if (params.DEPLOY_ENV == 'production') {
                    container('helm') {
                        sh '''
                            echo "Rolling back production deployment..."
                            helm rollback ${APP_NAME} -n ${TARGET_NAMESPACE}
                        '''
                    }
                }
            }
        }
        
        unstable {
            sendSlackNotification('UNSTABLE')
        }
    }
}

// Helper functions
def getReplicaCount(env) {
    switch(env) {
        case 'dev': return '1'
        case 'qa': return '2'
        case 'uat': return '2'
        case 'staging': return '3'
        case 'production': return '5'
        default: return '1'
    }
}

def getResourceLimits(env) {
    switch(env) {
        case 'dev': return '500m'
        case 'qa': return '1000m'
        case 'uat': return '1000m'
        case 'staging': return '2000m'
        case 'production': return '4000m'
        default: return '500m'
    }
}

def getNextEnvironment(currentEnv) {
    def envSequence = ['dev', 'qa', 'uat', 'staging', 'production']
    def currentIndex = envSequence.indexOf(currentEnv)
    return currentIndex >= 0 && currentIndex < envSequence.size() - 1 ? 
           envSequence[currentIndex + 1] : null
}

def sendSlackNotification(status) {
    def color = [
        'STARTED': '#FFFF00',
        'SUCCESS': '#36A64F',
        'FAILURE': '#FF0000',
        'UNSTABLE': '#FF8C00'
    ][status] ?: '#000000'
    
    def message = """
        *${status}*: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'
        *Environment*: ${params.DEPLOY_ENV}
        *Version*: ${BUILD_VERSION}
        *Branch*: ${env.GIT_BRANCH}
        *Duration*: ${currentBuild.durationString}
        *Build URL*: ${env.BUILD_URL}
    """
    
    slackSend(
        channel: '#deployments',
        color: color,
        message: message,
        teamDomain: 'your-team',
        webhookUrl: env.SLACK_WEBHOOK
    )
}
```

## GitLab CI/CD

### .gitlab-ci.yml

```yaml
# GitLab CI/CD Pipeline
variables:
  DOCKER_REGISTRY: $CI_REGISTRY
  APP_NAME: $CI_PROJECT_NAME
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: ""
  KUBECONFIG: /tmp/kubeconfig
  
stages:
  - validate
  - build
  - test
  - security
  - package
  - deploy-dev
  - deploy-qa
  - deploy-uat
  - deploy-staging
  - deploy-production
  - cleanup

# Global before script
before_script:
  - export BUILD_VERSION="${CI_PIPELINE_IID}-${CI_COMMIT_SHORT_SHA}"
  - echo "Building version $BUILD_VERSION"

# Templates
.deploy_template: &deploy_template
  image: bitnami/kubectl:latest
  before_script:
    - apk add --no-cache helm
    - echo $KUBECONFIG_CONTENT | base64 -d > $KUBECONFIG
    - export BUILD_VERSION="${CI_PIPELINE_IID}-${CI_COMMIT_SHORT_SHA}"
  script:
    - |
      # Create namespace if it doesn't exist
      kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
      
      # Deploy with Helm
      helm upgrade --install ${APP_NAME} ./helm-charts/${APP_NAME} \
        --namespace ${NAMESPACE} \
        --set image.repository=${DOCKER_REGISTRY}/${APP_NAME} \
        --set image.tag=${BUILD_VERSION} \
        --set replicaCount=${REPLICAS} \
        --set environment=${ENVIRONMENT} \
        --set ingress.host=${INGRESS_HOST} \
        --wait --timeout=300s
      
      # Health check
      kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s
      
      # Verify deployment
      kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME}
  after_script:
    - rm -f $KUBECONFIG

# Validate stage
validate:
  stage: validate
  image: alpine:latest
  script:
    - apk add --no-cache git
    - |
      # Validate commit message format
      if [[ ! "$CI_COMMIT_MESSAGE" =~ ^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+ ]]; then
        echo "Invalid commit message format!"
        exit 1
      fi
    - |
      # Check for required files
      required_files=("Dockerfile" "helm-charts")
      for file in "${required_files[@]}"; do
        if [[ ! -e "$file" ]]; then
          echo "Required file/directory missing: $file"
          exit 1
        fi
      done
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS'
      when: never
    - if: '$CI_COMMIT_BRANCH'

# Build stage
build:
  stage: build
  image: docker:20.10.12
  services:
    - docker:20.10.12-dind
  variables:
    DOCKER_HOST: tcp://docker:2376
    DOCKER_TLS_CERTDIR: "/certs"
  script:
    - echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
    - |
      # Multi-stage build with build args
      docker build \
        --build-arg BUILD_VERSION=$BUILD_VERSION \
        --build-arg GIT_COMMIT=$CI_COMMIT_SHA \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        -t $CI_REGISTRY_IMAGE:$BUILD_VERSION \
        -t $CI_REGISTRY_IMAGE:latest \
        .
    - docker push $CI_REGISTRY_IMAGE:$BUILD_VERSION
    - docker push $CI_REGISTRY_IMAGE:latest
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
    - if: '$CI_COMMIT_BRANCH == "develop"'
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

# Test stages
unit-tests:
  stage: test
  image: node:16-alpine  # Adjust based on your tech stack
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
  script:
    - npm ci
    - npm run test:unit -- --coverage
    - npm run lint
  artifacts:
    when: always
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
    paths:
      - coverage/
    expire_in: 1 week
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'

integration-tests:
  stage: test
  image: docker:20.10.12
  services:
    - docker:20.10.12-dind
    - postgres:13
    - redis:6
  variables:
    POSTGRES_DB: testdb
    POSTGRES_USER: testuser
    POSTGRES_PASSWORD: testpass
    DATABASE_URL: postgres://testuser:testpass@postgres:5432/testdb
    REDIS_URL: redis://redis:6379
  script:
    - apk add --no-cache docker-compose
    - docker-compose -f docker-compose.test.yml up -d
    - sleep 30  # Wait for services to be ready
    - docker-compose -f docker-compose.test.yml exec -T app npm run test:integration
  after_script:
    - docker-compose -f docker-compose.test.yml down
  artifacts:
    when: always
    reports:
      junit: test-results/integration-results.xml

# Security scanning
security-scan:
  stage: security
  image: docker:20.10.12
  services:
    - docker:20.10.12-dind
  before_script:
    - apk add --no-cache git curl
  script:
    - |
      # Container vulnerability scanning with Trivy
      curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
      trivy image --format json --output trivy-report.json $CI_REGISTRY_IMAGE:$BUILD_VERSION
      
      # Check for critical vulnerabilities
      CRITICAL_COUNT=$(cat trivy-report.json | jq '.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL") | length' | wc -l)
      if [ "$CRITICAL_COUNT" -gt "5" ]; then
        echo "Too many critical vulnerabilities found: $CRITICAL_COUNT"
        exit 1
      fi
    - |
      # Secret scanning with GitLeaks
      docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" --report-format=json --report-path=/path/gitleaks-report.json || true
    - |
      # Dependency scanning
      if [ -f "package.json" ]; then
        npm audit --audit-level high
      elif [ -f "requirements.txt" ]; then
        pip install safety
        safety check
      fi
  artifacts:
    when: always
    paths:
      - trivy-report.json
      - gitleaks-report.json
    expire_in: 1 week
  allow_failure: true

# SAST (Static Application Security Testing)
sast:
  stage: security
  include:
    - template: Security/SAST.gitlab-ci.yml

# Dependency scanning
dependency_scanning:
  stage: security
  include:
    - template: Security/Dependency-Scanning.gitlab-ci.yml

# License scanning
license_scanning:
  stage: security
  include:
    - template: Security/License-Scanning.gitlab-ci.yml

# Package stage
package:
  stage: package
  image: docker:20.10.12
  services:
    - docker:20.10.12-dind
  script:
    - echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
    - docker pull $CI_REGISTRY_IMAGE:$BUILD_VERSION
    - |
      # Add additional tags for release
      if [[ "$CI_COMMIT_BRANCH" == "main" ]]; then
        docker tag $CI_REGISTRY_IMAGE:$BUILD_VERSION $CI_REGISTRY_IMAGE:stable
        docker push $CI_REGISTRY_IMAGE:stable
      fi
    - |
      # Generate SBOM (Software Bill of Materials)
      apk add --no-cache curl
      curl -sfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
      syft $CI_REGISTRY_IMAGE:$BUILD_VERSION -o json > sbom.json
  artifacts:
    paths:
      - sbom.json
    expire_in: 1 month

# Deployment stages
deploy-dev:
  stage: deploy-dev
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-dev
    ENVIRONMENT: dev
    REPLICAS: "1"
    INGRESS_HOST: ${APP_NAME}-dev.example.com
  environment:
    name: development
    url: https://${APP_NAME}-dev.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "develop"'
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: manual

deploy-qa:
  stage: deploy-qa
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-qa
    ENVIRONMENT: qa
    REPLICAS: "2"
    INGRESS_HOST: ${APP_NAME}-qa.example.com
  environment:
    name: qa
    url: https://${APP_NAME}-qa.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "develop"'
      when: manual
  needs:
    - deploy-staging
  before_script:
    - !reference [.deploy_template, before_script]
    - |
      # Additional production checks
      echo "Performing pre-production validations..."
      
      # Check if staging environment is healthy
      STAGING_URL="https://${APP_NAME}-staging.example.com/health"
      if ! curl -f $STAGING_URL; then
        echo "Staging environment is not healthy, aborting production deployment"
        exit 1
      fi
      
      # Backup current production state
      helm get values ${APP_NAME} -n ${NAMESPACE} > production-backup-values.yaml || echo "No existing deployment to backup"
  after_script:
    - !reference [.deploy_template, after_script]
    - |
      # Post-deployment verification
      echo "Performing post-deployment verification..."
      sleep 60  # Wait for application to fully start
      
      PROD_URL="https://${APP_NAME}.example.com"
      if curl -f $PROD_URL/health; then
        echo "Production deployment successful!"
        # Send success notification
        curl -X POST -H 'Content-type: application/json' \
          --data '{"text":"🚀 Production deployment successful for '${APP_NAME}' version '${BUILD_VERSION}'"}' \
          $SLACK_WEBHOOK_URL
      else
        echo "Production health check failed, initiating rollback"
        helm rollback ${APP_NAME} -n ${NAMESPACE}
        exit 1
      fi

# Cleanup stage
cleanup:
  stage: cleanup
  image: docker:20.10.12
  script:
    - |
      # Clean up old images (keep last 5 versions)
      echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
      
      # Get list of tags and keep only recent ones
      TAGS=$(curl -s -H "PRIVATE-TOKEN: $CI_JOB_TOKEN" \
        "$CI_API_V4_URL/projects/$CI_PROJECT_ID/registry/repositories" | \
        jq -r '.[0].id')
      
      if [ "$TAGS" != "null" ]; then
        curl -s -H "PRIVATE-TOKEN: $CI_JOB_TOKEN" \
          "$CI_API_V4_URL/projects/$CI_PROJECT_ID/registry/repositories/$TAGS/tags" | \
          jq -r '.[] | select(.name | test("^[0-9]+-[a-f0-9]{8}$")) | .name' | \
          sort -V | head -n -5 | \
          while read tag; do
            echo "Deleting old tag: $tag"
            curl -X DELETE -H "PRIVATE-TOKEN: $CI_JOB_TOKEN" \
              "$CI_API_V4_URL/projects/$CI_PROJECT_ID/registry/repositories/$TAGS/tags/$tag"
          done
      fi
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: delayed
      start_in: 1 hour
  allow_failure: true

# Performance testing job
performance-test:
  stage: deploy-uat
  image: grafana/k6:latest
  script:
    - |
      if [ -f "tests/performance/load-test.js" ]; then
        k6 run tests/performance/load-test.js \
          --env BASE_URL=https://${APP_NAME}-uat.example.com \
          --out json=k6-results.json
      fi
  artifacts:
    when: always
    reports:
      performance: k6-results.json
    expire_in: 1 week
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs:
    - deploy-uat
```

## GitHub Actions

### .github/workflows/ci-cd.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options:
        - dev
        - qa
        - uat
        - staging
        - production
      skip_tests:
        description: 'Skip tests'
        required: false
        default: false
        type: boolean

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.9'

jobs:
  # Validation job
  validate:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      should_deploy: ${{ steps.changes.outputs.should_deploy }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate version
        id: version
        run: |
          VERSION="${GITHUB_RUN_NUMBER}-${GITHUB_SHA::8}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "Generated version: $VERSION"

      - name: Detect changes
        id: changes
        uses: dorny/paths-filter@v2
        with:
          filters: |
            should_deploy:
              - 'src/**'
              - 'Dockerfile'
              - 'helm-charts/**'
              - 'package.json'
              - 'requirements.txt'

      - name: Validate commit message
        if: github.event_name == 'push'
        run: |
          if [[ ! "${{ github.event.head_commit.message }}" =~ ^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+ ]]; then
            echo "Invalid commit message format!"
            exit 1
          fi

      - name: Check required files
        run: |
          required_files=("Dockerfile" "helm-charts")
          for file in "${required_files[@]}"; do
            if [[ ! -e "$file" ]]; then
              echo "Required file/directory missing: $file"
              exit 1
            fi
          done

  # Security and quality checks
  security:
    runs-on: ubuntu-latest
    needs: validate
    permissions:
      security-events: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}

      - name: Run CodeQL Analysis
        uses: github/codeql-action/init@v2
        with:
          languages: javascript, python, go, java
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v2
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2

  # Build and test job
  build-and-test:
    runs-on: ubuntu-latest
    needs: validate
    strategy:
      matrix:
        test-type: [unit, integration]
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        if: hashFiles('package.json') != ''
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Set up Python
        if: hashFiles('requirements.txt') != ''
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Set up Go
        if: hashFiles('go.mod') != ''
        uses: actions/setup-go@v4
        with:
          go-version: '1.19'
          cache: true

      - name: Install dependencies
        run: |
          if [[ -f "package.json" ]]; then
            npm ci
          elif [[ -f "requirements.txt" ]]; then
            pip install -r requirements.txt
            pip install pytest pytest-cov
          elif [[ -f "go.mod" ]]; then
            go mod download
          fi

      - name: Run linting
        run: |
          if [[ -f "package.json" ]]; then
            npm run lint
          elif [[ -f "requirements.txt" ]]; then
            pip install flake8 black
            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
            black --check .
          elif [[ -f "go.mod" ]]; then
            go vet ./...
            go fmt ./...
          fi

      - name: Run unit tests
        if: matrix.test-type == 'unit' && !inputs.skip_tests
        run: |
          if [[ -f "package.json" ]]; then
            npm run test:unit -- --coverage --watchAll=false
          elif [[ -f "requirements.txt" ]]; then
            pytest tests/unit --cov=. --cov-report=xml --cov-report=html
          elif [[ -f "go.mod" ]]; then
            go test -v -cover -coverprofile=coverage.out ./...
          fi

      - name: Run integration tests
        if: matrix.test-type == 'integration' && !inputs.skip_tests
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
        run: |
          if [[ -f "package.json" ]]; then
            npm run test:integration
          elif [[ -f "requirements.txt" ]]; then
            pytest tests/integration
          elif [[ -f "go.mod" ]]; then
            go test -v -tags=integration ./tests/integration/...
          fi

      - name: Upload coverage reports
        if: matrix.test-type == 'unit'
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results-${{ matrix.test-type }}
          path: |
            coverage/
            test-results/
          retention-days: 30

  # Docker build and push
  docker:
    runs-on: ubuntu-latest
    needs: [validate, build-and-test]
    if: needs.validate.outputs.should_deploy == 'true'
    permissions:
      contents: read
      packages: write
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=raw,value=${{ needs.validate.outputs.version }}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          build-args: |
            BUILD_VERSION=${{ needs.validate.outputs.version }}
            GIT_COMMIT=${{ github.sha }}
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run Trivy vulnerability scanner on image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ needs.validate.outputs.version }}
          format: 'sarif'
          output: 'trivy-image-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-image-results.sarif'

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ needs.validate.outputs.version }}
          format: spdx-json
          output-file: sbom.spdx.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v3
        with:
          name: sbom
          path: sbom.spdx.json

  # Deployment jobs
  deploy-dev:
    runs-on: ubuntu-latest
    needs: [validate, docker]
    if: github.ref == 'refs/heads/develop' || github.event.inputs.environment == 'dev'
    environment:
      name: development
      url: https://${{ github.event.repository.name }}-dev.example.com
    steps:
      - name: Deploy to Development
        uses: ./.github/actions/deploy
        with:
          environment: dev
          namespace: ${{ github.event.repository.name }}-dev
          image-tag: ${{ needs.validate.outputs.version }}
          replicas: 1
          kubeconfig: ${{ secrets.KUBECONFIG_DEV }}
          ingress-host: ${{ github.event.repository.name }}-dev.example.com

  deploy-qa:
    runs-on: ubuntu-latest
    needs: [validate, docker, deploy-dev]
    if: github.ref == 'refs/heads/develop' || github.event.inputs.environment == 'qa'
    environment:
      name: qa
      url: https://${{ github.event.repository.name }}-qa.example.com
    steps:
      - name: Deploy to QA
        uses: ./.github/actions/deploy
        with:
          environment: qa
          namespace: ${{ github.event.repository.name }}-qa
          image-tag: ${{ needs.validate.outputs.version }}
          replicas: 2
          kubeconfig: ${{ secrets.KUBECONFIG_QA }}
          ingress-host: ${{ github.event.repository.name }}-qa.example.com

      - name: Run API Tests
        run: |
          if [[ -f "tests/api/postman_collection.json" ]]; then
            npx newman run tests/api/postman_collection.json \
              --environment tests/api/postman_environment_qa.json \
              --reporters cli,json \
              --reporter-json-export newman-report.json
          fi

      - name: Upload API test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: api-test-results
          path: newman-report.json

  deploy-uat:
    runs-on: ubuntu-latest
    needs: [validate, docker, deploy-qa]
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'uat'
    environment:
      name: uat
      url: https://${{ github.event.repository.name }}-uat.example.com
    steps:
      - name: Deploy to UAT
        uses: ./.github/actions/deploy
        with:
          environment: uat
          namespace: ${{ github.event.repository.name }}-uat
          image-tag: ${{ needs.validate.outputs.version }}
          replicas: 2
          kubeconfig: ${{ secrets.KUBECONFIG_UAT }}
          ingress-host: ${{ github.event.repository.name }}-uat.example.com

      - name: Run Performance Tests
        run: |
          if [[ -f "tests/performance/load-test.js" ]]; then
            docker run --rm -v $(pwd)/tests/performance:/scripts \
              grafana/k6 run /scripts/load-test.js \
              --env BASE_URL=https://${{ github.event.repository.name }}-uat.example.com
          fi

  deploy-staging:
    runs-on: ubuntu-latest
    needs: [validate, docker, deploy-uat]
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'staging'
    environment:
      name: staging
      url: https://${{ github.event.repository.name }}-staging.example.com
    steps:
      - name: Pre-deployment smoke tests
        run: |
          # Run smoke tests against UAT before promoting to staging
          if [[ -f "tests/smoke/smoke-tests.sh" ]]; then
            ./tests/smoke/smoke-tests.sh https://${{ github.event.repository.name }}-uat.example.com
          fi

      - name: Deploy to Staging
        uses: ./.github/actions/deploy
        with:
          environment: staging
          namespace: ${{ github.event.repository.name }}-staging
          image-tag: ${{ needs.validate.outputs.version }}
          replicas: 3
          kubeconfig: ${{ secrets.KUBECONFIG_STAGING }}
          ingress-host: ${{ github.event.repository.name }}-staging.example.com

  deploy-production:
    runs-on: ubuntu-latest
    needs: [validate, docker, deploy-staging]
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'production'
    environment:
      name: production
      url: https://${{ github.event.repository.name }}.example.com
    steps:
      - name: Pre-production validations
        run: |
          # Validate staging environment health
          STAGING_URL="https://${{ github.event.repository.name }}-staging.example.com/health"
          if ! curl -f $STAGING_URL; then
            echo "Staging environment is not healthy, aborting production deployment"
            exit 1
          fi
          
          echo "All pre-production validations passed"

      - name: Deploy to Production
        uses: ./.github/actions/deploy
        with:
          environment: production
          namespace: ${{ github.event.repository.name }}-prod
          image-tag: ${{ needs.validate.outputs.version }}
          replicas: 5
          kubeconfig: ${{ secrets.KUBECONFIG_PROD }}
          ingress-host: ${{ github.event.repository.name }}.example.com

      - name: Post-deployment verification
        run: |
          echo "Waiting for deployment to stabilize..."
          sleep 60
          
          PROD_URL="https://${{ github.event.repository.name }}.example.com"
          if curl -f $PROD_URL/health; then
            echo "Production deployment successful!"
          else
            echo "Production health check failed!"
            exit 1
          fi

      - name: Send deployment notification
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          channel: '#deployments'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
          message: |
            🚀 Production deployment ${{ job.status }} for ${{ github.event.repository.name }}
            Version: ${{ needs.validate.outputs.version }}
            Commit: ${{ github.sha }}
            Actor: ${{ github.actor }}

  # Cleanup job
  cleanup:
    runs-on: ubuntu-latest
    needs: [deploy-production]
    if: always()
    steps:
      - name: Clean up old images
        uses: actions/delete-package-versions@v4
        with:
          package-name: ${{ github.event.repository.name }}
          package-type: 'container'
          min-versions-to-keep: 10
          ignore-versions: '^(latest|stable)
    - deploy-dev

deploy-uat:
  stage: deploy-uat
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-uat
    ENVIRONMENT: uat
    REPLICAS: "2"
    INGRESS_HOST: ${APP_NAME}-uat.example.com
  environment:
    name: uat
    url: https://${APP_NAME}-uat.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs:
    - deploy-qa

deploy-staging:
  stage: deploy-staging
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-staging
    ENVIRONMENT: staging
    REPLICAS: "3"
    INGRESS_HOST: ${APP_NAME}-staging.example.com
  environment:
    name: staging
    url: https://${APP_NAME}-staging.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs:
    - deploy-uat
  before_script:
    - !reference [.deploy_template, before_script]
    - |
      # Run smoke tests before staging deployment
      if [ -f "tests/smoke/smoke-tests.sh" ]; then
        ./tests/smoke/smoke-tests.sh $UAT_URL
      fi

deploy-production:
  stage: deploy-production
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-prod
    ENVIRONMENT: production
    REPLICAS: "5"
    INGRESS_HOST: ${APP_NAME}.example.com
  environment:
    name: production
    url: https://${APP_NAME}.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs:
```

### Custom GitHub Action - Deploy Action

#### .github/actions/deploy/action.yml

```yaml
name: 'Deploy to Kubernetes'
description: 'Deploy application to Kubernetes using Helm'

inputs:
  environment:
    description: 'Target environment'
    required: true
  namespace:
    description: 'Kubernetes namespace'
    required: true
  image-tag:
    description: 'Docker image tag'
    required: true
  replicas:
    description: 'Number of replicas'
    required: true
  kubeconfig:
    description: 'Kubernetes config'
    required: true
  ingress-host:
    description: 'Ingress hostname'
    required: true

runs:
  using: 'composite'
  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.24.0'

    - name: Set up Helm
      uses: azure/setup-helm@v3
      with:
        version: '3.10.0'

    - name: Configure kubectl
      shell: bash
      run: |
        echo "${{ inputs.kubeconfig }}" | base64 -d > /tmp/kubeconfig
        echo "KUBECONFIG=/tmp/kubeconfig" >> $GITHUB_ENV

    - name: Create namespace
      shell: bash
      run: |
        kubectl create namespace ${{ inputs.namespace }} --dry-run=client -o yaml | kubectl apply -f -

    - name: Deploy with Helm
      shell: bash
      run: |
        helm upgrade --install ${{ github.event.repository.name }} ./helm-charts/${{ github.event.repository.name }} \
          --namespace ${{ inputs.namespace }} \
          --set image.repository=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }} \
          --set image.tag=${{ inputs.image-tag }} \
          --set replicaCount=${{ inputs.replicas }} \
          --set environment=${{ inputs.environment }} \
          --set ingress.host=${{ inputs.ingress-host }} \
          --wait --timeout=300s

    - name: Verify deployment
      shell: bash
      run: |
        kubectl rollout status deployment/${{ github.event.repository.name }} -n ${{ inputs.namespace }} --timeout=300s
        kubectl get pods -n ${{ inputs.namespace }} -l app=${{ github.event.repository.name }}

    - name: Health check
      shell: bash
      run: |
        sleep 30
        if kubectl run health-check-${{ github.run_number }} --rm -i --restart=Never --image=curlimages/curl -- \
           curl -f http://${{ github.event.repository.name }}.${{ inputs.namespace }}.svc.cluster.local:8080/health; then
          echo "Health check passed"
        else
          echo "Health check failed"
          exit 1
        fi

    - name: Clean up
      shell: bash
      if: always()
      run: |
        rm -f /tmp/kubeconfig
```

## Environment Management

### Environment Configuration Files

#### environments/dev/values.yaml
```yaml
# Development Environment Configuration
replicaCount: 1

image:
  repository: ""
  tag: ""
  pullPolicy: Always

service:
  type: ClusterIP
  port: 8080

ingress:
  enabled: true
  className: nginx
  host: ""
  tls:
    enabled: false

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: false

env:
  NODE_ENV: development
  LOG_LEVEL: debug
  DATABASE_POOL_SIZE: "5"

configMap:
  data:
    app.properties: |
      debug=true
      feature.flags.new_ui=true

secrets:
  database:
    host: dev-db.internal
    name: devdb
  cache:
    url: redis://dev-cache.internal:6379

monitoring:
  enabled: true
  metrics: true
  tracing: false
```

#### environments/production/values.yaml
```yaml
# Production Environment Configuration
replicaCount: 5

image:
  repository: ""
  tag: ""
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

ingress:
  enabled: true
  className: nginx
  host: ""
  tls:
    enabled: true
    secretName: app-tls

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

env:
  NODE_ENV: production
  LOG_LEVEL: info
  DATABASE_POOL_SIZE: "20"

configMap:
  data:
    app.properties: |
      debug=false
      feature.flags.new_ui=false

secrets:
  database:
    host: prod-db.internal
    name: proddb
  cache:
    url: redis://prod-cache.internal:6379

monitoring:
  enabled: true
  metrics: true
  tracing: true
  alerting: true

backup:
  enabled: true
  schedule: "0 2 * * *"
  retention: 30d
```

## Security Implementation

### Secret Management

#### Using External Secret Operator
```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: app-prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
  - secretKey: database-password
    remoteRef:
      key: secret/prod/database
      property: password
  - secretKey: api-key
    remoteRef:
      key: secret/prod/api
      property: key
```

### RBAC Configuration

#### rbac.yaml
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: app-prod
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: app-prod
  name: app-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-rolebinding
  namespace: app-prod
subjects:
- kind: ServiceAccount
  name: app-service-account
  namespace: app-prod
roleRef:
  kind: Role
  name: app-role
  apiGroup: rbac.authorization.k8s.io
```

### Security Policies

#### Network Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-network-policy
  namespace: app-prod
spec:
  podSelector:
    matchLabels:
      app: myapp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: UDP
      port: 53
```

#### Pod Security Policy
```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: app-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Monitoring & Notifications

### Prometheus Monitoring

#### ServiceMonitor
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-metrics
  namespace: app-prod
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### Alerting Rules

#### PrometheusRule
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: app-alerts
  namespace: app-prod
spec:
  groups:
  - name: app.rules
    rules:
    - alert: AppDown
      expr: up{job="myapp"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Application is down"
        description: "{{ $labels.instance }} has been down for more than 1 minute"
    
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }} requests per second"
    
    - alert: HighMemoryUsage
      expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage"
        description
    - deploy-dev

deploy-uat:
  stage: deploy-uat
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-uat
    ENVIRONMENT: uat
    REPLICAS: "2"
    INGRESS_HOST: ${APP_NAME}-uat.example.com
  environment:
    name: uat
    url: https://${APP_NAME}-uat.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs:
    - deploy-qa

deploy-staging:
  stage: deploy-staging
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-staging
    ENVIRONMENT: staging
    REPLICAS: "3"
    INGRESS_HOST: ${APP_NAME}-staging.example.com
  environment:
    name: staging
    url: https://${APP_NAME}-staging.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs:
    - deploy-uat
  before_script:
    - !reference [.deploy_template, before_script]
    - |
      # Run smoke tests before staging deployment
      if [ -f "tests/smoke/smoke-tests.sh" ]; then
        ./tests/smoke/smoke-tests.sh $UAT_URL
      fi

deploy-production:
  stage: deploy-production
  <<: *deploy_template
  variables:
    NAMESPACE: ${APP_NAME}-prod
    ENVIRONMENT: production
    REPLICAS: "5"
    INGRESS_HOST: ${APP_NAME}.example.com
  environment:
    name: production
    url: https://${APP_NAME}.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  needs: