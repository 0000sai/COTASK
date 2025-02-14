# Managing Infrastructure Pipelines - Session Notes

![Azure Devops](https://github.com/user-attachments/assets/a9b32e1f-1bea-48b9-ac03-5e75daa04d4a)

From today’s session, we discussed how to effectively manage Infrastructure Pipelines, focusing on real-world scenarios like sharing agents across organizations, password version control, and handling secure files.

### Key Concepts:

**Example Scenario:**
- We have an Agent in one organization and need to share the same Agent with another organization.
- Managing passwords in version control securely.
- Handling sensitive security files.

---

### Start Agent - Example 01:
- Create a Project in the PROD organization and demonstrate how to use the existing Agent Pool.

**Task:**
1. Open the VSCode file and explain the "AZURE-PIPELINE" code. Add the `.pem` file.
2. Edit `packer-vars.json`.
   - The file wasn’t present earlier because it’s a secure file. If you check `.gitignore`, you’ll notice sensitive files are ignored.
   - Create the necessary secure files and add values later.

3. Update the following files:
   - `route53`
   - Certificate name under `prod-auto.tfvars`
   - Bucket name in `main.tf` and `prod-auto.tfvars`
   - VPC, IGW, and Subnet names.

**CIDR Ranges:**
- VPC CIDR: `10.37.0.0/16`
- Public Subnet CIDRs:
  - `10.37.1.0/24`
  - `10.37.2.0/24`
  - `10.37.3.0/24`
- Private Subnet CIDR: `10.37.20.0/24`
- Remove the private subnet name.
- Remove the AMI as it’s being taken from the Datasource.

4. Go to the Terraform code and highlight where the access key and secret key are specified. Now, these keys need to be referenced as variables:
   - Push the code first.
   - Navigate to Pipeline > Code > Edit > Variables.
     - **Name:** `aws_access_key` (Copy from IAM)
     - **Value:** `aws_secret_key` (Copy from IAM)

5. Go to the previous ADO Project > Service Connections > Azure Connections:
   - Options > Security > + Search and confirm.
   - This demonstrates that not only agents but also service connections can be shared across projects.

6. Configure the project:
   - **Library**
   - Create a Variable Group: `AWS_ACCESS_GROUP`
     - Add the access key and secret key.

7. Return to the Terraform code:
   - Copy-paste your `.pem` file.
   - Add access key and secret key in `access.auto.tfvars`.
   - Update `packer-vars.json`.
   - Apply the changes in `backend.json`.

8. Upload all four files as secure files under the pipeline.
9. Push the code to the repository.
   - Initially, everything was set to 'NO' except for `destroy` which was set to 'YES'.
   - Modify the code to set `destroy` to 'NO' and other parameters to 'YES'.
   - Run `git status` and push the changes to master.

10. Once done, change `Terraform Destroy` back to 'YES' and others to 'NO'. Push the changes.
11. Enable release pipelines:
    - Go to Org Settings > Pipelines > Settings > Disable the creation of classic release pipelines.
    - In Pipelines, you will see the Release option.

**Purpose:**
The reason for this hands-on demonstration is to prepare you for real-time environments. When you encounter these processes in a production setting, they should not feel overwhelming. These are simply release pipelines that you now understand.

---

### Next Session Preview:
- Understanding pipeline licensing.
- Exploring different types of Azure Boards and how agile delivery works.
- Hosted vs. Self-hosted Pipelines.
- Various types of integrations.

Stay tuned for more insights in the next session!

