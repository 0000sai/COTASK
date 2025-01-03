# Terraform AWS ECS Deployment

## Giới thiệu

Dự án này sử dụng Terraform để tạo các resource cơ bản trên AWS bao gồm VPC, Subnet, Security Group, Application Load Balancer (ALB), Target Groups, và ECS Clusters. Ngoài ra, dự án cũng tích hợp Jenkins để thực hiện các job tự động hóa như build, deploy, switch traffic, và clear resources.

![Terraform AWS ECS Deployment](https://github.com/VIET-TU/images/blob/main/Terraform%20AWS%20ECS%20Deployment.drawio.png)

## Các thành phần chính

### Terraform

- **VPC**: Tạo một VPC mới.
- **Subnets**: Tạo các subnets cần thiết cho VPC.
- **Security Groups**: Tạo các security groups để bảo vệ các resource.
- **ALB (Application Load Balancer)**: Tạo một ALB để phân phối traffic.
- **Target Groups**: Tạo hai target groups để triển khai chiến lược blue/green deployment.
- **ECS Clusters**: Tạo hai ECS clusters để chạy các dịch vụ.

### Jenkins

- **Job Build**: Nhận tham số là `version tag`, build source code và push Docker image lên ECR với tag là `<version>`.
- **Job Deploy**: Nhận tham số là `version`, `ECS Cluster name`. Nhiệm vụ là triển khai Docker image lên ECS Cluster.
- **Job Switch Traffic**: Switch traffic trên ALB giữa hai target groups (blue/green).
- **Job Clear Resource**: Nhận tham số là `Cluster name`, nhiệm vụ là stop hết task trên cluster hoặc chỉnh service capacity về 0.
