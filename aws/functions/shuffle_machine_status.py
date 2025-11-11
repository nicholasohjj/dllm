import os

import boto3

_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
_TABLE_NAME = os.getenv("MACHINE_STATUS_TABLE", "MachineStatusTable")

dynamodb = boto3.resource("dynamodb", region_name=_REGION)
table = dynamodb.Table(_TABLE_NAME)

statuss = ["available", "in-use", "complete"]

def lambda_handler(event, context):
    response = table.scan()
    items = response.get("Items", [])

    if not items:
        return {"message": "No machines found in MachineStatusTable"}

    for item in items:
        machine_id = item["machineID"]
        current_status = item.get("status")

        if current_status not in statuss:
            print(f"Skipping machine {machine_id} due to invalid status '{current_status}'")
            continue 

        next_status_index = (statuss.index(current_status) + 1) % len(statuss)
        next_status = statuss[next_status_index]

        table.update_item(
            Key={"machineID": machine_id},
            UpdateExpression="SET #s = :next_status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":next_status": next_status}
        )

    return {
        "message": f"statuses shuffled for {len(items)} machines",
        "updated_machines": len(items)
    }
