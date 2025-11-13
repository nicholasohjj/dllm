import boto3
import time

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('WebSocketConnections')

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
