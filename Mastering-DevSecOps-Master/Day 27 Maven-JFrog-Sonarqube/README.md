
![Untitled design](https://github.com/user-attachments/assets/dfaf3392-9cfd-43b2-86c1-e1bdd956b3ee)


# Maven-Jfrog Integration

This repository showcases the integration of **Maven**, **JFrog**, and **SonarQube** to build, manage, and analyze a Java-based Spring Boot application. Below are the detailed steps to set up and deploy a sample application.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Setup and Installation](#setup-and-installation)
4. [Maven Lifecycle](#maven-lifecycle)
5. [Integrating with JFrog](#integrating-with-jfrog)
6. [Pushing Artifacts to JFrog](#pushing-artifacts-to-jfrog)
7. [Version Management](#version-management)
8. [License](#license)

---

## Introduction

This project demonstrates:
- Building a Spring Boot application using Maven.
- Managing dependencies with `pom.xml`.
- Storing and managing build artifacts using JFrog Artifactory.
- Incremental versioning of artifacts.
- Deployment to a private repository for reuse in other projects.

**Note:** While this project highlights all major steps, application-specific code and configurations will typically be managed by your development team.

---

## Prerequisites

1. **AWS EC2 Instance**:
   - Instance type: `T2.large`
   - Storage: `20 GB`
   - OS: Ubuntu 20.04+
2. **Tools**:
   - **Maven**: Installed and configured.
   - **OpenJDK**: Version 17 or higher.
   - **JFrog Artifactory**: Installed and licensed.
   - **Git**: Configured with SSH authentication.
3. **Networking**:
   - Configure DNS using Route 53 (if applicable).

---

## Setup and Installation

### 1. Create EC2 Instance
Launch an EC2 instance and install required tools:

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk maven git jq net-tools
```

### 2. Clone and Build the Application

```bash
git clone https://github.com/spring-projects/spring-petclinic.git
cd spring-petclinic
mvn clean package
```

### 3. Push Code to Azure DevOps
1. Initialize a new Git repository if needed:
   ```bash
   rm -rf .git
   git init
   ```
2. Set up SSH authentication:
   - Generate an SSH key: `ssh-keygen`
   - Add the public key to Azure DevOps under **User Settings > SSH Public Keys**.
   - Clone the repository using the SSH link.

3. Push code:
   ```bash
   git add .
   git commit -m "Initial commit"
   git remote add origin <ssh-link>
   git push -u origin master
   ```

---

## Maven Lifecycle

### Maven Commands Overview

1. **Validate**:
   ```bash
   mvn validate
   ```
   Ensures the `pom.xml` is valid.

2. **Compile**:
   ```bash
   mvn compile
   ```
   Compiles Java files into `.class` files.

3. **Package**:
   ```bash
   mvn package
   ```
   Packages the compiled code into `.jar` or `.war` artifacts.

4. **Run Application**:
   ```bash
   java -jar target/*.jar
   ```

5. **Clean**:
   ```bash
   mvn clean
   ```
   Deletes previous build artifacts.

---

## Integrating with JFrog

1. **Install JFrog**:
   ```bash
   wget -O jfrog-deb-installer.tar.gz "https://releases.jfrog.io/artifactory/jfrog-prox/org/artifactory/pro/deb/jfrog-platform-trial-prox/[RELEASE]/jfrog-platform-trial-prox-[RELEASE]-deb.tar.gz"
   tar -xvzf jfrog-deb-installer.tar.gz
   cd jfrog-platform-trial-pro*
   sudo ./install.sh
   sudo systemctl start artifactory.service
   ```

2. **Configure JFrog**:
   - Access JFrog via `http://<instance-ip>:8082`.
   - Apply the trial license.
   - Create a Maven repository (`libs-release-local`).

3. **Update Maven Configuration**:
   Add the following in your `settings.xml`:

   ```xml
   <servers>
      <server>
         <id>central</id>
         <username>YOUR_USERNAME</username>
         <password>YOUR_PASSWORD</password>
      </server>
   </servers>
   ```

---

## Pushing Artifacts to JFrog

1. **Add Distribution Management to `pom.xml`**:

   ```xml
   <distributionManagement>
      <repository>
         <id>central</id>
         <name>libs-release</name>
         <url>http://<jfrog-instance>:8081/artifactory/libs-release-local</url>
      </repository>
      <snapshotRepository>
         <id>snapshots</id>
         <name>libs-snapshot</name>
         <url>http://<jfrog-instance>:8081/artifactory/libs-snapshot-local</url>
      </snapshotRepository>
   </distributionManagement>
   ```

2. **Deploy Artifact**:
   ```bash
   mvn clean install deploy
   ```

3. Verify the artifact in JFrog's repository.

---

## Version Management

Update versions dynamically using Maven's version plugin:

```bash
mvn versions:set -DnewVersion=1.0.0
mvn clean install deploy
```

Repeat for subsequent versions:
```bash
mvn versions:set -DnewVersion=1.0.1
```

---

## License

This project is licensed under the [MIT License](LICENSE).
