import os
import boto3
import time

_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
_TABLE_NAME = os.getenv("WEBSOCKET_CONNECTIONS_TABLE", "WebSocketConnections")

dynamodb = boto3.resource("dynamodb", region_name=_REGION)
table = dynamodb.Table(_TABLE_NAME)

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    # Set TTL to 30 minutes from now (in seconds)
    ttl_duration = 1800  # 30 minutes
    expiration_time = int(time.time()) + ttl_duration

    table.put_item(
        Item={
            'connectionId': connection_id,
            'ExpirationTime': expiration_time  # This field is used for TTL
        }
    )
    
    return {'statusCode': 200, 'body': 'Connection added with TTL'}
