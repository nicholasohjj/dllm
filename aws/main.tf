provider "aws" {
  region = var.aws_region
}

terraform {
  backend "s3" {
    bucket  = "terraform-bucket-dllm"     
    key     = "dllm-tf/terraform.tfstate"
    region  = "ap-southeast-1"            
    encrypt = true
  }
}