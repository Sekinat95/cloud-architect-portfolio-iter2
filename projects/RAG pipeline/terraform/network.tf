resource "google_compute_network" "myvpc" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false
  depends_on = [google_project_service.compute]
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "${var.project_id}-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.myvpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.myvpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]

  depends_on = [google_project_service.servicenetworking]
}