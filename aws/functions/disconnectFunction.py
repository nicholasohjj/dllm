import os
import boto3

_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
_TABLE_NAME = os.getenv("WEBSOCKET_CONNECTIONS_TABLE", "WebSocketConnections")

dynamodb = boto3.resource("dynamodb", region_name=_REGION)
table = dynamodb.Table(_TABLE_NAME)

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    table.delete_item(Key={'connectionId': connection_id})
    
    return {'statusCode': 200}
