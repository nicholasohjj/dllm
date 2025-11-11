import importlib
import json
import os

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def machine_status_table():
    with mock_aws():
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        table_name = "MachineStatusTable"
        dynamodb.create_table(
            TableName=table_name,
            AttributeDefinitions=[{"AttributeName": "machineID", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "machineID", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        table = resource.Table(table_name)
        yield table


def test_fetch_machine_status_returns_items(machine_status_table, monkeypatch):
    machine_status_table.put_item(Item={"machineID": "RVREB-W1", "status": "available"})
    machine_status_table.put_item(Item={"machineID": "RVREB-D1", "status": "in-use"})

    monkeypatch.setenv("MACHINE_STATUS_TABLE", "MachineStatusTable")
    module = importlib.import_module("aws.functions.fetchMachineStatusFunction")

    response = module.lambda_handler({}, {})
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["message"] == "Machine status retrieved successfully"
    assert len(body["data"]) == 2


def test_post_camera_image_updates_status(machine_status_table):
    machine_status_table.put_item(Item={"machineID": "RVREB-W1", "status": "available"})

    module = importlib.import_module("aws.functions.postCameraImageJSONFunction")
    event = {"body": json.dumps({"machine_id": "RVREB-W1", "available": 0})}
    response = module.lambda_handler(event, {})

    assert response["statusCode"] == 200
    item = machine_status_table.get_item(Key={"machineID": "RVREB-W1"})["Item"]
    assert item["status"] == "in-use"


def test_shuffle_machine_status_cycles_values(machine_status_table):
    machine_status_table.put_item(Item={"machineID": "RVREB-W1", "status": "available"})
    machine_status_table.put_item(Item={"machineID": "RVREB-D1", "status": "in-use"})

    module = importlib.import_module("aws.functions.shuffle_machine_status")
    response = module.lambda_handler({}, {})

    assert response["updated_machines"] == 2
    assert machine_status_table.get_item(Key={"machineID": "RVREB-W1"})["Item"]["status"] == "in-use"
    assert machine_status_table.get_item(Key={"machineID": "RVREB-D1"})["Item"]["status"] == "complete"


