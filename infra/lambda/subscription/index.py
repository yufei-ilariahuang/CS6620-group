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
        user_email = claims.get("email")

        # Parse request body
        body = json.loads(event.get("body") or "{}")
        item_id = body.get("itemId")

        if not item_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": False, "error": "itemId is required"}),
            }

        if not user_email:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": False, "error": "email claim is required"}),
            }

        existing_item = table.get_item(Key={"itemId": item_id}).get("Item")
        if not existing_item:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": False, "error": "Item not found"}),
            }

        subscribed_user_ids = existing_item.get("subscribedUserIds", [])
        subscriber_emails = existing_item.get("subscriberEmails", [])

        if user_id in subscribed_user_ids and user_email in subscriber_emails:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"success": True, "message": f"Already subscribed to {item_id}"}),
            }

        expression_parts = []
        expression_values = {":empty": []}

        if user_id not in subscribed_user_ids:
            expression_parts.append(
                "subscribedUserIds = list_append(if_not_exists(subscribedUserIds, :empty), :userId)"
            )
            expression_values[":userId"] = [user_id]

        if user_email not in subscriber_emails:
            expression_parts.append(
                "subscriberEmails = list_append(if_not_exists(subscriberEmails, :empty), :email)"
            )
            expression_values[":email"] = [user_email]

        # Append only the missing subscription attributes.
        table.update_item(
            Key={"itemId": item_id},
            UpdateExpression="SET " + ", ".join(expression_parts),
            ConditionExpression="attribute_exists(itemId)",
            ExpressionAttributeValues=expression_values,
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
