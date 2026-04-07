from aws_cdk import aws_lambda as aws_lambda, aws_iam as iam, Duration, CfnOutput
from constructs import Construct


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

        # Grant Lambda read access to DynamoDB table
        product_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Scan", "dynamodb:GetItem"],
                resources=[inventory_table_arn],
                effect=iam.Effect.ALLOW,
            )
        )

        # Store reference for cross-stack access
        self.product_lambda = product_lambda

        # Outputs
        CfnOutput(self, "ProductLambdaArn", value=product_lambda.function_arn)
        CfnOutput(self, "ProductLambdaName", value=product_lambda.function_name)
