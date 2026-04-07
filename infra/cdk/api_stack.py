from aws_cdk import aws_apigateway as apigw, aws_cognito as cognito, CfnOutput
from constructs import Construct


class ApiStack(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool: cognito.IUserPool,
        project_prefix: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create REST API
        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{project_prefix}-api",
            description="Inventory Restock Notification API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

        # Store references for cross-stack access
        self.api = api
        self.user_pool = user_pool

        # Outputs
        CfnOutput(self, "ApiEndpoint", value=api.url)
