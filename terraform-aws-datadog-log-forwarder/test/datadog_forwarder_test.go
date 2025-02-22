package test

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/cloudwatchlogs"
	"github.com/aws/aws-sdk-go/service/iam"
	"github.com/aws/aws-sdk-go/service/lambda"
	awstest "github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/retry"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDatadogForwarderComplete(t *testing.T) {
	t.Parallel()

	// Test configuration
	awsRegion := "us-east-1"
	logGroup := "/poc/dd-log"
	secretArn := os.Getenv("DD_API_KEY_SECRET_ARN")
	if secretArn == "" {
		t.Fatal("DD_API_KEY_SECRET_ARN environment variable is required")
	}
	uniqueID := random.UniqueId()
	functionName := fmt.Sprintf("datadog-forwarder-test-%s", uniqueID)
	namePrefix := "datadog-test"

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../examples/complete",
		Vars: map[string]interface{}{
			"name_prefix":      namePrefix,
			"function_name":    functionName,
			"lambda_s3_bucket": "study-datadog-lambda-artifacts",
			"lambda_s3_key":    "datadog-forwarder/v1.0.0/function.zip",
			"aws_region":       awsRegion,
			"environment":      "test",
		},
	})

	// Clean up resources after test
	defer func() {
		terraform.Destroy(t, terraformOptions)
	}()

	// Deploy resources
	terraform.InitAndApply(t, terraformOptions)

	// Get AWS clients
	lambdaClient := awstest.NewLambdaClient(t, awsRegion)
	logsClient := awstest.NewCloudWatchLogsClient(t, awsRegion)
	iamClient := awstest.NewIamClient(t, awsRegion)

	// Test 1: Lambda Function Configuration
	t.Run("Lambda Configuration", func(t *testing.T) {
		// Get Lambda function details with retry for eventual consistency
		var getFunctionOutput *lambda.GetFunctionOutput
		var err error

		retry.DoWithRetry(t, "Getting Lambda Function", 3, 5*time.Second, func() (string, error) {
			getFunctionOutput, err = lambdaClient.GetFunction(&lambda.GetFunctionInput{
				FunctionName: aws.String(functionName),
			})
			if err != nil {
				return "", err
			}
			return "Lambda function found", nil
		})

		require.NoError(t, err)
		require.NotNil(t, getFunctionOutput)
		require.NotNil(t, getFunctionOutput.Configuration)

		// Basic configuration
		assert.Equal(t, "python3.9", *getFunctionOutput.Configuration.Runtime)
		assert.Equal(t, "lambda_function.lambda_handler", *getFunctionOutput.Configuration.Handler)
		assert.Equal(t, int64(256), *getFunctionOutput.Configuration.MemorySize)
		assert.Equal(t, int64(300), *getFunctionOutput.Configuration.Timeout)

		// Environment variables
		require.NotNil(t, getFunctionOutput.Configuration.Environment)
		require.NotNil(t, getFunctionOutput.Configuration.Environment.Variables)
		envVars := getFunctionOutput.Configuration.Environment.Variables

		assert.Equal(t, "datadoghq.com", *envVars["DD_SITE"])
		assert.Equal(t, secretArn, *envVars["DD_API_KEY_SECRET_ARN"])
		assert.Equal(t, "INFO", *envVars["LOG_LEVEL"])
	})

	// Test 2: CloudWatch Log Subscription
	t.Run("CloudWatch Log Subscription", func(t *testing.T) {
		var describeFiltersOutput *cloudwatchlogs.DescribeSubscriptionFiltersOutput
		var err error

		retry.DoWithRetry(t, "Getting CloudWatch Log Subscription", 3, 5*time.Second, func() (string, error) {
			describeFiltersOutput, err = logsClient.DescribeSubscriptionFilters(&cloudwatchlogs.DescribeSubscriptionFiltersInput{
				LogGroupName: aws.String(logGroup),
			})
			if err != nil {
				return "", err
			}
			return "Subscription filter found", nil
		})

		require.NoError(t, err)
		require.NotNil(t, describeFiltersOutput)

		// Find the subscription filter for our Lambda
		functionARN := terraform.Output(t, terraformOptions, "lambda_function_arn")
		found := false
		for _, filter := range describeFiltersOutput.SubscriptionFilters {
			if *filter.DestinationArn == functionARN {
				found = true
				break
			}
		}
		assert.True(t, found, "Subscription filter not found for Lambda function")
	})

	// Test 3: Lambda Health Check
	t.Run("Lambda Health Check", func(t *testing.T) {
		var invokeOutput *lambda.InvokeOutput
		var err error

		retry.DoWithRetry(t, "Invoking Lambda Health Check", 3, 5*time.Second, func() (string, error) {
			invokeOutput, err = lambdaClient.Invoke(&lambda.InvokeInput{
				FunctionName: aws.String(functionName),
				Payload:     []byte(`{"healthCheck": true}`),
			})
			if err != nil {
				return "", err
			}
			return "Lambda invoked successfully", nil
		})

		require.NoError(t, err)
		require.NotNil(t, invokeOutput)
		require.NotNil(t, invokeOutput.Payload)

		var response map[string]interface{}
		err = json.Unmarshal(invokeOutput.Payload, &response)
		require.NoError(t, err)
		require.NotNil(t, response)

		body, ok := response["body"].(string)
		require.True(t, ok, "body should be a string")

		var healthCheck map[string]interface{}
		err = json.Unmarshal([]byte(body), &healthCheck)
		require.NoError(t, err)

		healthy, ok := healthCheck["healthy"].(bool)
		require.True(t, ok, "healthy should be a boolean")
		assert.True(t, healthy)

		checks, ok := healthCheck["checks"].(map[string]interface{})
		require.True(t, ok, "checks should be a map")

		secretsManager, ok := checks["secrets_manager"].(map[string]interface{})
		require.True(t, ok, "secrets_manager should be a map")
		assert.Equal(t, "ok", secretsManager["status"])

		datadogApi, ok := checks["datadog_api"].(map[string]interface{})
		require.True(t, ok, "datadog_api should be a map")
		assert.Equal(t, "ok", datadogApi["status"])
	})

	// Test 4: IAM Role and Policies
	t.Run("IAM Configuration", func(t *testing.T) {
		roleName := fmt.Sprintf("%s-lambda-role", namePrefix)

		// Verify role exists
		getRole, err := iamClient.GetRole(&iam.GetRoleInput{
			RoleName: aws.String(roleName),
		})
		require.NoError(t, err)
		require.NotNil(t, getRole.Role)

		// Verify inline policies
		listPoliciesOutput, err := iamClient.ListRolePolicies(&iam.ListRolePoliciesInput{
			RoleName: aws.String(roleName),
		})
		require.NoError(t, err)

		expectedPolicies := []string{
			fmt.Sprintf("%s-logging", roleName),
			fmt.Sprintf("%s-secrets", roleName),
			fmt.Sprintf("%s-cloudwatch", roleName),
		}

		for _, expectedPolicy := range expectedPolicies {
			found := false
			for _, policy := range listPoliciesOutput.PolicyNames {
				if *policy == expectedPolicy {
					found = true
					break
				}
			}
			assert.True(t, found, fmt.Sprintf("Policy %s not found", expectedPolicy))

			// Verify policy content
			getPolicyOutput, err := iamClient.GetRolePolicy(&iam.GetRolePolicyInput{
				RoleName:   aws.String(roleName),
				PolicyName: aws.String(expectedPolicy),
			})
			require.NoError(t, err)
			require.NotNil(t, getPolicyOutput.PolicyDocument)
		}
	})
}
