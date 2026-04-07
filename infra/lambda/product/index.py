import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("INVENTORY_TABLE_NAME")
table = dynamodb.Table(table_name)


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal to float for JSON serialization."""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o) if o % 1 else int(o)
        return super().default(o)


def handler(event, context):
    """
    GET /products endpoint.
    Scans the inventory table and returns all products.
    """
    try:
        # Scan entire inventory table
        response = table.scan()
        items = response.get("Items", [])

        # Return product list
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "products": items,
                    "count": len(items),
                },
                cls=DecimalEncoder,
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
        }
