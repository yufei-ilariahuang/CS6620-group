from aws_cdk import aws_dynamodb as dynamodb, RemovalPolicy, CfnOutput
from constructs import Construct


class StorageStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, project_prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Inventory DynamoDB Table
        inventory_table = dynamodb.Table(
            self,
            "InventoryTable",
            table_name=f"{project_prefix}-inventory",
            partition_key=dynamodb.Attribute(
                name="itemId",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev only; use RETAIN in prod
        )

        # Store reference for cross-stack access
        self.inventory_table = inventory_table

        # Outputs
        CfnOutput(self, "InventoryTableName", value=inventory_table.table_name)
        CfnOutput(self, "InventoryTableArn", value=inventory_table.table_arn)
