#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${ENDPOINT:-http://localhost:4566}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

TABLE="taskflow-tasks"
FUNCTION="taskflow-api"
ROLE="taskflow-lambda-role"
API_NAME="taskflow-api"
STAGE="dev"

DIR="$(cd "$(dirname "$0")" && pwd)"
aws_() { aws --endpoint-url "$ENDPOINT" --output text "$@"; }

echo "==> DynamoDB table"
if aws_ dynamodb describe-table --table-name "$TABLE" >/dev/null 2>&1; then
  echo "exists"
else
  aws_ dynamodb create-table \
    --table-name "$TABLE" \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST >/dev/null
fi

echo "==> IAM role"
if ! ROLE_ARN=$(aws_ iam get-role --role-name "$ROLE" --query Role.Arn 2>/dev/null); then
  ROLE_ARN=$(aws_ iam create-role --role-name "$ROLE" \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
    --query Role.Arn)
  aws_ iam put-role-policy --role-name "$ROLE" --policy-name taskflow-dynamodb \
    --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"dynamodb:PutItem\",\"dynamodb:GetItem\",\"dynamodb:DeleteItem\",\"dynamodb:Scan\"],\"Resource\":\"arn:aws:dynamodb:*:*:table/$TABLE\"}]}"
fi

echo "==> Lambda package"
BUILD="$(mktemp -d)"
(cd "$DIR/lambda" && zip -q "$BUILD/function.zip" handler.py)

echo "==> Lambda function"
if aws_ lambda get-function --function-name "$FUNCTION" >/dev/null 2>&1; then
  aws_ lambda update-function-code --function-name "$FUNCTION" \
    --zip-file "fileb://$BUILD/function.zip" >/dev/null
else
  aws_ lambda create-function \
    --function-name "$FUNCTION" \
    --runtime python3.12 \
    --handler handler.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://$BUILD/function.zip" \
    --environment "Variables={TABLE_NAME=$TABLE}" >/dev/null
fi
aws --endpoint-url "$ENDPOINT" lambda wait function-active-v2 --function-name "$FUNCTION"
FUNCTION_ARN=$(aws_ lambda get-function --function-name "$FUNCTION" \
  --query Configuration.FunctionArn)

echo "==> API Gateway"
for id in $(aws_ apigateway get-rest-apis \
  --query "items[?name=='$API_NAME'].id"); do
  aws_ apigateway delete-rest-api --rest-api-id "$id"
done
API_ID=$(aws_ apigateway create-rest-api --name "$API_NAME" --query id)
ROOT_ID=$(aws_ apigateway get-resources --rest-api-id "$API_ID" --query "items[0].id")
TASKS_ID=$(aws_ apigateway create-resource --rest-api-id "$API_ID" \
  --parent-id "$ROOT_ID" --path-part tasks --query id)
TASK_ID=$(aws_ apigateway create-resource --rest-api-id "$API_ID" \
  --parent-id "$TASKS_ID" --path-part '{id}' --query id)

URI="arn:aws:apigateway:$AWS_DEFAULT_REGION:lambda:path/2015-03-31/functions/$FUNCTION_ARN/invocations"
add_method() {
  aws_ apigateway put-method --rest-api-id "$API_ID" --resource-id "$1" \
    --http-method "$2" --authorization-type NONE >/dev/null
  aws_ apigateway put-integration --rest-api-id "$API_ID" --resource-id "$1" \
    --http-method "$2" --type AWS_PROXY --integration-http-method POST \
    --uri "$URI" >/dev/null
}
add_method "$TASKS_ID" GET
add_method "$TASKS_ID" POST
add_method "$TASK_ID" GET
add_method "$TASK_ID" DELETE

aws_ apigateway create-deployment --rest-api-id "$API_ID" \
  --stage-name "$STAGE" >/dev/null

BASE_URL="$ENDPOINT/restapis/$API_ID/$STAGE/_user_request_"
echo "$BASE_URL" > "$DIR/.api_url"

echo
echo "Deployed. Base URL:"
echo "  $BASE_URL"
