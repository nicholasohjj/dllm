resource "aws_dynamodb_table" "MachineStatusTable" {
  name         = var.MachineStatusTable
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "machineID"
  attribute {
    name = "machineID"
    type = "S"
  }

  tags = {
    Name        = "MachineStatusTable"
    Environment = "production"
    Project     = "DLLM"
    Owner       = "Nicholas"
  }
}

resource "aws_dynamodb_table" "VibrationData" {
  name         = var.VibrationData
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "timestamp_value"
  range_key    = "machine_id"

  attribute {
    name = "timestamp_value"
    type = "S"
  }

  attribute {
    name = "machine_id"
    type = "S"
  }

  tags = {
    Name        = "VibrationData"
    Environment = "production"
    Project     = "DLLM"
    Owner       = "Nicholas"
  }
}

resource "aws_dynamodb_table" "WebSocketConnections" {
  name         = "WebSocketConnections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "connectionId"

  ttl {
    attribute_name = "ExpirationTime"
    enabled        = "true"
  }

  attribute {
    name = "connectionId"
    type = "S"
  }

  tags = {
    Name        = "WebSocketConnections"
    Environment = "production"
    Project     = "DLLM"
    Owner       = "Nicholas"
  }
}

resource "aws_dynamodb_table" "CameraImageJSON" {
  name         = var.CameraImageJSON
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "timestamp_value"

  attribute {
    name = "timestamp_value"
    type = "S"
  }

  tags = {
    Name        = "CameraImageJSON"
    Environment = "production"
    Project     = "DLLM"
    Owner       = "Nicholas"
  }
  
}

# New table for processed camera detections (from YOLOv7 + classification)
resource "aws_dynamodb_table" "CameraDetectionData" {
  name         = "CameraDetectionData"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "machine_id"
  range_key    = "timestamp"

  attribute {
    name = "machine_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "CameraDetectionData"
    Environment = "production"
    Project     = "DLLM"
    Owner       = "Nicholas"
  }
}