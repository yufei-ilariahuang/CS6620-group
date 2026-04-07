#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.core_stack import CoreStack


app = cdk.App()
project_prefix = (
    app.node.try_get_context("projectPrefix")
    or os.getenv("PROJECT_PREFIX")
    or "cs6620-group"
)
stage = app.node.try_get_context("stage") or os.getenv("STAGE") or "dev"
bootstrap_qualifier = os.getenv("CDK_QUALIFIER", "hnb659fds")
account_id = os.getenv("CDK_DEFAULT_ACCOUNT") or os.getenv("AWS_ACCOUNT_ID")
region = os.getenv("CDK_DEFAULT_REGION") or os.getenv("AWS_REGION")

CoreStack(
    app,
    f"{project_prefix}-{stage}-core",
    project_prefix=project_prefix,
    stage=stage,
    synthesizer=cdk.DefaultStackSynthesizer(qualifier=bootstrap_qualifier),
    env=cdk.Environment(
        account=account_id,
        region=region,
    ),
)

app.synth()
