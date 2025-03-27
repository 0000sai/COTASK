
provider "azurerm" {
  features {}
}

terraform {
  backend "azurerm" {
    resource_group_name  = "costoptimizationsas"
    storage_account_name = "costoptimizationsas"
    container_name       = "tfstate"
    key                  = "gitlab.tfstate"
  }
}