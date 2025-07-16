# Compute Instance
resource "google_compute_instance" "app_server" {
  count        = var.instance_count
  name         = "app-server-${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 20
    }
  }

  network_interface {
    network    = google_compute_network.vpc.name
    subnetwork = google_compute_subnetwork.subnet.name

    access_config {
      // Ephemeral public IP
    }
  }

  metadata = {
    ssh-keys = "debian:${file(var.ssh_public_key_path)}"
  }

  tags = ["app-server", "http-server", "https-server"]
}

# Firewall Rules
resource "google_compute_firewall" "allow_http" {
  name    = "allow-http"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server", "https-server"]
}
