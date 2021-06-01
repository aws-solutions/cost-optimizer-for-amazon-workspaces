#/bin/bash
AWS_ACCESS_KEY_ID=$(aws --profile wcoprofile configure get aws_access_key_id)
AWS_SECRET_ACCESS_KEY=$(aws --profile wcoprofile configure get aws_secret_access_key)

docker run -e BucketName="$1" -e LogLevel="INFO" -e DryRun="Yes" -e TestEndOfMonth="No" -e SendAnonymousData="No" -e SolutionVersion="v2.0" -e SolutionID="SO0018" -e ValueLimit="83" -e StandardLimit="83" -e PerformanceLimit="11" -e PowerLimit="20" -e PowerProLimit="13" -e GraphicsLimit="2" -e GraphicsProLimit="12" -e UUID="abcdefghi" -e AWS_DEFAULT_REGION="us-east-1" -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY wco-container
