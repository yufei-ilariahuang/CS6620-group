import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("INVENTORY_TABLE_NAME")
table = dynamodb.Table(table_name)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
        groups = claims.get("cognito:groups", "")
        if "admin" not in groups:
            return _response(403, {"success": False, "error": "Admin access required"})

        body = json.loads(event.get("body") or "{}")
        item_id = (body.get("itemId") or "").strip()
        stock_count = body.get("stockCount", 0)

        if not item_id:
            return _response(400, {"success": False, "error": "itemId is required"})

        if not isinstance(stock_count, int) or stock_count < 0:
            return _response(
                400, {"success": False, "error": "stockCount must be a non-negative integer"}
            )

        table.put_item(
            Item={
                "itemId": item_id,
                "stockCount": stock_count,
                "subscribedUserIds": [],
                "subscriberEmails": [],
            },
            ConditionExpression="attribute_not_exists(itemId)",
        )

        return _response(
            201,
            {
                "success": True,
                "message": f"Created item {item_id} with stockCount {stock_count}",
            },
        )

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(409, {"success": False, "error": "Item already exists"})
    except Exception as e:
        print(f"Error: {str(e)}")
        return _response(500, {"success": False, "error": str(e)})
