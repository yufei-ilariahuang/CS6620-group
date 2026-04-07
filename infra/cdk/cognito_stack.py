from aws_cdk import aws_cognito as cognito, CfnOutput
from constructs import Construct


class CognitoStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, project_prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create User Pool
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{project_prefix}-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases={"email": True},
            standard_attributes={
                "email": cognito.StandardAttribute(required=True, mutable=True),
            },
        )

        # Create User Pool Client
        app_client = user_pool.add_client(
            "AppClient",
            auth_flows=cognito.AuthFlow(
                user_password=True,
            ),
        )

        # Create Admin Group
        admin_group = cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="admin",
            description="Admin users can trigger restock",
        )

        # Store references as class attributes for cross-stack access
        self.user_pool = user_pool
        self.app_client = app_client
        self.admin_group = admin_group

        # Outputs
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolArn", value=user_pool.user_pool_arn)
        CfnOutput(self, "AppClientId", value=app_client.user_pool_client_id)
