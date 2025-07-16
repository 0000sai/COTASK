variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "subnet_cidr" {
  description = "CIDR for subnet"
  type        = string
  default     = "10.10.0.0/24"
}

variable "pod_cidr" {
  description = "CIDR for pods"
  type        = string
  default     = "10.20.0.0/16"
}

variable "service_cidr" {
  description = "CIDR for services"
  type        = string
  default     = "10.30.0.0/16"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "main-cluster"
}

variable "gke_num_nodes" {
  description = "Number of GKE nodes"
  type        = number
  default     = 2
}

variable "machine_type" {
  description = "Machine type for compute instances"
  type        = string
  default     = "n1-standard-1"
}

variable "instance_count" {
  description = "Number of compute instances"
  type        = number
  default     = 2
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
}
