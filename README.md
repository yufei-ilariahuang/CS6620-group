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
- **SES**: email delivery channel for subscribed users.

## Restock Flow
1. Admin calls `POST /restock`.
2. Restock service updates stock in DynamoDB.
3. Restock service emits event to SQS (`item xyz restocked`).
4. Notification service consumes SQS message.
5. Notification service reads subscriber list from DynamoDB.
6. Notification service sends SES emails to subscribed users.

## SES Final Implementation

The notification path now uses Amazon SES:

`POST /restock -> SQS -> Notification Lambda -> SES -> subscribed user email`

`Subscription Lambda` stores `subscriberEmails`, and `Notification Lambda` reads those emails from DynamoDB and sends the restock notification through SES.

If SES is still in sandbox, both sender and recipient emails must be verified.

The sender email is configured in [app_config.yml](./app_config.yml) as `backend.ses_from_email`. If you change it, verify the new sender in SES and redeploy CDK.

## Repository Structure
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
4. Wire restock -> SQS -> notification -> SES.
5. Seed sample products and test full flow end-to-end.



## Teammate Repro 

1. Create `.env.team` from template, then edit values:

```bash
cp .env.team.example .env.team
```

Rules:
- Use your own `AWS_PROFILE` and `AWS_ACCOUNT_ID`.
- Keep `AWS_REGION`, `PROJECT_PREFIX`, `STAGE`, and `CDK_QUALIFIER` project-specific to avoid conflicts.
- `CDK_QUALIFIER` must be lowercase letters/numbers.

2. Bootstrap, then deploy:

```bash
cd /Users/liahuang/CS6620-group
set -a
source .env.team
set +a

./bootstrap-team.sh

cd infra
cdk deploy --all \
  --profile "$AWS_PROFILE" \
  --qualifier "$CDK_QUALIFIER" \
  -c projectPrefix="$PROJECT_PREFIX" \
  -c stage="$STAGE" \
  --require-approval never
```

3. Seed test items:

```bash
# If you use a different region/profile/prefix, keep .env.team updated first.
set -a
source .env.team
set +a

STACK_NAME="${PROJECT_PREFIX}-${STAGE}-core"
TABLE_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'InventoryTableName')].OutputValue" \
  --output text)

aws dynamodb put-item --table-name "$TABLE_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" --item '{"itemId":{"S":"item-001"},"stockCount":{"N":"10"},"subscribedUserIds":{"L":[]}}'
aws dynamodb put-item --table-name "$TABLE_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" --item '{"itemId":{"S":"item-002"},"stockCount":{"N":"0"},"subscribedUserIds":{"L":[]}}'
aws dynamodb put-item --table-name "$TABLE_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" --item '{"itemId":{"S":"item-003"},"stockCount":{"N":"25"},"subscribedUserIds":{"L":[]}}'
```

4. Verify API:

```bash
set -a
source .env.team
set +a

STACK_NAME="${PROJECT_PREFIX}-${STAGE}-core"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'ApiEndpoint')].OutputValue" \
  --output text)

curl "${API_URL}products"
```

## Minimal Test Checklist
- `GET /products` returns product list.
- `POST /subscriptions` saves subscriber for item.
- Unauthorized `POST /restock` is denied.
- Authorized `POST /restock` updates stock and enqueues message.
- Notification service sends SES email to subscribers.

## Run Frontend

The frontend is a static site under [services/frontend/](./services/frontend/).

Before running it:

1. deploy the AWS stack
2. refresh [app_config.yml](./app_config.yml) with the latest stack values

Use the sync script:

bash:

```bash
python ./scripts/sync_app_config.py
```

Then start a local static server from the repository root.

bash:

```bash
python -m http.server 8000
```

Open the frontend in your browser:

```text
http://localhost:8000/services/frontend/
```

Current frontend capabilities:

- user sign up
- user email confirmation
- user sign in
- admin sign in
- first-login password challenge handling
- user subscribe flow
- admin restock flow
- admin product upload flow

Role behavior:

- normal user signs in to the subscribe dashboard
- admin signs in to the restock/upload dashboard

## Notes
- Use least-privilege IAM for each Lambda.
- Add DLQ for SQS to handle failed notifications.
- Add idempotency for restock and notification processing.
