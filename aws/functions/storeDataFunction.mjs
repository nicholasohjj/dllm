import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand } from "@aws-sdk/lib-dynamodb";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const dynamoClient = new DynamoDBClient({});
const ddbDocClient = DynamoDBDocumentClient.from(dynamoClient);
const lambdaClient = new LambdaClient({});
const toIsoSeconds = (date) => date.toISOString().replace(/\.\d{3}Z$/, "Z");

export const handler = async (event) => {
  console.log("Received vibration event:", JSON.stringify(event));
  
  const tableName = process.env.DYNAMODB_TABLE;
  const stateMachineFunctionName = process.env.STATE_MACHINE_FUNCTION || "updateMachineStateFunction";
  const eventTimestamp = event.timestamp ?? Date.now() / 1000;
  const normalizedEvent = {
    ...event,
    timestamp: eventTimestamp,
    timestamp_value: event.timestamp_value || toIsoSeconds(new Date())
  };

  // Structure the event data to fit the DynamoDB table's schema
  const params = {
    TableName: tableName,
    Item: normalizedEvent,
  };

  try {
    await ddbDocClient.send(new PutCommand(params));
    console.log("Vibration data stored successfully:", event);

    // Invoke state machine function to process the event
    const stateMachinePayload = {
      source: "imu",
      data: normalizedEvent
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
      body: JSON.stringify({ message: "Data processed successfully" }),
    };
  } catch (error) {
    console.error("Error processing data:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Failed to process data", error: error.message }),
    };
  }
};
