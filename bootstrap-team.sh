#!/usr/bin/env bash
set -euo pipefail

# Team-safe CDK bootstrap/deploy helper.
# Use unique PROJECT_PREFIX/STAGE/QUALIFIER to avoid affecting other stacks (e.g., HW4).

if [[ -f .env.team ]]; then
  # shellcheck disable=SC1091
  source .env.team
fi

: "${AWS_PROFILE:=default}"
: "${AWS_REGION:=us-east-1}"
: "${PROJECT_PREFIX:=cs6620-group}"
: "${STAGE:=dev}"
: "${CDK_QUALIFIER:=h3grp}"
: "${INFRA_DIR:=infra}"
: "${DEPLOY:=false}"

if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)"
fi

export AWS_PROFILE AWS_REGION CDK_DEFAULT_ACCOUNT="$AWS_ACCOUNT_ID" CDK_DEFAULT_REGION="$AWS_REGION" CDK_QUALIFIER

echo "Using:"
echo "  AWS_PROFILE=$AWS_PROFILE"
echo "  AWS_REGION=$AWS_REGION"
echo "  AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"
echo "  PROJECT_PREFIX=$PROJECT_PREFIX"
echo "  STAGE=$STAGE"
echo "  CDK_QUALIFIER=$CDK_QUALIFIER"
echo "  INFRA_DIR=$INFRA_DIR"

TARGET="aws://${AWS_ACCOUNT_ID}/${AWS_REGION}"

if [[ ! -d "$INFRA_DIR" ]]; then
  echo "Infra directory not found: $INFRA_DIR"
  exit 1
fi

pushd "$INFRA_DIR" >/dev/null

echo "Bootstrapping CDK environment: $TARGET"
cdk bootstrap "$TARGET" \
  --profile "$AWS_PROFILE" \
  --qualifier "$CDK_QUALIFIER" \
  -c projectPrefix="$PROJECT_PREFIX" \
  -c stage="$STAGE"

if [[ "$DEPLOY" == "true" ]]; then
  echo "Deploying stacks"
  cdk deploy --all \
    --profile "$AWS_PROFILE" \
    --qualifier "$CDK_QUALIFIER" \
    -c projectPrefix="$PROJECT_PREFIX" \
    -c stage="$STAGE" \
    --require-approval never
else
  echo "Bootstrap done. Set DEPLOY=true to deploy stacks too."
fi

popd >/dev/null
