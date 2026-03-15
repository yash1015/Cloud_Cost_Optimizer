# FinOps Cost Optimization Platform

A cloud cost optimization tool that automatically detects AWS resource waste and visualizes savings opportunities.

## What it detects
- Idle EC2 instances (CPU < 5% over 7 days)
- Unattached EBS volumes
- S3 buckets with wrong storage class / no lifecycle policy
- Over-provisioned Kubernetes pods

## Tech Stack
- Python 3
- AWS Lambda + CloudWatch + DynamoDB
- Kubernetes metrics server
- Grafana dashboard

## Project Structure
```
finops-tool/
├── collectors/         # One collector per AWS service
│   ├── ec2_collector.py
│   ├── ebs_collector.py
│   ├── s3_collector.py
│   └── k8s_collector.py
├── engine/             # Recommendations + cost engine
│   ├── waste_detector.py
│   ├── cost_calculator.py
│   ├── report_builder.py
│   └── cloudwatch_metrics.py
├── alerts/             # Slack notifications
│   └── slack_alerts.py
├── dashboard/          # Grafana dashboard JSON
│   └── grafana_dashboard.json
├── lambda_handler.py   # AWS Lambda entry point
├── requirements.txt
└── .env.example
```

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/finops-tool.git
cd finops-tool
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure credentials
```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

### 4. Verify setup
```bash
python verify_setup.py
```

### 5. Run the tool
```bash
python lambda_handler.py
```

## Results
Detected **$962/year** in cloud waste on first run:
- 9 over-provisioned Kubernetes pods
- 1 S3 bucket with no lifecycle policy

## Grafana Dashboard
Import `dashboard/grafana_dashboard.json` into Grafana with a CloudWatch datasource.

## Environment Variables
| Variable | Description |
|---|---|
| AWS_ACCESS_KEY_ID | AWS access key |
| AWS_SECRET_ACCESS_KEY | AWS secret key |
| AWS_REGION | AWS region (e.g. ap-south-1) |
| EC2_CPU_IDLE_THRESHOLD | CPU % below which instance is idle (default: 5) |
| EC2_IDLE_DAYS | Days to look back for idle detection (default: 7) |
| K8S_CPU_THRESHOLD | K8s CPU usage % threshold (default: 30) |
| K8S_MEMORY_THRESHOLD | K8s memory usage % threshold (default: 30) |
| S3_DAYS_SINCE_LAST_ACCESS | Days before S3 object is flagged (default: 90) |
| SLACK_WEBHOOK_URL | Slack webhook for alerts |
