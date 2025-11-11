import importlib
from datetime import datetime, timedelta

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def websocket_table():
    with mock_aws():
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="WebSocketConnections",
            AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield boto3.resource("dynamodb", region_name="us-east-1").Table("WebSocketConnections")


def test_connect_function_adds_connection_with_ttl(websocket_table):
    module = importlib.import_module("aws.functions.connectFunction")
    response = module.lambda_handler({"requestContext": {"connectionId": "abc123"}}, {})

    assert response["statusCode"] == 200
    item = websocket_table.get_item(Key={"connectionId": "abc123"})["Item"]
    expires_at = datetime.fromtimestamp(int(item["ExpirationTime"]))
    assert expires_at > datetime.utcnow()


def test_disconnect_function_removes_connection(websocket_table):
    websocket_table.put_item(
        Item={"connectionId": "abc123", "ExpirationTime": int((datetime.utcnow() + timedelta(minutes=30)).timestamp())}
    )

    module = importlib.import_module("aws.functions.disconnectFunction")
    response = module.lambda_handler({"requestContext": {"connectionId": "abc123"}}, {})

    assert response["statusCode"] == 200
    assert "Item" not in websocket_table.get_item(Key={"connectionId": "abc123"})


