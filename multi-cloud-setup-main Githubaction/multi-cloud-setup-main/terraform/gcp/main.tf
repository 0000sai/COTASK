terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "environments/production/gcp/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "main-vpc"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "main-subnet"
  ip_cidr_range = var.subnet_cidr
  network       = google_compute_network.vpc.id
  region        = var.region

  secondary_ip_range {
    range_name    = "pod-range"
    ip_cidr_range = var.pod_cidr
  }

  secondary_ip_range {
    range_name    = "service-range"
    ip_cidr_range = var.service_cidr
  }
}
