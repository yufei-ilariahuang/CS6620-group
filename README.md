# Inventory Restock Notification System

Serverless backend on AWS for product browsing, subscriptions, and restock notifications.

## What This Project Does
- Users can view products.
- Users can subscribe to product restock notifications.
- Admin can restock inventory.
- Restock events trigger notifications to subscribed users.

## API Endpoints
- `GET /products` -> Product Lambda
- `POST /subscriptions` (or `/subscribe`) -> Subscription Lambda
- `POST /restock` -> Restock Lambda (admin only)

## Core Architecture
- **API Gateway (CDK-managed)**: public API entry point.
- **Cognito**: token issue/validation for users/admin.
- **Product Service**: reads product/inventory data.
- **Subscription Service**: stores user subscriptions.
- **Restock Service**: updates stock and emits restock events.
- **DynamoDB (Inventory table)**: product stock + subscriber references.
- **SQS**: queue for restock notification jobs.
- **Notification Service**: consumes queue, loads subscribers, sends notifications.
- **SNS**: fan-out/email delivery channel.

## Restock Flow
1. Admin calls `POST /restock`.
2. Restock service updates stock in DynamoDB.
3. Restock service emits event to SQS (`item xyz restocked`).
4. Notification service consumes SQS message.
5. Notification service reads subscriber list from DynamoDB.
6. Notification service publishes to SNS (email notifications).

## Suggested Repository Structure
```
.
├── infra/                 # CDK stacks (API Gateway, Cognito, DynamoDB, SQS, SNS)
├── services/
│   ├── product/
│   ├── subscription/
│   ├── restock/
│   └── notification/
├── shared/                # common models/utilities/auth helpers
└── README.md
```

## Quick Start (High Level)
1. Create AWS resources with CDK (API Gateway, Cognito, DynamoDB, SQS, SNS).
2. Implement Lambdas/services for product, subscription, restock, and notification.
3. Configure API Gateway routes and Cognito authorizer.
4. Wire restock -> SQS -> notification -> SNS.
5. Seed sample products and test full flow end-to-end.

## Minimal Test Checklist
- `GET /products` returns product list.
- `POST /subscriptions` saves subscriber for item.
- Unauthorized `POST /restock` is denied.
- Authorized `POST /restock` updates stock and enqueues message.
- Notification service sends SNS message to subscribers.

## Notes
- Use least-privilege IAM for each Lambda.
- Add DLQ for SQS to handle failed notifications.
- Add idempotency for restock and notification processing.
