# Reimbursement System - Terraform Infrastructure

This directory contains Terraform code for deploying the Reimbursement System to AWS.

## Architecture Overview

The infrastructure includes:

- **VPC**: Multi-AZ VPC with public and private subnets
- **RDS**: MySQL database for storing reports, receipts, and audit logs
- **S3**: Bucket for storing receipt images with versioning and encryption
- **SQS**: Message queues for OCR and validation jobs with DLQs
- **ECS Fargate**: Container orchestration for API and worker services
- **CloudWatch**: Log aggregation and monitoring
- **IAM**: Fine-grained permissions for ECS tasks

## Pre-requisites

1. Install Terraform >= 1.0
2. Install AWS CLI
3. Configure AWS credentials (`~/.aws/credentials` or environment variables)
4. Docker images built and pushed to ECR (or use public registry)

## Quick Start

### 1. Build and Push Docker Images

```bash
# Build images
cd services/reimbursement_api
docker build -t reimbursement-api:staging .

cd services/ocr_worker
docker build -t reimbursement-ocr-worker:staging .

# Tag for ECR (replace with your ECR URI)
docker tag reimbursement-api:staging <account-id>.dkr.ecr.us-east-1.amazonaws.com/reimbursement-api:staging
docker tag reimbursement-ocr-worker:staging <account-id>.dkr.ecr.us-east-1.amazonaws.com/reimbursement-ocr-worker:staging

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/reimbursement-api:staging
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/reimbursement-ocr-worker:staging
```

### 2. Deploy Infrastructure

```bash
cd infrastructure/terraform/staging

# Initialize Terraform
terraform init

# Create a terraform.tfvars file (see terraform.tfvars.example)
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Plan the deployment
terraform plan -out=tfplan

# Apply the infrastructure
terraform apply tfplan
```

### 3. Access the API

After deployment:

1. Get the ALB DNS name from AWS Console or Terraform output
2. Test the API:

```bash
# Create a report
curl -X POST https://<alb-dns-name>/v1/reports \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Report", "description": "Testing deployment"}'
```

## Module Details

### VPC Module

Creates a multi-AZ VPC with:
- 2 public subnets (for load balancers)
- 2 private subnets (for ECS tasks and RDS)
- NAT Gateways for outbound internet access
- VPC Flow Logs (optional)

**Variables:**
- `vpc_cidr`: CIDR block (default: 10.0.0.0/16)
- `public_subnet_cidrs`: Public subnet CIDR blocks
- `private_subnet_cidrs`: Private subnet CIDR blocks
- `enable_nat_gateway`: Enable NAT gateways (default: true)

### RDS Module

Creates a MySQL RDS instance with:
- Multi-AZ for production
- Automated backups
- Performance Insights
- Enhanced Monitoring

**Variables:**
- `db_instance_class`: RDS instance class
- `db_allocated_storage`: Storage size in GB
- `db_name`, `db_username`, `db_password`: Database credentials
- `backup_retention_period`: Backup retention days

### S3 Module

Creates S3 buckets for:
- Receipt images storage
- Terraform state (optional)
- ECS exec logs

Features:
- Server-side encryption
- Versioning enabled
- Lifecycle policies

### SQS Module

Creates queues for:
- OCR jobs (with DLQ)
- Validation jobs (with DLQ)

Features:
- 3-attempt retry policy
- 14-day message retention
- Queue policies for ECS access

### ECS Module

Creates Fargate services for:
- API (with ALB integration)
- OCR Worker
- Validation Worker

Features:
- Auto-scaling based on CPU/memory
- CloudWatch Logs integration
- Health checks
- Task roles for AWS service access

## Monitoring

### CloudWatch Metrics

The deployment creates several CloudWatch resources:

- **Log Groups**: `/ecs/<project>/<env>/*`
- **VPC Flow Logs**: VPC traffic monitoring (if enabled)
- **RDS Metrics**: Database performance metrics

### Important Metrics to Monitor

1. **API Health**:
   - TargetResponseTime
   - HTTPCode_Target_2XX_Count
   - HTTPCode_Target_5XX_Count

2. **Worker Performance**:
   - ApproximateNumberOfMessagesVisible (SQS)
   - CPUUtilization (ECS)
   - MemoryUtilization (ECS)

3. **Database**:
   - CPUUtilization
   - DatabaseConnections
   - FreeStorageSpace

## Security Considerations

1. **Credentials**: All sensitive data (DB passwords, JWT secrets) should be passed via environment variables or AWS Secrets Manager
2. **Network**: ECS tasks run in private subnets with no public IPs
3. **Encryption**: S3 buckets and RDS have encryption at rest enabled
4. **IAM**: Least-privilege policies for ECS tasks

## Cost Optimization

1. **Development**: Use `db.t3.micro` for RDS, single NAT Gateway
2. **Staging**: Use `db.t3.small`, enable auto-scaling
3. **Production**: Use `db.m5.large` or higher, multi-AZ, multiple NAT Gateways

## Troubleshooting

### Common Issues

1. **ECS tasks not starting**
   - Check CloudWatch Logs for errors
   - Verify security group rules
   - Check IAM role permissions

2. **Database connection errors**
   - Verify RDS security group allows ECS security group
   - Check database credentials
   - Ensure private subnet route tables have NAT Gateway

3. **SQS messages not processing**
   - Check worker logs in CloudWatch
   - Verify SQS queue policies
   - Check IAM task role permissions

### Useful Commands

```bash
# View ECS service events
aws ecs describe-services --cluster <cluster-name> --services <service-name>

# View logs
aws logs tail /ecs/reimbursement-system/staging/api --follow

# Check SQS queue depth
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names ApproximateNumberOfMessages

# List running tasks
aws ecs list-tasks --cluster <cluster-name>
```

## Environment-Specific Configurations

### Staging

- Smaller instance sizes
- Single NAT Gateway
- Shorter backup retention
- Lower auto-scaling limits

### Production

- Larger instance sizes
- Multiple NAT Gateways (one per AZ)
- Multi-AZ RDS
- Longer backup retention
- Higher auto-scaling limits

## CI/CD Integration

### Example GitHub Actions Workflow

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ develop ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v1

      - name: Terraform Init
        run: |
          cd infrastructure/terraform/staging
          terraform init

      - name: Terraform Apply
        run: |
          cd infrastructure/terraform/staging
          terraform apply -auto-approve -var="db_password=${{ secrets.DB_PASSWORD }}"
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all data in RDS and S3. Make sure to backup production data before destroying.

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review Terraform state: `terraform show`
3. Check AWS Console for resource health
4. Enable debug logging: `export TF_LOG=DEBUG`
