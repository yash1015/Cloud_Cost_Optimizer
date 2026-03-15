Cloud Cost Optimization Platform

A FinOps tool that detects wasted AWS resources and highlights potential cost savings.

Features

Detects idle EC2 instances (CPU < 5% for 7 days)

Finds unattached EBS volumes

Flags S3 buckets without lifecycle policies / incorrect storage class

Detects over-provisioned Kubernetes pods

Displays savings insights via Grafana dashboard

Sends Slack alerts

Tech Stack

Python 3

AWS Lambda

CloudWatch

DynamoDB

Kubernetes Metrics Server

Grafana

Project Structure
finops-tool/
├── collectors/      # AWS resource collectors
├── engine/          # Waste detection & cost calculations
├── alerts/          # Slack notifications
├── dashboard/       # Grafana dashboard
├── lambda_handler.py
└── requirements.txt
Setup
git clone https://github.com/YOUR_USERNAME/finops-tool.git
cd finops-tool
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Configure credentials:

cp .env.example .env

Run the tool:

python lambda_handler.py
Example Result

First scan detected ~$962/year in cloud waste:

9 over-provisioned Kubernetes pods

1 S3 bucket without lifecycle policy

Dashboard

Import dashboard/grafana_dashboard.json into Grafana with a CloudWatch datasource.
