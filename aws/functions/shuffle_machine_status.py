import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('MACHINE_STATUS_TABLE', 'MachineStatusTable'))

STATUSES = ["available", "in-use", "complete"]

def lambda_handler(event, context):
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    if not items:
        return {"message": "No machines found in MachineStatusTable"}

    updated_machines = 0
    for item in items:
        machine_id = item["machineID"]
        current_status = item.get("status")

        if current_status not in STATUSES:
            print(f"Skipping machine {machine_id} due to invalid status '{current_status}'")
            continue 

        next_status_index = (STATUSES.index(current_status) + 1) % len(STATUSES)
        next_status = STATUSES[next_status_index]

        table.update_item(
            Key={"machineID": machine_id},
            UpdateExpression="SET #s = :next_status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":next_status": next_status}
        )
        updated_machines += 1

    return {
        "message": f"statuses shuffled for {updated_machines} machines",
        "updated_machines": updated_machines
    }
