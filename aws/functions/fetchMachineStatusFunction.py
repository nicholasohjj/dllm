import boto3
import json
import os
from decimal import Decimal

_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
_TABLE_NAME = os.getenv("MACHINE_STATUS_TABLE", "MachineStatusTable")

dynamodb = boto3.resource("dynamodb", region_name=_REGION)
machine_status_table = dynamodb.Table(_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    
    try:
        items = []
        response = machine_status_table.scan()
        items.extend(response.get('Items', []))
        
        while 'LastEvaluatedKey' in response:
            response = machine_status_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Machine status retrieved successfully',
                'data': items  
            }, cls=DecimalEncoder),  
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    except Exception as e:
        print(f"Error fetching data from DynamoDB: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to fetch machine status'}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
