# Multi-Cloud Infrastructure Setup

This directory contains Terraform configurations for setting up infrastructure across AWS and GCP, including compute instances and Kubernetes clusters.

## Directory Structure

```
terraform/
├── bootstrap/          # State management setup
├── aws/               # AWS infrastructure
└── gcp/               # GCP infrastructure
```

## Prerequisites

1. Install required tools:
   ```bash
   # Install Terraform
   curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt-get update && sudo apt-get install terraform

   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # Install Google Cloud SDK
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   ```

2. Configure cloud provider credentials:
   ```bash
   # AWS credentials
   aws configure

   # GCP credentials
   gcloud auth application-default login
   ```

## Setup Instructions

### 1. Bootstrap State Management

First, set up the state management infrastructure:

```bash
cd bootstrap

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
aws_region = "us-west-2"
state_bucket_name = "your-terraform-state-bucket"
dynamodb_table_name = "terraform-state-lock"
EOF

# Initialize and apply
terraform init
terraform apply
```

### 2. AWS Infrastructure

Set up AWS infrastructure including VPC, EC2, and EKS:

```bash
cd ../aws

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
aws_region = "us-west-2"
vpc_cidr = "10.0.0.0/16"
ec2_instance_count = 2
ec2_instance_type = "t3.micro"
eks_cluster_name = "main-cluster"
eks_cluster_version = "1.27"
EOF

# Initialize and apply
terraform init
terraform apply
```

### 3. GCP Infrastructure

Set up GCP infrastructure including VPC, Compute Engine, and GKE:

```bash
cd ../gcp

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
project_id = "your-gcp-project-id"
region = "us-central1"
zone = "us-central1-a"
ssh_public_key_path = "~/.ssh/id_rsa.pub"
cluster_name = "main-cluster"
gke_num_nodes = 2
instance_count = 2
EOF

# Initialize and apply
terraform init
terraform apply
```

## Resource Management

### Viewing Resources
```bash
terraform show     # Show current state
terraform output  # Show outputs
```

### Making Changes
```bash
terraform plan    # Preview changes
terraform apply   # Apply changes
```

### Cleaning Up
```bash
terraform destroy # Delete all resources
```

## Important Notes

1. **State Management**:
   - State files are stored in S3 with encryption
   - State locking uses DynamoDB to prevent concurrent modifications
   - Each environment has its own state file

2. **Security**:
   - All compute instances are in private subnets
   - Security groups/firewall rules limit access
   - Kubernetes clusters use managed node groups

3. **Cost Management**:
   - Resources are configured for development by default
   - Adjust instance types and counts in terraform.tfvars
   - Remember to destroy unused resources

## Troubleshooting

1. **State Lock Issues**:
   ```bash
   terraform force-unlock [LOCK_ID]
   ```

2. **Authentication Issues**:
   - AWS: Check `~/.aws/credentials`
   - GCP: Run `gcloud auth application-default login`

3. **Resource Creation Failures**:
   - Check cloud provider quotas
   - Verify network connectivity
   - Review error messages in terraform output

## Best Practices

1. Always run `terraform plan` before `terraform apply`
2. Use workspaces for different environments
3. Tag all resources appropriately
4. Keep sensitive data in terraform.tfvars (git-ignored)
5. Regularly update provider versions
