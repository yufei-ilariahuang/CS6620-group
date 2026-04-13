from aws_cdk import (
    aws_iam as iam,
    aws_lambda as aws_lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
    Duration,
    CfnOutput,
)
from constructs import Construct
from .config_loader import load_app_config


class ComputeStack(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        project_prefix: str,
        inventory_table_name: str,
        inventory_table_arn: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        app_config = load_app_config()
        ses_from_email = app_config["backend"]["ses_from_email"]

        # Create SQS Queue for restock notifications
        restock_queue = sqs.Queue(
            self,
            "RestockQueue",
            queue_name=f"{project_prefix}-restock-queue",
        )
        self.restock_queue = restock_queue

        # Create Product Lambda
        product_lambda = aws_lambda.Function(
            self,
            "ProductLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=aws_lambda.Code.from_asset("./lambda/product"),
            environment={
                "INVENTORY_TABLE_NAME": inventory_table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )
        product_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Scan", "dynamodb:GetItem"],
                resources=[inventory_table_arn],
                effect=iam.Effect.ALLOW,
            )
        )
        self.product_lambda = product_lambda

        create_product_lambda = aws_lambda.Function(
            self,
            "CreateProductLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=aws_lambda.Code.from_asset("./lambda/create_product"),
            environment={
                "INVENTORY_TABLE_NAME": inventory_table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )
        create_product_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:PutItem"],
                resources=[inventory_table_arn],
                effect=iam.Effect.ALLOW,
            )
        )
        self.create_product_lambda = create_product_lambda

        # Create Subscription Lambda
        subscription_lambda = aws_lambda.Function(
            self,
            "SubscriptionLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=aws_lambda.Code.from_asset("./lambda/subscription"),
            environment={
                "INVENTORY_TABLE_NAME": inventory_table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )
        subscription_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:UpdateItem", "dynamodb:GetItem"],
                resources=[inventory_table_arn],
                effect=iam.Effect.ALLOW,
            )
        )
        self.subscription_lambda = subscription_lambda

        # Create Restock Lambda
        restock_lambda = aws_lambda.Function(
            self,
            "RestockLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=aws_lambda.Code.from_asset("./lambda/restock"),
            environment={
                "INVENTORY_TABLE_NAME": inventory_table_name,
                "RESTOCK_QUEUE_URL": restock_queue.queue_url,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )
        restock_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:UpdateItem"],
                resources=[inventory_table_arn],
                effect=iam.Effect.ALLOW,
            )
        )
        restock_queue.grant_send_messages(restock_lambda)
        self.restock_lambda = restock_lambda

        # Create Notification Lambda
        notification_lambda = aws_lambda.Function(
            self,
            "NotificationLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=aws_lambda.Code.from_asset("./lambda/notification"),
            environment={
                "INVENTORY_TABLE_NAME": inventory_table_name,
                "SES_FROM_EMAIL": ses_from_email,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )
        notification_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem"],
                resources=[inventory_table_arn],
                effect=iam.Effect.ALLOW,
            )
        )
        notification_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            )
        )
        notification_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(restock_queue, batch_size=10)
        )
        self.notification_lambda = notification_lambda

        # Outputs
        CfnOutput(self, "ProductLambdaArn", value=product_lambda.function_arn)
        CfnOutput(self, "ProductLambdaName", value=product_lambda.function_name)
        CfnOutput(self, "CreateProductLambdaArn", value=create_product_lambda.function_arn)
        CfnOutput(self, "RestockQueueUrl", value=restock_queue.queue_url)
        CfnOutput(self, "RestockQueueArn", value=restock_queue.queue_arn)
        CfnOutput(self, "NotificationLambdaArn", value=notification_lambda.function_arn)
