Cloud Cost Optimization Platform (FinOps Tool)

Purpose:
A tool that detects wasted AWS resources and shows potential cost savings.

Key Features

Detects idle EC2 instances (CPU < 5% for 7 days)

Finds unattached EBS volumes

Identifies S3 buckets without lifecycle policies / wrong storage class

Detects over-provisioned Kubernetes pods

Shows savings insights via Grafana dashboard

Sends Slack alerts

Tech Stack

Python 3

AWS Lambda

CloudWatch

DynamoDB

Kubernetes Metrics Server

Grafana

Project Structure

collectors/ – AWS resource data collectors (EC2, EBS, S3, K8s)

engine/ – Waste detection and cost calculation

alerts/ – Slack notifications

dashboard/ – Grafana dashboard configuration

lambda_handler.py – Main execution file

Setup Steps

Clone repository

Create Python virtual environment

Install dependencies

Configure AWS credentials in .env

Run the tool

Example Result

First scan detected $962/year in wasted cloud resources:

9 over-provisioned Kubernetes pods

1 S3 bucket without lifecycle policy

Environment Variables

AWS_ACCESS_KEY_ID – AWS access key

AWS_SECRET_ACCESS_KEY – AWS secret key

AWS_REGION – AWS region

EC2_CPU_IDLE_THRESHOLD – Idle CPU threshold

EC2_IDLE_DAYS – Idle detection period

K8S_CPU_THRESHOLD / K8S_MEMORY_THRESHOLD – K8s resource thresholds

S3_DAYS_SINCE_LAST_ACCESS – S3 access limit

SLACK_WEBHOOK_URL – Slack alert webhook
