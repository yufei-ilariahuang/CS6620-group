import json
import boto3
import os

dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("INVENTORY_TABLE_NAME")
table = dynamodb.Table(table_name)


def handler(event, context):
    try:
        # Extract userId from Cognito JWT claims
        claims = event["requestContext"]["authorizer"]["claims"]
        user_id = claims["sub"]

        # Parse request body
        body = json.loads(event.get("body") or "{}")
        item_id = body.get("itemId")

        if not item_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": False, "error": "itemId is required"}),
            }

        # Append userId to subscribedUserIds list (creates list if not exists)
        table.update_item(
            Key={"itemId": item_id},
            UpdateExpression="SET subscribedUserIds = list_append(if_not_exists(subscribedUserIds, :empty), :userId)",
            ConditionExpression="attribute_exists(itemId)",
            ExpressionAttributeValues={
                ":userId": [user_id],
                ":empty": [],
            },
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"success": True, "message": f"Subscribed to {item_id}"}),
        }

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"success": False, "error": "Item not found"}),
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"success": False, "error": str(e)}),
        }
