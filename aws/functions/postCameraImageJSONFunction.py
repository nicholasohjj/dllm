import json
import boto3

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table_name = "MachineStatusTable" 
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': json.dumps('Error: Missing body in request')
            }
        
        json_data = json.loads(event['body'])
        
        if 'machine_id' not in json_data:
            return {
                'statusCode': 400,
                'body': json.dumps('Error: machine_id is required')
            }
        
        machine_id = json_data.pop('machine_id')
        
        if 'available' in json_data:
            status = "available" if json_data.pop('available') == 1 else "in-use"
        else:
            status = "in-use"  
        
        table.update_item(
            Key={'machineID': machine_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={
                '#s': 'status'  
            },
            ExpressionAttributeValues={
                ':status': status
            },
            ReturnValues="UPDATED_NEW"
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Status updated successfully')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error updating data: {str(e)}")
        }
