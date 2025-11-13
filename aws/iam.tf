resource "aws_iam_role" "modifyMachineStatusRole" {
  name = "modifyMachineStatusRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
}

resource "aws_iam_role" "processDataRole" {
  name = "processDataRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
}

resource "aws_iam_policy" "process_data_policy" {
  name        = "processDataPolicy"
  description = "Policy to allow DynamoDB scan access for VibrationData table and update access for MachineStatusTable"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:Scan"
        ],
        "Resource" : "arn:aws:dynamodb:ap-southeast-1:149536472280:table/VibrationData"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:UpdateItem"
        ],
        "Resource" : "arn:aws:dynamodb:ap-southeast-1:149536472280:table/MachineStatusTable"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "process_data_role_attach" {
  role       = aws_iam_role.processDataRole.name
  policy_arn = aws_iam_policy.process_data_policy.arn
}

resource "aws_iam_role" "modifyWebConnectionsRole" {
  name = "modifyWebConnectionsRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
}

resource "aws_iam_role" "archiveOldDataRole" {
  name = "archiveOldDataRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
}

resource "aws_iam_policy" "archive_data_policy" {
  name        = "archiveDataPolicy"
  description = "Policy to allow Lambda function to archive data to S3"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:PutObject"
        ],
        "Resource": "arn:aws:s3:::archived-data-dllm/archive/*"  # Ensure bucket name and path are correct here
      },
      {
        "Effect": "Allow",
        "Action": [
          "s3:ListBucket"
        ],
        "Resource": "arn:aws:s3:::archived-data-dllm"  # Allow list operation at bucket level
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "archive_data_role_attach" {
  role       = aws_iam_role.archiveOldDataRole.name
  policy_arn = aws_iam_policy.archive_data_policy.arn
}

resource "aws_iam_role_policy_attachment" "dynamodb_full_access" {
  role       = aws_iam_role.modifyMachineStatusRole.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_execution_role" {
  role       = aws_iam_role.modifyMachineStatusRole.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole"
}

resource "aws_iam_role" "postCameraImageJSONRole" {
  name = "postCameraImageJSONRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"

      }
    ]
  })
  
}

resource "aws_iam_policy" "post_camera_image_policy" {
  name        = "postCameraImagePolicy"
  description = "Policy to allow DynamoDB PutItem access for CameraImageJSON table"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:PutItem"
        ],
        "Resource" : "arn:aws:dynamodb:ap-southeast-1:149536472280:table/CameraImageJSON"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "post_camera_image_policy_attach" {
  role       = aws_iam_role.postCameraImageJSONRole.name
  policy_arn = aws_iam_policy.post_camera_image_policy.arn
}

resource "aws_iam_role" "storeDataRole" {
  name = "storeDataRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
  
}

resource "aws_iam_policy" "store_data_policy" {
  name        = "storeDataPolicy"
  description = "Policy to allow DynamoDB PutItem access for VibrationData table"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:PutItem"
        ],
        "Resource": "arn:aws:dynamodb:ap-southeast-1:149536472280:table/VibrationData"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "store_data_role_attach" {
  role       = aws_iam_role.storeDataRole.name
  policy_arn = aws_iam_policy.store_data_policy.arn
}

resource "aws_iam_policy" "update_machine_status_policy" {
  name        = "updateMachineStatusPolicy"
  description = "Policy to allow DynamoDB UpdateItem access for MachineStatusTable"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:UpdateItem"
        ],
        "Resource": "arn:aws:dynamodb:ap-southeast-1:149536472280:table/MachineStatusTable"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "update_machine_status_role_attach" {
  role       = aws_iam_role.storeDataRole.name
  policy_arn = aws_iam_policy.update_machine_status_policy.arn
}

resource "aws_iam_role" "shuffleMachineStatusRole" {
  name = "shuffleMachineStatusRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
  
}

