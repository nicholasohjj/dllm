import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = os.environ.get('VIBRATION_DATA_TABLE')
BUCKET_NAME = os.environ.get('ARCHIVE_BUCKET_NAME')
S3_KEY = os.environ.get('ARCHIVE_S3_KEY', 'archive/oldData.json') 

def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    
    current_time_utc = datetime.now(timezone.utc)
    cutoff_time_utc = current_time_utc - timedelta(minutes=10)
    cutoff_iso = cutoff_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')  # ISO 8601 format
    
    response = table.scan(
        FilterExpression='#ts < :cutoff_time',
        ExpressionAttributeNames={'#ts': 'timestamp_value'},
        ExpressionAttributeValues={':cutoff_time': cutoff_iso}
    )
    
    items_to_archive = response.get('Items', [])
    
    if not items_to_archive:
        print("No items older than 10 minutes to archive.")
        return {
            'statusCode': 200,
            'body': json.dumps('No data found for archiving')
        }
    
    try:
        s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=S3_KEY)
        existing_data = json.loads(s3_response['Body'].read().decode('utf-8'))
    except s3.exceptions.NoSuchKey:
        # Initialize empty list if file does not exist
        existing_data = []

    # Add new items to the existing data list
    existing_data.extend(items_to_archive)
    
    # Save updated data back to S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=S3_KEY,
        Body=json.dumps(existing_data, cls=DecimalEncoder)
    )
    
    # Delete archived items from DynamoDB
    total_archived = 0
    for item in items_to_archive:
        table.delete_item(
            Key={
                'timestamp_value': item['timestamp_value'],
                'machine_id': item['machine_id']
            }
        )
        total_archived += 1
    
    return {
        'statusCode': 200,
        'body': json.dumps(f"Archived {total_archived} items to S3 and removed from DynamoDB.")
    }

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
