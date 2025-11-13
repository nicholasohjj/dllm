  resource "aws_iot_policy" "esp32_policy" {
    name = "ESP32Policy"
    policy = jsonencode({
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Effect" : "Allow",
          "Action" : [
            "iot:Connect",
            "iot:Publish",
            "iot:Subscribe",
            "iot:Receive"
          ],
          "Resource" : "*"
        }
      ]
    })
  }

  resource "aws_iot_thing" "esp32_1" { name = "esp32-1" }
  resource "aws_iot_thing" "esp32_2" { name = "esp32-2" }
  resource "aws_iot_thing" "esp32_3" { name = "esp32-3" }
  resource "aws_iot_thing" "esp32_4" { name = "esp32-4" }

  resource "aws_iot_topic_rule" "StoreVibrationDataRule" {
    name        = "StoreVibrationData"
    description = "Store Vibration Data in DynamoDB"
    enabled     = true
    sql         = "SELECT * FROM 'laundry/vibration'"
    sql_version = "2016-03-23"

    lambda {
      function_arn = aws_lambda_function.storeDataFunction.arn
    }
  }

  resource "aws_lambda_permission" "allow_iot_invoke" {
    statement_id  = "AllowIoTInvoke"
    action        = "lambda:InvokeFunction"
    function_name = aws_lambda_function.storeDataFunction.function_name
    principal     = "iot.amazonaws.com"
    source_arn    = aws_iot_topic_rule.StoreVibrationDataRule.arn
  }

  resource "aws_iot_topic_rule" "buttonRule" {
    name        = "ButtonRule"
    enabled     = true
    sql         = "SELECT * FROM 'laundry/button'"
    sql_version = "2016-03-23"

    lambda {
      function_arn = aws_lambda_function.shuffle_machine_status.arn
    }
  }

  resource "aws_lambda_permission" "allow_iot_invoke_button" {
    statement_id  = "AllowIoTInvokeButton"
    action        = "lambda:InvokeFunction"
    function_name = aws_lambda_function.shuffle_machine_status.function_name
    principal     = "iot.amazonaws.com"
    source_arn    = aws_iot_topic_rule.buttonRule.arn
  }

  # New IoT Rule for Camera Detection Data
  resource "aws_iot_topic_rule" "ProcessCameraDataRule" {
    name        = "ProcessCameraData"
    description = "Process camera detection data and update machine status"
    enabled     = true
    sql         = "SELECT * FROM 'laundry/camera'"
    sql_version = "2016-03-23"

    lambda {
      function_arn = aws_lambda_function.processCameraDataFunction.arn
    }
  }

  resource "aws_lambda_permission" "allow_iot_invoke_camera" {
    statement_id  = "AllowIoTInvokeCamera"
    action        = "lambda:InvokeFunction"
    function_name = aws_lambda_function.processCameraDataFunction.function_name
    principal     = "iot.amazonaws.com"
    source_arn    = aws_iot_topic_rule.ProcessCameraDataRule.arn
  }

  