# Define policy to allow Scan and UpdateItem actions on MachineStatusTable
resource "aws_iam_policy" "shuffle_machine_status_policy" {
  name        = "ShuffleMachineStatusPolicy"
  description = "Policy to allow DynamoDB Scan and UpdateItem access for MachineStatusTable"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:Scan",
          "dynamodb:UpdateItem"
        ],
        "Resource": "arn:aws:dynamodb:ap-southeast-1:149536472280:table/MachineStatusTable"
      }
    ]
  })
}

# Attach the policy to shuffleMachineStatusRole
resource "aws_iam_role_policy_attachment" "shuffle_machine_status_role_attach" {
  role       = aws_iam_role.shuffleMachineStatusRole.name
  policy_arn = aws_iam_policy.shuffle_machine_status_policy.arn
}

resource "aws_iam_role" "processCameraJSONRole" {
  name = "processCameraJSONRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
  
}

# Define policy to allow UpdateItem action on MachineStatusTable for postCameraImageJSONRole
resource "aws_iam_policy" "post_camera_image_update_machine_status_policy" {
  name        = "PostCameraImageUpdateMachineStatusPolicy"
  description = "Policy to allow DynamoDB UpdateItem access for MachineStatusTable for postCameraImageJSONRole"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:UpdateItem"
        ],
        "Resource": "arn:aws:dynamodb:ap-southeast-1:149536472280:table/MachineStatusTable"
      }
    ]
  })
}

# Attach the policy to postCameraImageJSONRole
resource "aws_iam_role_policy_attachment" "post_camera_image_update_machine_status_policy_attach" {
  role       = aws_iam_role.postCameraImageJSONRole.name
  policy_arn = aws_iam_policy.post_camera_image_update_machine_status_policy.arn
}

# IAM Role for Camera Data Processing Function
resource "aws_iam_role" "cameraDataRole" {
  name = "CameraDataRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
}

# Policy for Camera Data Role: DynamoDB and Lambda invoke
resource "aws_iam_policy" "camera_data_policy" {
  name        = "CameraDataPolicy"
  description = "Policy for camera data processing function"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:GetItem"
        ],
        "Resource" : "arn:aws:dynamodb:ap-southeast-1:149536472280:table/CameraDetectionData"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "lambda:InvokeFunction"
        ],
        "Resource" : "arn:aws:lambda:ap-southeast-1:149536472280:function:updateMachineStateFunction"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "camera_data_role_attach" {
  role       = aws_iam_role.cameraDataRole.name
  policy_arn = aws_iam_policy.camera_data_policy.arn
}

# IAM Role for State Machine Function (Sensor Fusion)
resource "aws_iam_role" "stateMachineRole" {
  name = "StateMachineRole"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  path = "/service-role/"
}

# Policy for State Machine: Access all relevant DynamoDB tables
resource "aws_iam_policy" "state_machine_policy" {
  name        = "StateMachinePolicy"
  description = "Policy for state machine sensor fusion function"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        "Resource" : [
          "arn:aws:dynamodb:ap-southeast-1:149536472280:table/MachineStatusTable",
          "arn:aws:dynamodb:ap-southeast-1:149536472280:table/CameraDetectionData",
          "arn:aws:dynamodb:ap-southeast-1:149536472280:table/VibrationData"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "state_machine_role_attach" {
  role       = aws_iam_role.stateMachineRole.name
  policy_arn = aws_iam_policy.state_machine_policy.arn
}

# Update storeDataRole to allow Lambda invocation
resource "aws_iam_policy" "store_data_lambda_invoke_policy" {
  name        = "StoreDataLambdaInvokePolicy"
  description = "Policy to allow storeDataFunction to invoke state machine"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "lambda:InvokeFunction"
        ],
        "Resource" : "arn:aws:lambda:ap-southeast-1:149536472280:function:updateMachineStateFunction"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "store_data_lambda_invoke_attach" {
  role       = aws_iam_role.storeDataRole.name
  policy_arn = aws_iam_policy.store_data_lambda_invoke_policy.arn
}