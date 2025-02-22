#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Running Terraform format check...${NC}"
terraform fmt -check -recursive ..

echo -e "${YELLOW}Running Terraform validation...${NC}"
for dir in ../examples/*/; do
    echo "Validating $dir..."
    (cd "$dir" && terraform init -backend=false && terraform validate)
done

echo -e "${YELLOW}Running tflint...${NC}"
tflint --recursive

echo -e "${YELLOW}Running Terratest...${NC}"
go mod tidy
go test -v -timeout 30m
