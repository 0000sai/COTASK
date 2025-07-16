# Docker Configuration

This directory contains Docker configurations for containerizing the application.

## Directory Structure

```
docker/
├── Dockerfile           # Main application Dockerfile
└── README.md           # This file
```

## Dockerfile Details

The Dockerfile is configured to:
- Use a secure base image
- Run the application on port 8443 (HTTPS)
- Follow security best practices
- Implement multi-stage builds for smaller image size

## Building the Image

```bash
# Build the image
docker build -t demo-app:latest .

# Build with specific platform
docker build --platform linux/amd64 -t demo-app:latest .
```

## Running Locally

```bash
# Run the container
docker run -d -p 8443:8443 demo-app:latest

# Run with environment variables
docker run -d \
  -p 8443:8443 \
  -e ENV_VAR1=value1 \
  -e ENV_VAR2=value2 \
  demo-app:latest
```

## Pushing to Container Registry

### AWS ECR
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag the image
docker tag demo-app:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/demo-app:latest

# Push the image
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/demo-app:latest
```

### GCP Artifact Registry
```bash
# Login to GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# Tag the image
docker tag demo-app:latest us-central1-docker.pkg.dev/your-project/demo-app:latest

# Push the image
docker push us-central1-docker.pkg.dev/your-project/demo-app:latest
```

## Security Best Practices

1. Use specific image versions instead of `latest`
2. Implement least privilege principle
3. Scan images for vulnerabilities
4. Keep base images updated
5. Use multi-stage builds
6. Never store secrets in images
