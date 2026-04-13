from aws_cdk import (
    CfnOutput,
    Stack,
    Tags,
)
from constructs import Construct
from .cognito_stack import CognitoStack
from .storage_stack import StorageStack
from .api_stack import ApiStack
from .compute_stack import ComputeStack
import aws_cdk.aws_apigateway as apigw


class CoreStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, project_prefix: str, stage: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        Tags.of(self).add("project", project_prefix)
        Tags.of(self).add("stage", stage)

        # 1. Create Cognito stack
        cognito_stack = CognitoStack(self, "CognitoStack", project_prefix=project_prefix)

        # 2. Create Storage stack (DynamoDB)
        storage_stack = StorageStack(self, "StorageStack", project_prefix=project_prefix)

        # 3. Create API Gateway stack
        api_stack = ApiStack(
            self,
            "ApiStack",
            user_pool=cognito_stack.user_pool,
            project_prefix=project_prefix,
        )

        # 4. Create Compute stack (Lambda + SQS)
        compute_stack = ComputeStack(
            self,
            "ComputeStack",
            project_prefix=project_prefix,
            inventory_table_name=storage_stack.inventory_table.table_name,
            inventory_table_arn=storage_stack.inventory_table.table_arn,
        )

        # 5. Wire Product Lambda to GET /products (no auth)
        product_integration = apigw.LambdaIntegration(compute_stack.product_lambda)
        products_resource = api_stack.api.root.add_resource("products")
        products_resource.add_method("GET", product_integration)
        create_product_integration = apigw.LambdaIntegration(compute_stack.create_product_lambda)
        products_resource.add_method(
            "POST",
            create_product_integration,
            authorizer=api_stack.cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # 6. Wire Subscription Lambda to POST /subscriptions (Cognito auth)
        subscription_integration = apigw.LambdaIntegration(compute_stack.subscription_lambda)
        subscriptions_resource = api_stack.api.root.add_resource("subscriptions")
        subscriptions_resource.add_method(
            "POST",
            subscription_integration,
            authorizer=api_stack.cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # 7. Wire Restock Lambda to POST /restock (Cognito auth, admin check in Lambda)
        restock_integration = apigw.LambdaIntegration(compute_stack.restock_lambda)
        restock_resource = api_stack.api.root.add_resource("restock")
        restock_resource.add_method(
            "POST",
            restock_integration,
            authorizer=api_stack.cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # Output summary
        CfnOutput(self, "ProjectPrefix", value=project_prefix)
        CfnOutput(self, "Stage", value=stage)
