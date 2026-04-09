import json
import boto3
import os

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")
table_name = os.environ.get("INVENTORY_TABLE_NAME")
queue_url = os.environ.get("RESTOCK_QUEUE_URL")
table = dynamodb.Table(table_name)


def handler(event, context):
    try:
        # Check admin group from Cognito JWT claims
        claims = event["requestContext"]["authorizer"]["claims"]
        groups = claims.get("cognito:groups", "")
        if "admin" not in groups:
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": False, "error": "Admin access required"}),
            }

        # Parse request body
        body = json.loads(event.get("body") or "{}")
        item_id = body.get("itemId")
        stock_count = body.get("stockCount")

        if not item_id or stock_count is None:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": False, "error": "itemId and stockCount are required"}),
            }

        # Update stockCount in DynamoDB
        table.update_item(
            Key={"itemId": item_id},
            UpdateExpression="SET stockCount = :count",
            ConditionExpression="attribute_exists(itemId)",
            ExpressionAttributeValues={":count": stock_count},
        )

        # Send restock event to SQS
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({"itemId": item_id, "stockCount": stock_count}),
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"success": True, "message": f"Item {item_id} restocked to {stock_count}"}),
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
