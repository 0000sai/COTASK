# Enterprise Microservices CI/CD Pipeline Architecture

## Architecture Overview

### Multi-Platform CI/CD Strategy
- **Jenkins**: Primary orchestration and enterprise integration
- **GitLab CI**: Code quality, security scanning, and container builds
- **GitHub Actions**: Open source integrations and community workflows
- **AWS Services**: ECR (registry), ECS/EKS (deployment), CloudFormation/CDK

### Environment Strategy
- **DEV**: Development environment with rapid deployment
- **UAT**: User Acceptance Testing with production-like data
- **PROD**: Production environment with blue-green deployment

---

## Repository Structure

```
microservices-platform/
├── services/
│   ├── user-service/
│   ├── order-service/
│   ├── payment-service/
│   └── ... (40+ services)
├── infrastructure/
│   ├── terraform/
│   ├── helm-charts/
│   └── k8s-manifests/
├── shared/
│   ├── libraries/
│   ├── docker-base-images/
│   └── pipeline-templates/
└── ci-cd/
    ├── jenkins/
    ├── gitlab/
    └── github-actions/
```

---

## 1. Jenkins Pipeline Configuration

### Jenkinsfile Template (per microservice)

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
    image: docker:20.10.7-dind
    securityContext:
      privileged: true
  - name: kubectl
    image: bitnami/kubectl:latest
  - name: aws-cli
    image: amazon/aws-cli:latest
