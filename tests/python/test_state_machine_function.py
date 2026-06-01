import importlib
import json
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def state_machine_tables(monkeypatch):
    with mock_aws():
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MachineStatusTable",
            AttributeDefinitions=[{"AttributeName": "machineID", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "machineID", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="CameraDetectionData",
            AttributeDefinitions=[
                {"AttributeName": "machine_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "N"},
            ],
            KeySchema=[
                {"AttributeName": "machine_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        monkeypatch.setenv("MACHINE_STATUS_TABLE", "MachineStatusTable")
        monkeypatch.setenv("CAMERA_DETECTION_TABLE", "CameraDetectionData")

        resource = boto3.resource("dynamodb", region_name="us-east-1")
        yield resource.Table("MachineStatusTable"), resource.Table("CameraDetectionData")


def test_camera_unload_after_completed_cycle_updates_machine(state_machine_tables):
    machine_table, camera_table = state_machine_tables
    module = importlib.import_module("aws.functions.updateMachineStateFunction")
    now = datetime.now()

    machine_table.put_item(
        Item={
            "machineID": "RVREB-W1",
            "status": "in-use",
            "lastUpdated": Decimal(str((now - timedelta(minutes=45)).timestamp())),
        }
    )
    camera_table.put_item(
        Item={"machine_id": "RVREB-W1", "timestamp": Decimal(str(now.timestamp() - 2))}
    )
    camera_table.put_item(
        Item={"machine_id": "RVREB-W1", "timestamp": Decimal(str(now.timestamp() - 1))}
    )

    response = module.lambda_handler(
        {
            "source": "camera",
            "data": {
                "machine_id": "RVREB-W1",
                "device_type": "washer",
                "is_bending": True,
                "confidence": 0.9,
            },
        },
        {},
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["previous_state"] == "in-use"
    assert body["new_state"] == "available"
    assert machine_table.get_item(Key={"machineID": "RVREB-W1"})["Item"]["status"] == "available"


def test_legacy_vibration_payload_can_mark_machine_in_use(state_machine_tables):
    machine_table, _ = state_machine_tables
    module = importlib.import_module("aws.functions.updateMachineStateFunction")
    machine_table.put_item(Item={"machineID": "RVREB-W1", "status": "available"})

    response = module.lambda_handler(
        {"source": "imu", "data": {"machine_id": "RVREB-W1", "vibration": 1}},
        {},
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["new_state"] == "in-use"
    assert machine_table.get_item(Key={"machineID": "RVREB-W1"})["Item"]["status"] == "in-use"


def test_low_spinning_vote_confidence_can_finish_cycle(state_machine_tables):
    machine_table, _ = state_machine_tables
    module = importlib.import_module("aws.functions.updateMachineStateFunction")
    machine_table.put_item(
        Item={
            "machineID": "RVREB-D1",
            "status": "in-use",
            "lastUpdated": Decimal(str((datetime.now() - timedelta(minutes=60)).timestamp())),
        }
    )

    response = module.lambda_handler(
        {
            "source": "imu",
            "data": {
                "machine_id": "RVREB-D1",
                "device_type": "dryer",
                "is_spinning": 0,
                "confidence": 0.0,
            },
        },
        {},
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["new_state"] == "finishing"
    assert machine_table.get_item(Key={"machineID": "RVREB-D1"})["Item"]["status"] == "finishing"
