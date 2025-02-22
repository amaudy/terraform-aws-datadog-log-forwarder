package test

import (
	"fmt"
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestDatadogForwarderComplete(t *testing.T) {
	t.Parallel()

	// Generate a random name to prevent a naming conflict
	uniqueID := random.UniqueId()
	functionName := fmt.Sprintf("datadog-forwarder-test-%s", uniqueID)

	// Construct the terraform options with default retryable errors
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../examples/complete",
		Vars: map[string]interface{}{
			"function_name":     functionName,
			"lambda_s3_bucket": "study-datadog-lambda-artifacts",
			"lambda_s3_key":    "datadog-forwarder/v1.0.0/function.zip",
			"datadog_api_key":  "dummy-key-for-testing",
		},
	})

	// At the end of the test, run `terraform destroy`
	defer terraform.Destroy(t, terraformOptions)

	// Run `terraform init` and `terraform apply`
	terraform.InitAndApply(t, terraformOptions)

	// Get the Lambda function ARN
	functionARN := terraform.Output(t, terraformOptions, "lambda_arn")

	// Verify the Lambda function exists
	aws.GetFunction(t, aws.GetDefaultRegion(t), functionName)

	// Verify the function has the correct environment variables
	function := aws.GetFunction(t, aws.GetDefaultRegion(t), functionName)
	envVars := function.Configuration.Environment.Variables

	assert.Equal(t, "datadoghq.com", *envVars["DD_SITE"])
	assert.NotEmpty(t, *envVars["DD_API_KEY_SECRET_ARN"])

	// Test the Lambda function's health check
	result, err := aws.InvokeFunctionE(t, aws.GetDefaultRegion(t), functionName, map[string]interface{}{
		"healthCheck": true,
	})
	assert.NoError(t, err)
	assert.Contains(t, string(result), "healthy")
}
