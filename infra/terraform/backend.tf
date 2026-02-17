# Remote state backend — created by infra/bootstrap/.
# Run `make bootstrap-init && make bootstrap-apply` before first use.

terraform {
  backend "s3" {
    bucket         = "cloudcrew-terraform-state"
    key            = "cloudcrew/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "cloudcrew-terraform-locks"
    encrypt        = true
  }
}