"""
        }
    }
    
    environment {
        AWS_REGION = 'us-west-2'
        ECR_REPO = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        SERVICE_NAME = "${env.JOB_NAME.split('/')[0]}"
        BUILD_NUMBER = "${env.BUILD_NUMBER}"
        BRANCH_NAME = "${env.BRANCH_NAME}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Environment Setup') {
            steps {
                script {
                    if (BRANCH_NAME == 'main') {
                        env.ENVIRONMENT = 'prod'
                        env.REPLICAS = '3'
                    } else if (BRANCH_NAME == 'develop') {
                        env.ENVIRONMENT = 'uat'
                        env.REPLICAS = '2'
                    } else {
                        env.ENVIRONMENT = 'dev'
                        env.REPLICAS = '1'
                    }
                }
            }
        }
        
        stage('Build & Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        script {
                            sh """
                                docker build -t ${SERVICE_NAME}-test \
                                  --target test \
                                  --build-arg BUILDKIT_INLINE_CACHE=1 .
                                docker run --rm ${SERVICE_NAME}-test
                            """
                        }
                    }
                }
                
                stage('Security Scan') {
                    steps {
                        script {
                            sh """
                                # Trivy vulnerability scan
                                docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                                  aquasec/trivy image --exit-code 1 --severity HIGH,CRITICAL \
                                  ${SERVICE_NAME}-test
                            """
                        }
                    }
                }
            }
        }
        
        stage('Build Production Image') {
            steps {
                container('docker') {
                    script {
                        sh """
                            # AWS ECR Login
                            aws ecr get-login-password --region ${AWS_REGION} | \
                              docker login --username AWS --password-stdin ${ECR_REPO}
                            
                            # Build and tag image
                            docker build -t ${SERVICE_NAME}:${BUILD_NUMBER} \
                              --build-arg BUILDKIT_INLINE_CACHE=1 .
                            
                            docker tag ${SERVICE_NAME}:${BUILD_NUMBER} \
                              ${ECR_REPO}/${SERVICE_NAME}:${BUILD_NUMBER}
                            
                            docker tag ${SERVICE_NAME}:${BUILD_NUMBER} \
                              ${ECR_REPO}/${SERVICE_NAME}:${ENVIRONMENT}-latest
                            
                            # Push to ECR
                            docker push ${ECR_REPO}/${SERVICE_NAME}:${BUILD_NUMBER}
                            docker push ${ECR_REPO}/${SERVICE_NAME}:${ENVIRONMENT}-latest
                        """
                    }
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    if (ENVIRONMENT == 'prod') {
                        // Blue-Green deployment for production
                        deployBlueGreen()
                    } else {
                        // Rolling update for dev/uat
                        deployRolling()
                    }
                }
            }
        }
        
        stage('Integration Tests') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                }
            }
            steps {
                script {
                    sh """
                        # Run integration tests
                        helm test ${SERVICE_NAME}-${ENVIRONMENT} \
                          --namespace ${ENVIRONMENT}
                    """
                }
            }
        }
    }
    
    post {
        always {
            publishTestResults testResultsPattern: '**/test-results.xml'
            publishCoverage adapters: [
                jacocoAdapter('**/jacoco.xml')
            ]
        }
        failure {
            script {
                if (ENVIRONMENT == 'prod') {
                    // Rollback on production failure
                    rollbackDeployment()
                }
            }
        }
    }
}

def deployBlueGreen() {
    sh """
        # Blue-Green deployment logic
        kubectl patch deployment ${SERVICE_NAME}-green \
          --namespace prod \
          --patch='{"spec":{"template":{"spec":{"containers":[{"name":"${SERVICE_NAME}","image":"${ECR_REPO}/${SERVICE_NAME}:${BUILD_NUMBER}"}]}}}}'
        
        kubectl rollout status deployment/${SERVICE_NAME}-green --namespace prod
        
        # Switch traffic to green
        kubectl patch service ${SERVICE_NAME} \
          --namespace prod \
          --patch='{"spec":{"selector":{"version":"green"}}}'
    """
}

def deployRolling() {
    sh """
        helm upgrade --install ${SERVICE_NAME}-${ENVIRONMENT} \
          ./helm-charts/${SERVICE_NAME} \
          --namespace ${ENVIRONMENT} \
          --set image.tag=${BUILD_NUMBER} \
          --set replicaCount=${REPLICAS} \
          --set environment=${ENVIRONMENT} \
          --wait
    """
}

def rollbackDeployment() {
    sh """
        kubectl rollout undo deployment/${SERVICE_NAME}-green --namespace prod
        kubectl patch service ${SERVICE_NAME} \
          --namespace prod \
          --patch='{"spec":{"selector":{"version":"blue"}}}'
    """
}
```

### Jenkins Shared Library (`vars/microservicePipeline.groovy`)

```groovy
def call(Map config) {
    pipeline {
        agent any
        
        environment {
            SERVICE_NAME = config.serviceName
            AWS_REGION = config.awsRegion ?: 'us-west-2'
            ECR_REPO = "${config.awsAccountId}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        }
        
        stages {
            stage('Dynamic Pipeline') {
                steps {
                    script {
                        // Load service-specific configuration
                        def serviceConfig = readYaml file: "${config.serviceName}/pipeline-config.yml"
                        
                        // Execute custom stages based on service type
                        executeServicePipeline(serviceConfig)
                    }
                }
            }
        }
    }
}

def executeServicePipeline(config) {
    config.stages.each { stage ->
        stage(stage.name) {
            steps {
                script {
                    stage.steps.each { step ->
                        sh step
                    }
                }
            }
        }
    }
}
```

---

## 2. GitLab CI Configuration

### `.gitlab-ci.yml` Template

```yaml
variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  AWS_DEFAULT_REGION: us-west-2
  ECR_REGISTRY: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com

stages:
  - validate
  - build
  - test
  - security
  - deploy-dev
  - deploy-uat
  - deploy-prod

include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Container-Scanning.gitlab-ci.yml
  - template: Security/Dependency-Scanning.gitlab-ci.yml

.microservice-template: &microservice-template
  image: docker:20.10.7
  services:
    - docker:20.10.7-dind
  before_script:
    - apk add --no-cache aws-cli curl
    - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

validate:
  stage: validate
  script:
    - echo "Validating service configuration..."
    - |
      for service in $(find services -name "Dockerfile" -exec dirname {} \;); do
        echo "Validating $service"
        docker build --dry-run $service
      done
  rules:
    - changes:
      - services/**/*

build:
  <<: *microservice-template
  stage: build
  script:
    - |
      for service_path in $(find services -name "Dockerfile" -exec dirname {} \;); do
        service_name=$(basename $service_path)
        echo "Building $service_name..."
        
        docker build -t $service_name:$CI_COMMIT_SHA $service_path
        docker tag $service_name:$CI_COMMIT_SHA $ECR_REGISTRY/$service_name:$CI_COMMIT_SHA
        
        if [ "$CI_COMMIT_BRANCH" == "main" ]; then
          docker tag $service_name:$CI_COMMIT_SHA $ECR_REGISTRY/$service_name:prod-latest
        elif [ "$CI_COMMIT_BRANCH" == "develop" ]; then
          docker tag $service_name:$CI_COMMIT_SHA $ECR_REGISTRY/$service_name:uat-latest
        else
          docker tag $service_name:$CI_COMMIT_SHA $ECR_REGISTRY/$service_name:dev-latest
        fi
        
        docker push $ECR_REGISTRY/$service_name:$CI_COMMIT_SHA
        docker push $ECR_REGISTRY/$service_name:${CI_COMMIT_BRANCH:-dev}-latest
      done

test:
  stage: test
  script:
    - |
      for service_path in $(find services -name "package.json" -o -name "pom.xml" -o -name "requirements.txt" | xargs dirname | sort -u); do
        service_name=$(basename $service_path)
        echo "Testing $service_name..."
        
        cd $service_path
        # Run service-specific tests based on detected tech stack
        if [ -f "package.json" ]; then
          npm ci && npm test
        elif [ -f "pom.xml" ]; then
          mvn test
        elif [ -f "requirements.txt" ]; then
          python -m pytest
        fi
        cd -
      done
  coverage: '/Coverage: \d+\.\d+%/'

security-scan:
  stage: security
  image: aquasec/trivy:latest
  script:
    - |
      for service_name in $(find services -name "Dockerfile" -exec dirname {} \; | xargs basename); do
        echo "Scanning $service_name for vulnerabilities..."
        trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REGISTRY/$service_name:$CI_COMMIT_SHA
      done

.deploy-template: &deploy-template
  image: alpine/helm:latest
  before_script:
    - apk add --no-cache aws-cli kubectl
    - aws eks update-kubeconfig --region $AWS_DEFAULT_REGION --name $CLUSTER_NAME

deploy-dev:
  <<: *deploy-template
  stage: deploy-dev
  variables:
    ENVIRONMENT: dev
    CLUSTER_NAME: microservices-dev-cluster
  script:
    - |
      for service_path in $(find services -name "Dockerfile" -exec dirname {} \;); do
        service_name=$(basename $service_path)
        
        helm upgrade --install $service_name-dev \
          ./infrastructure/helm-charts/microservice \
          --namespace dev \
          --create-namespace \
          --set image.repository=$ECR_REGISTRY/$service_name \
          --set image.tag=$CI_COMMIT_SHA \
          --set environment=dev \
          --set replicaCount=1
      done
  only:
    - develop
    - feature/*

deploy-uat:
  <<: *deploy-template
  stage: deploy-uat
  variables:
    ENVIRONMENT: uat
    CLUSTER_NAME: microservices-uat-cluster
  script:
    - |
      for service_path in $(find services -name "Dockerfile" -exec dirname {} \;); do
        service_name=$(basename $service_path)
        
        helm upgrade --install $service_name-uat \
          ./infrastructure/helm-charts/microservice \
          --namespace uat \
          --create-namespace \
          --set image.repository=$ECR_REGISTRY/$service_name \
          --set image.tag=$CI_COMMIT_SHA \
          --set environment=uat \
          --set replicaCount=2
      done
  only:
    - develop

deploy-prod:
  <<: *deploy-template
  stage: deploy-prod
  variables:
    ENVIRONMENT: prod
    CLUSTER_NAME: microservices-prod-cluster
  script:
    - |
      for service_path in $(find services -name "Dockerfile" -exec dirname {} \;); do
        service_name=$(basename $service_path)
        
        # Blue-Green deployment
        helm upgrade --install $service_name-green \
          ./infrastructure/helm-charts/microservice \
          --namespace prod \
          --create-namespace \
          --set image.repository=$ECR_REGISTRY/$service_name \
          --set image.tag=$CI_COMMIT_SHA \
          --set environment=prod \
          --set version=green \
          --set replicaCount=3
        
        # Wait for deployment and run health checks
        kubectl wait --for=condition=available --timeout=300s deployment/$service_name-green -n prod
        
        # Switch traffic (this would be done via service mesh or ingress)
        kubectl patch service $service_name -n prod -p '{"spec":{"selector":{"version":"green"}}}'
      done
  when: manual
  only:
    - main
```

---

## 3. GitHub Actions Configuration

### `.github/workflows/microservices.yml`

```yaml
name: Microservices CI/CD

on:
  push:
    branches: [main, develop]
    paths: ['services/**']
  pull_request:
    branches: [main, develop]
    paths: ['services/**']

env:
  AWS_REGION: us-west-2
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-west-2.amazonaws.com

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.changes.outputs.services }}
      matrix: ${{ steps.changes.outputs.matrix }}
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Detect changed services
        id: changes
        run: |
          # Detect which services have changed
          CHANGED_SERVICES=$(git diff --name-only HEAD~1 HEAD | grep '^services/' | cut -d'/' -f2 | sort -u | jq -R -s -c 'split("\n")[:-1]')
          echo "services=$CHANGED_SERVICES" >> $GITHUB_OUTPUT
          
          # Create matrix for parallel processing
          MATRIX=$(echo $CHANGED_SERVICES | jq -c '{service: .}')
          echo "matrix=$MATRIX" >> $GITHUB_OUTPUT

  build-and-test:
    needs: detect-changes
    if: ${{ needs.detect-changes.outputs.services != '[]' }}
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Build and test
        run: |
          SERVICE_PATH="services/${{ matrix.service }}"
          
          # Build test image
          docker build \
            --target test \
            --cache-from $ECR_REGISTRY/${{ matrix.service }}:cache \
            --cache-to $ECR_REGISTRY/${{ matrix.service }}:cache,mode=max \
            -t ${{ matrix.service }}:test \
            $SERVICE_PATH
          
          # Run tests
          docker run --rm ${{ matrix.service }}:test
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ matrix.service }}:test
          format: sarif
          output: trivy-results.sarif
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: trivy-results.sarif
      
      - name: Build and push production image
        if: github.event_name == 'push'
        run: |
          SERVICE_PATH="services/${{ matrix.service }}"
          
          # Determine environment based on branch
          if [ "${{ github.ref }}" == "refs/heads/main" ]; then
            ENV="prod"
          elif [ "${{ github.ref }}" == "refs/heads/develop" ]; then
            ENV="uat"
          else
            ENV="dev"
          fi
          
          # Build and push
          docker build \
            --cache-from $ECR_REGISTRY/${{ matrix.service }}:cache \
            -t $ECR_REGISTRY/${{ matrix.service }}:${{ github.sha }} \
            -t $ECR_REGISTRY/${{ matrix.service }}:$ENV-latest \
            $SERVICE_PATH
          
          docker push $ECR_REGISTRY/${{ matrix.service }}:${{ github.sha }}
          docker push $ECR_REGISTRY/${{ matrix.service }}:$ENV-latest

  deploy:
    needs: [detect-changes, build-and-test]
    if: github.event_name == 'push' && needs.detect-changes.outputs.services != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Install kubectl
        uses: azure/setup-kubectl@v3
      
      - name: Install Helm
        uses: azure/setup-helm@v3
      
      - name: Deploy to environment
        run: |
          # Determine environment and cluster
          if [ "${{ github.ref }}" == "refs/heads/main" ]; then
            ENV="prod"
            CLUSTER="microservices-prod-cluster"
            REPLICAS=3
          elif [ "${{ github.ref }}" == "refs/heads/develop" ]; then
            ENV="uat"
            CLUSTER="microservices-uat-cluster"
            REPLICAS=2
          else
            ENV="dev"
            CLUSTER="microservices-dev-cluster"
            REPLICAS=1
          fi
          
          # Update kubeconfig
          aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER
          
          # Deploy using Helm
          helm upgrade --install ${{ matrix.service }}-$ENV \
            ./infrastructure/helm-charts/microservice \
            --namespace $ENV \
            --create-namespace \
            --set image.repository=$ECR_REGISTRY/${{ matrix.service }} \
            --set image.tag=${{ github.sha }} \
            --set environment=$ENV \
            --set replicaCount=$REPLICAS \
            --wait

  integration-tests:
    needs: [detect-changes, deploy]
    if: github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run integration tests
        run: |
          # Run comprehensive integration tests
          ./scripts/run-integration-tests.sh
```

---

## 4. Infrastructure as Code

### Terraform Configuration (`infrastructure/terraform/main.tf`)

```hcl
# EKS Clusters
module "eks_dev" {
  source = "./modules/eks"
  
  cluster_name = "microservices-dev-cluster"
  environment  = "dev"
  node_groups = {
    general = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
    }
  }
}

module "eks_uat" {
  source = "./modules/eks"
  
  cluster_name = "microservices-uat-cluster"
  environment  = "uat"
  node_groups = {
    general = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 5
      desired_size   = 3
    }
  }
}

module "eks_prod" {
  source = "./modules/eks"
  
  cluster_name = "microservices-prod-cluster"
  environment  = "prod"
  node_groups = {
    general = {
      instance_types = ["t3.xlarge"]
      min_size       = 3
      max_size       = 10
      desired_size   = 5
    }
  }
}

# ECR Repositories
resource "aws_ecr_repository" "microservices" {
  for_each = toset(var.microservice_names)
  
  name                 = each.key
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  lifecycle_policy {
    policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 10 production images"
          selection = {
            tagStatus     = "tagged"
            tagPrefixList = ["prod"]
            countType     = "imageCountMoreThan"
            countNumber   = 10
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
  }
}
```

### Helm Chart Template (`infrastructure/helm-charts/microservice/templates/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "microservice.fullname" . }}
  namespace: {{ .Values.environment }}
  labels:
    {{- include "microservice.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  strategy:
    type: {{ .Values.deploymentStrategy.type }}
    {{- if eq .Values.deploymentStrategy.type "RollingUpdate" }}
    rollingUpdate:
      maxUnavailable: {{ .Values.deploymentStrategy.maxUnavailable }}
      maxSurge: {{ .Values.deploymentStrategy.maxSurge }}
    {{- end }}
  selector:
    matchLabels:
      {{- include "microservice.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
      labels:
        {{- include "microservice.selectorLabels" . | nindent 8 }}
        version: {{ .Values.version | default "blue" }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "microservice.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.port }}
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /health/live
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          env:
            - name: ENVIRONMENT
              value: {{ .Values.environment }}
            - name: SERVICE_NAME
              value: {{ include "microservice.fullname" . }}
          envFrom:
            - configMapRef:
                name: {{ include "microservice.fullname" . }}-config
            - secretRef:
                name: {{ include "microservice.fullname" . }}-secrets
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

---

## 5. Security and DevSecOps Integration

### Security Pipeline Configuration

```yaml
# security-pipeline.yml
security_checks:
  sast:
    tools:
      - sonarqube
      - checkmarx
      - semgrep
  
  dependency_scan:
    tools:
      - snyk
      - dependabot
      - owasp-dependency-check
  
  container_scan:
    tools:
      - trivy
      - clair
      - anchore
  
  infrastructure_scan:
    tools:
      - checkov
      - tfsec
      - bridgecrew

quality_gates:
  security_score: 8.0
  vulnerability_threshold: "HIGH"
  code_coverage: 80%
  technical_debt: "A"
```

### Monitoring and Observability

```yaml
# monitoring-stack.yml
monitoring:
  prometheus:
    enabled: true
    retention: "30d"
  
  grafana:
    enabled: true
    dashboards:
      - microservices-overview
      - application-performance
      - infrastructure-metrics
  
  jaeger:
    enabled: true
    storage: elasticsearch
  
  elk_stack:
    elasticsearch:
      replicas: 3
    kibana:
      enabled: true
    logstash:
      enabled: true

alerts:
  - name: HighCPUUsage
    condition: cpu > 80%
    duration: 5m
  - name: HighMemoryUsage
    condition: memory > 85%
    duration: 5m
  - name: DeploymentFailure
    condition: deployment_status == "failed"
```

---

## 6. Dynamic Pipeline Configuration

### Service Configuration Template (`pipeline-config.yml`)

```yaml
# Per-service configuration
service:
  name: user-service
  type: web-api
  language: java
  framework: spring-boot
  
build:
  dockerfile: Dockerfile
  context: .
  cache: true
  multi_stage: true
  
test:
  unit_tests:
    command: mvn test
    coverage_threshold: 80
  integration_tests:
    command: mvn integration-test
    dependencies:
      - postgres
      - redis
  
security:
  sast_scan: true
  dependency_scan: true
  container_scan: true
  
deployment:
  strategy: rolling-update
  health_check:
    path: /health
    initial_delay: 30
    period: 10
  resources:
    cpu: 500m
    memory: 1Gi
    cpu_limit: 1000m
    memory_limit: 2Gi
  
environments:
  dev:
    replicas: 1
    auto_deploy: true
  uat:
    replicas: 2
    auto_deploy: false
    approval_required: true
  prod:
    replicas: 3
    auto_deploy: false
    approval_required: true
    deployment_strategy: blue-green
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. Set up repository structure
2. Configure Jenkins/GitLab/GitHub Actions
3. Create ECR repositories
4. Set up basic EKS clusters

### Phase 2: Pipeline Development (Weeks 3-4)
1. Implement basic CI/CD pipelines
2. Create Helm charts
3. Set up security scanning
4. Configure monitoring

### Phase 3: Advanced Features (Weeks 5-6)
1. Implement blue-green deployments
2. Add comprehensive testing
3. Set up observability stack
4. Configure alerting

### Phase 4: Optimization (Weeks 7-8)
1. Performance tuning
2. Cost optimization
3. Security hardening
4. Documentation and training

---

## Best Practices

### Code Quality
- Mandatory code reviews for all changes
- Automated code formatting and linting
- SonarQube integration for code quality metrics
- Branch protection rules requiring CI/CD checks

### Security Best Practices
- Least privilege IAM policies
- Secrets management using AWS Secrets Manager
- Network segmentation with security groups
- Regular security scanning and updates
- Multi-factor authentication for production deployments

### Performance Optimization
- Container image optimization and layering
- Resource limits and requests properly configured
- Horizontal pod autoscaling based on metrics
- Database connection pooling and caching strategies

### Disaster Recovery
- Multi-AZ deployments for high availability
- Automated backups and restore procedures
- Cross-region replication for critical services
- Regular disaster recovery testing

---

## Advanced Configurations

### Multi-Environment GitOps with ArgoCD

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: microservices-platform
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/microservices-platform
    targetRevision: HEAD
    path: infrastructure/k8s-manifests
    directory:
      recurse: true
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Service Mesh Integration (Istio)

```yaml
# istio-gateway.yaml
apiVersion: networking.istio.io/v1alpha3
kind: Gateway
metadata:
  name: microservices-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - api.yourdomain.com
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: tls-secret
    hosts:
    - api.yourdomain.com

---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: microservices-routes
spec:
  hosts:
  - api.yourdomain.com
  gateways:
  - microservices-gateway
  http:
  - match:
    - uri:
        prefix: /api/v1/users
    route:
    - destination:
        host: user-service
        port:
          number: 80
      weight: 90
    - destination:
        host: user-service-canary
        port:
          number: 80
      weight: 10
  - match:
    - uri:
        prefix: /api/v1/orders
    route:
    - destination:
        host: order-service
        port:
          number: 80
```

### Canary Deployment with Flagger

```yaml
# flagger-canary.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: user-service
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  progressDeadlineSeconds: 60
  service:
    port: 80
    targetPort: 8080
    gateways:
    - microservices-gateway
    hosts:
    - api.yourdomain.com
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
    webhooks:
    - name: acceptance-test
      type: pre-rollout
      url: http://flagger-loadtester.test/
      timeout: 30s
      metadata:
        type: bash
        cmd: "curl -sd 'test' http://user-service-canary/api/v1/health"
    - name: load-test
      url: http://flagger-loadtester.test/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://user-service-canary.production:80/api/v1/health"
```

---

## Monitoring and Alerting Configuration

### Prometheus Configuration

```yaml
# prometheus-config.yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "microservices_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
    - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
    - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
      action: keep
      regex: default;kubernetes;https

  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
    - role: node
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
    - action: labelmap
      regex: __meta_kubernetes_node_label_(.+)

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
    - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $1:$2
      target_label: __address__
```

### Alert Rules

```yaml
# microservices_rules.yml
groups:
- name: microservices.rules
  rules:
  - alert: ServiceDown
    expr: up == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.instance }} is down"
      description: "{{ $labels.instance }} has been down for more than 5 minutes."

  - alert: HighCPUUsage
    expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage detected"
      description: "CPU usage is above 80% for {{ $labels.instance }}"

  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage detected"
      description: "Memory usage is above 85% for {{ $labels.instance }}"

  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pod is crash looping"
      description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is crash looping"

  - alert: DeploymentReplicasMismatch
    expr: kube_deployment_spec_replicas != kube_deployment_status_replicas_available
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Deployment replicas mismatch"
      description: "Deployment {{ $labels.deployment }} replicas mismatch for more than 10 minutes"
```

---

## Cost Optimization Strategies

### Resource Right-Sizing

```yaml
# resource-optimization.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: microservices-quota
  namespace: production
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "4"

---
apiVersion: policy/v1beta1
kind: PodDisruptionBudget
metadata:
  name: microservices-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: microservice

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: microservice-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: microservice
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
```

### Cluster Autoscaling

```yaml
# cluster-autoscaler.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.21.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/microservices-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
        env:
        - name: AWS_REGION
          value: us-west-2
```

---

## Testing Strategy

### End-to-End Testing Pipeline

```yaml
# e2e-tests.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: e2e-test-config
data:
  test-suite.js: |
    const { test, expect } = require('@playwright/test');
    
    test.describe('Microservices E2E Tests', () => {
      test('User registration flow', async ({ page }) => {
        await page.goto('https://api.yourdomain.com');
        
        // Test user service
        const userResponse = await page.request.post('/api/v1/users', {
          data: {
            name: 'Test User',
            email: 'test@example.com'
          }
        });
        expect(userResponse.ok()).toBeTruthy();
        
        // Test order service integration
        const orderResponse = await page.request.post('/api/v1/orders', {
          data: {
            userId: 1,
            items: [{ id: 1, quantity: 2 }]
          }
        });
        expect(orderResponse.ok()).toBeTruthy();
      });
      
      test('Service health checks', async ({ request }) => {
        const services = [
          'user-service',
          'order-service',
          'payment-service',
          'inventory-service'
        ];
        
        for (const service of services) {
          const response = await request.get(`/api/v1/${service}/health`);
          expect(response.status()).toBe(200);
        }
      });
      
      test('Load balancing and failover', async ({ request }) => {
        const responses = [];
        
        // Make multiple requests to test load balancing
        for (let i = 0; i < 10; i++) {
          const response = await request.get('/api/v1/users/health');
          responses.push(response.headers()['x-instance-id']);
        }
        
        // Verify requests hit multiple instances
        const uniqueInstances = [...new Set(responses)];
        expect(uniqueInstances.length).toBeGreaterThan(1);
      });
    });

---
apiVersion: batch/v1
kind: Job
metadata:
  name: e2e-tests
spec:
  template:
    spec:
      containers:
      - name: playwright-tests
        image: mcr.microsoft.com/playwright:latest
        command: ["npx", "playwright", "test"]
        volumeMounts:
        - name: test-config
          mountPath: /tests
        env:
        - name: BASE_URL
          value: "https://api.yourdomain.com"
      volumes:
      - name: test-config
        configMap:
          name: e2e-test-config
      restartPolicy: Never
  backoffLimit: 3
```

---

## Documentation and Training

### API Documentation Generation

```yaml
# swagger-ui.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: swagger-ui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: swagger-ui
  template:
    metadata:
      labels:
        app: swagger-ui
    spec:
      containers:
      - name: swagger-ui
        image: swaggerapi/swagger-ui:latest
        ports:
        - containerPort: 8080
        env:
        - name: URLS
          value: |
            [
              {
                "url": "https://api.yourdomain.com/api/v1/users/swagger.json",
                "name": "User Service"
              },
              {
                "url": "https://api.yourdomain.com/api/v1/orders/swagger.json",
                "name": "Order Service"
              }
            ]
```

### Runbook Templates

```markdown
# Service Runbook Template

## Service Overview
- **Name**: {SERVICE_NAME}
- **Purpose**: {SERVICE_DESCRIPTION}
- **Team**: {TEAM_NAME}
- **Repository**: {REPO_URL}

## Architecture
- **Technology Stack**: {TECH_STACK}
- **Dependencies**: {DEPENDENCIES}
- **Database**: {DATABASE_INFO}

## Operational Procedures

### Deployment
```bash
# Production deployment
kubectl apply -f k8s/production/
helm upgrade --install {SERVICE_NAME} ./helm-charts/{SERVICE_NAME}
```

### Monitoring
- **Health Check**: `curl https://api.yourdomain.com/api/v1/{SERVICE_NAME}/health`
- **Metrics**: Grafana dashboard link
- **Logs**: `kubectl logs -f deployment/{SERVICE_NAME} -n production`

### Troubleshooting
1. **High CPU Usage**: Check for infinite loops or inefficient queries
2. **Memory Leaks**: Monitor heap dumps and garbage collection
3. **Database Issues**: Check connection pool and query performance

### Rollback Procedures
```bash
# Rollback to previous version
kubectl rollout undo deployment/{SERVICE_NAME} -n production

# Rollback using Helm
helm rollback {SERVICE_NAME} -n production
```
```

---

## Conclusion

This comprehensive CI/CD pipeline architecture provides:

1. **Multi-platform integration** with Jenkins, GitLab CI, and GitHub Actions
2. **Robust security** with DevSecOps practices integrated throughout
3. **Scalable infrastructure** using AWS EKS and ECR
4. **Dynamic deployment strategies** including blue-green and canary deployments
5. **Comprehensive monitoring** and alerting capabilities
6. **Cost optimization** through right-sizing and autoscaling
7. **Automated testing** at multiple levels
8. **Infrastructure as Code** for reproducible environments

The modular design allows you to implement components incrementally while maintaining flexibility for future enhancements. Each microservice can be configured independently while benefiting from shared pipeline templates and infrastructure components.