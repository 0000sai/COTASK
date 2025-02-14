#distinct takes a list and returns a new list with any duplicate elements removed.
#toset takes a list will remove any duplicate elements and discard the ordering of the elements.
locals {
  new_public_subnet_cidrs  = distinct(var.public_subnet_cidrs)
  new_private_subnet_cidrs = distinct(var.private_subnet_cidrs)
  new_environment          = lower(var.environment)
  projid                   = format("%s-%s", lower(var.vpc_name), lower(var.projid))
}