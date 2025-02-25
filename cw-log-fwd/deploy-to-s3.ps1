# PowerShell script to package Lambda function and upload to S3

param(
    [Parameter(Mandatory=$false)]
    [string]$Version = (Get-Date -Format "yyyyMMdd-HHmmss")
)

# Configuration
$S3BucketName = "my-lambda-deployments-bucket"
$S3KeyPrefix = "datadog-log-forwarder"
$SourceDir = ".\src"
$TempDir = ".\temp"
$ZipFileName = "lambda-package.zip"

# Ensure AWS CLI is available
if (-not (Get-Command "aws" -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI is not installed. Please install it first."
    exit 1
}

# Create temp directory if it doesn't exist
if (-not (Test-Path -Path $TempDir)) {
    New-Item -ItemType Directory -Path $TempDir | Out-Null
}

# Clean up any existing zip file
if (Test-Path "$TempDir\$ZipFileName") {
    Remove-Item "$TempDir\$ZipFileName" -Force
}

# Create zip file
try {
    Write-Host "Creating zip package for version: $Version"
    
    # Create a temporary directory for packaging
    $PackageDir = Join-Path $TempDir "package"
    if (Test-Path $PackageDir) {
        Remove-Item $PackageDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $PackageDir | Out-Null
    
    # Copy source files to package directory
    Copy-Item "$SourceDir\*" $PackageDir -Recurse
    
    # Create zip file
    $ZipPath = Join-Path $TempDir $ZipFileName
    Compress-Archive -Path "$PackageDir\*" -DestinationPath $ZipPath -Force
    
    # Set S3 key with version
    $S3Key = "$S3KeyPrefix/$Version/$ZipFileName"
    
    # Upload to S3
    Write-Host "Uploading to S3..."
    aws s3 cp $ZipPath "s3://$S3BucketName/$S3Key"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully uploaded package to s3://$S3BucketName/$S3Key"
        Write-Host "S3 URI: s3://$S3BucketName/$S3Key"
    } else {
        Write-Error "Failed to upload package to S3"
        exit 1
    }
    
} catch {
    Write-Error "Error occurred: $_"
    exit 1
} finally {
    # Cleanup
    if (Test-Path $PackageDir) {
        Remove-Item $PackageDir -Recurse -Force
    }
}
