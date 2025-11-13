import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand } from "@aws-sdk/lib-dynamodb";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const dynamoClient = new DynamoDBClient({});
const ddbDocClient = DynamoDBDocumentClient.from(dynamoClient);
const lambdaClient = new LambdaClient({});

export const handler = async (event) => {
  console.log("Received camera detection event:", JSON.stringify(event));
  
  const cameraDataTable = process.env.CAMERA_DETECTION_TABLE || "CameraDetectionData";
  const stateMachineFunctionName = process.env.STATE_MACHINE_FUNCTION || "updateMachineStateFunction";
  
  // Add TTL (7 days from now)
  const ttl = Math.floor(Date.now() / 1000) + (7 * 24 * 60 * 60);
  
  // Store camera detection in DynamoDB
  const params = {
    TableName: cameraDataTable,
    Item: {
      machine_id: event.machine_id,
      timestamp: event.timestamp || Date.now() / 1000,
      device_type: event.device_type || "washer",
      event_type: event.event_type || "person_detected",
      is_bending: event.is_bending || false,
      confidence: event.confidence || 0,
      sensor_type: event.sensor_type || "camera",
      ttl: ttl
    }
  };
  
  try {
    await ddbDocClient.send(new PutCommand(params));
    console.log("Camera detection stored successfully");
    
    // Invoke state machine function to process the event
    const stateMachinePayload = {
      source: "camera",
      data: event
    };
    
    const invokeParams = {
      FunctionName: stateMachineFunctionName,
      InvocationType: "Event", // Async invocation
      Payload: JSON.stringify(stateMachinePayload)
    };
    
    await lambdaClient.send(new InvokeCommand(invokeParams));
    console.log("State machine function invoked");
    
    return {
      statusCode: 200,
      body: JSON.stringify({ message: "Camera data processed successfully" })
    };
  } catch (error) {
    console.error("Error processing camera data:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Failed to process camera data", error: error.message })
    };
  }
};

