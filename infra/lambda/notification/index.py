import json
import os

import boto3


dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")

table_name = os.environ.get("INVENTORY_TABLE_NAME")
ses_from_email = os.environ.get("SES_FROM_EMAIL")
table = dynamodb.Table(table_name)


def _build_message(item_id, stock_count, subscribed_user_ids, subscriber_emails):
    subscriber_count = len(subscribed_user_ids)
    return {
        "eventType": "ITEM_RESTOCKED",
        "itemId": item_id,
        "stockCount": stock_count,
        "subscriberCount": subscriber_count,
        "subscribedUserIds": subscribed_user_ids,
        "subscriberEmails": subscriber_emails,
    }


def _send_email(item_id, stock_count, subscribed_user_ids, recipient_email):
    subscriber_count = len(subscribed_user_ids)
    ses.send_email(
        Source=ses_from_email,
        Destination={"ToAddresses": [recipient_email]},
        Message={
            "Subject": {
                "Data": f"Restock alert for {item_id}",
                "Charset": "UTF-8",
            },
            "Body": {
                "Text": {
                    "Data": (
                        f"Item {item_id} has been restocked.\n"
                        f"New stock count: {stock_count}\n"
                        f"Subscribed user count: {subscriber_count}\n"
                        f"Your subscription has been matched for item {item_id}."
                    ),
                    "Charset": "UTF-8",
                }
            },
        },
    )


def handler(event, context):
    processed = 0
    skipped = 0

    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            item_id = body.get("itemId")
            stock_count = body.get("stockCount")

            if not item_id:
                print(f"Skipping message without itemId: {record['body']}")
                skipped += 1
                continue

            response = table.get_item(Key={"itemId": item_id})
            item = response.get("Item")
            if not item:
                print(f"Skipping message because item does not exist: {item_id}")
                skipped += 1
                continue

            subscribed_user_ids = item.get("subscribedUserIds", [])
            subscriber_emails = item.get("subscriberEmails", [])
            if not subscribed_user_ids or not subscriber_emails:
                print(f"No subscribers for item {item_id}; skipping publish.")
                skipped += 1
                continue

            unique_emails = sorted(set(subscriber_emails))
            message = _build_message(item_id, stock_count, subscribed_user_ids, unique_emails)
            print(f"Sending SES notification: {json.dumps(message)}")
            for email in unique_emails:
                _send_email(item_id, stock_count, subscribed_user_ids, email)
                processed += 1
        except Exception as exc:
            print(f"Failed to process SQS record: {exc}")
            raise

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "success": True,
                "processed": processed,
                "skipped": skipped,
            }
        ),
    }
