# Day 27 HashicorpVault AWSIntegration
Below is a structured GitHub repository content outline and README for the integration of HashiCorp Vault with Ansible, based on the provided instructions:

---

### Repository Structure

```plaintext
HashiCorp-Vault-Ansible-Integration/
├── README.md
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
├── vault/
│   ├── config.hcl
│   ├── config-kms.hcl
│   ├── init.file
├── ansible/
│   ├── playbook.yml
│   ├── vault_secret_retrieve.yml
├── docs/
│   ├── installation_steps.md
│   ├── troubleshooting.md
└── scripts/
    ├── setup_docker.sh
    ├── setup_ssl.sh
```

---

### **README.md**

```markdown
# HashiCorp Vault Integration with Ansible

This repository demonstrates the integration of **HashiCorp Vault** with **Ansible** for managing secrets in real-world scenarios, specifically focusing on environments where servers need to retrieve sensitive information after unexpected reboots. The solution leverages Terraform for provisioning, AWS KMS for auto-unsealing, and Docker to host Vault.

---

## **Use Case**

A Java application is running on a server. When the server reboots due to a disaster or maintenance:
- The application must securely retrieve sensitive information (e.g., credentials) from a centralized Key Management System (KMS).
- HashiCorp Vault is used for this purpose, ensuring compatibility with both on-premises and cloud environments.

### Why not Ansible Vault?
- **Ansible Vault** is ideal for encrypting sensitive data like API keys or database credentials within playbooks. However, it cannot autonomously retrieve secrets from another server when triggered by events like server reboots.
- **HashiCorp Vault**, combined with AWS KMS, provides auto-unsealing capabilities and centralized secret management.

---

## **Solution Overview**

1. **HashiCorp Vault Setup**:
   - Install Vault on a t2.medium instance.
   - Configure Vault with auto-unsealing using AWS KMS.
   - Store Vault initialization keys securely in S3.

2. **Terraform Configuration**:
   - Provisions Vault server.
   - Sets up IAM roles and S3 buckets for storing Vault keys.
   - Configures KMS for encryption and auto-unsealing.

3. **Ansible Integration**:
   - Demonstrates how to retrieve secrets stored in Vault using Ansible playbooks.

---

## **Setup Instructions**

### 1. Prerequisites
- AWS Account with administrative access.
- A t2.medium EC2 instance with Docker installed.
- Terraform installed locally.
- Ansible installed locally.

### 2. Vault Installation
Follow the steps in `docs/installation_steps.md` to:
1. Start an EC2 instance.
2. Install Docker and SSL.
3. Configure Vault.

### 3. Configuring AWS KMS
- Navigate to AWS Management Console > KMS.
- Create a symmetric key with "Encrypt and Decrypt" permissions.
- Add the IAM role of the EC2 instance to allow access.

### 4. Configuring Vault with KMS
1. Replace the Vault config file:
   ```bash
   sudo nano /etc/vault/config.hcl
   ```
   Copy and paste the contents from `vault/config-kms.hcl`.
2. Ensure S3 bucket details are correctly updated.
3. Initialize Vault:
   ```bash
   vault operator init | tee -a /etc/vault/init.file
   ```

### 5. Terraform Setup
- Navigate to the `terraform/` directory.
- Update variables in `variables.tf` for your environment.
- Apply the configuration:
  ```bash
  terraform apply
  ```

### 6. Reboot Handling
- After rebooting the server:
  ```bash
  terraform apply
  ```
- Verify that Vault is accessible and unsealed automatically.

---

## **Ansible Playbook Example**

Retrieve secrets from Vault after server reboot:
```yaml
---
- name: Retrieve secrets from HashiCorp Vault
  hosts: localhost
  tasks:
    - name: Fetch secret from Vault
      uri:
        url: "http://<vault-server-ip>:8200/v1/secret/data/my-secret"
        method: GET
        headers:
          X-Vault-Token: "{{ vault_token }}"
      register: secret_response

    - name: Debug retrieved secret
      debug:
        msg: "{{ secret_response.json }}"
```

---

## **Troubleshooting**
- Refer to `docs/troubleshooting.md` for common issues, such as:
  - Vault not unsealing after reboot.
  - KMS misconfiguration.
  - Terraform or Ansible errors.

---

## **License**
This repository is licensed under the MIT License. See `LICENSE` for details.
```

---

### Additional Notes
1. **Scripts**:
   - `setup_docker.sh`: Automates Docker installation.
   - `setup_ssl.sh`: Configures SSL for Vault.

2. **Documentation**:
   - `docs/installation_steps.md`: Step-by-step guide for setting up Vault and related components.
   - `docs/troubleshooting.md`: Solutions for potential issues during setup and execution.
