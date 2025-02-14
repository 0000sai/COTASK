# DevSecOps Pipeline Tutorial

![Day 02 (1)](https://github.com/user-attachments/assets/ae4bd8bb-3988-45c9-887d-cb14531c40e5)


### Start the Instances
1. Start all the instances on **AWS** and **Azure**.
2. Copy the IP addresses of the instances to **Route53**.
3. Clone the production code and switch to the development branch.

### Recap of Previous Session
In the previous session, we created a Docker image and analyzed it with **Trivy** for any security vulnerabilities.

### Today's Session
We will complete the next stages by pushing the Docker image to:
- **Azure Container Registry (ACR)**
- **Docker Hub (Private)**

### Steps for Azure Container Registry
1. Copy the code to production.
2. Go to **Azure** and create a container registry:
   - **Container Registry** > **Create**
   - Resource Group: `devSecOps`
   - Registry Name: `devsecopsacr`
   - Region: `East US`
   - Click **Review and Create**.
3. After creating the registry:
   - Go to the resources > **Access Keys**.
   - Enable the **Admin user** checkbox.
4. In the pipeline:
   - Edit the pipeline > **Variables** > **Add**:
     - Name: `acrpassword`
     - Value: Copy and paste the password (keep it secret).
   - Save the changes.

### Steps for Docker Hub
1. Go to **Project Settings** > **Service Connections** > **New** > **Docker Registry** > **Docker Hub**.
2. Enter the following details:
   - Docker ID: `kiran2361993`
   - Password or Token.
   - Service Connection Name: `devops-dockerhub-connection`.
   - Grant access and click **Save**.
3. Push the changes to Git and monitor the pipeline.

## Step 09: Fixing Errors and Deploying to Azure Container Instance (ACI)
### Java Version Change
- Show the error and update the Java version in the Dockerfile from **11** to **17**.

### Deploy to Azure Container Instance
1. Copy the code.
2. Deploy it to **Azure Container Instance (ACI)**:
   - ACI automatically creates an instance without manual provisioning.

### Creating Environments on AWS
1. Create two different Ubuntu servers on **AWS**:
   - One for **Staging** and another for **Production**.
2. Deploy two **t2.medium** instances with the following settings:
   - **Tag**: `Name: Staging` (Rename one instance to `Production` after creation).
   - **Advanced Details** > **User Data**:
     ```bash
     #!bin/bash
     apt update
     apt install -y openjdk-17-jdk
     ```
   - Launch the instances.
3. Once deployed, rename one instance to `Production`.

### Route53 Records
1. Create two records in **Route53**:
   - Record Name: `staging` and its IP address.
   - Record Name: `prod` and its IP address.
2. Create the records.

### Configuring Environments in the Pipeline
1. Go to **Pipeline** > **Edit** > **Environment** > **Create**:
   - **Staging**:
     - Select **Virtual Machines** > **Linux**.
     - Log in to the staging EC2 instance and verify Java version using:
       ```bash
       java -version
       ```
     - Copy the register script from Azure and run it in the instance.
   - **Production**:
     - Select **Virtual Machines** > **Linux**.
     - Log in to the production EC2 instance and verify Java version.
     - Copy the register script from Azure and run it in the instance.

2. Verify the following:
   - **ACI**, **Docker Hub**, and **ACR** for images.
   - Go to **Azure** > **Container Instances** > Check the **FQDN** and access it on port **8080**.

## Step 10: Adding Deployment Code and Running DAST Testing
1. Add deployment code and run **ZAP** for security testing.
2. Go to the pipeline:
   - **Edit** > **Variables** > Add Docker login variables.
3. Push the changes to Git.

### Handling Pipeline Issues
- If you see an orange status in the pipeline, it’s not an issue.
- Explanation: If a JAR file is already found, the process will stop; otherwise, it will continue.

### Break Time
Let the pipeline complete. After the break:
1. Access the application via **ACI FQDN** and `http://staging.cloudvishwakarma.in:8080`.
2. Run **DAST** testing and show the results.

### Fixing Maven Build Configuration
- Since the pipeline was configured for **Dev**, update it for **Prod** by commenting out the previous condition:
  ```yaml
  # condition: or(eq(variables.isProd, true), eq(variables.isDev, true))
  ```
- Push the changes to the `production` branch instead of `development`.
- Monitor the pipeline; most tasks should be skipped.

## Next Session Preview
In the next session, we will cover:
1. **Infrastructure Pipeline** using **Terraform**.
2. **SAST** directly on the code.
3. **DAST** after deploying the application.

