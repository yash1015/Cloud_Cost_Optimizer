import boto3
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

cloudwatch = boto3.client(
    "cloudwatch",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)


def push_metrics(findings, summary):
    """
    Pushes findings as custom CloudWatch metrics.
    Grafana will read these and display them as panels.
    """
    timestamp = datetime.now(timezone.utc)

    metrics = [
        {
            "MetricName": "TotalMonthlyWaste",
            "Value":      summary["total_monthly_saving"],
            "Unit":       "None",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "TotalFindings",
            "Value":      summary["total_findings"],
            "Unit":       "Count",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "EC2Findings",
            "Value":      summary["by_type"]["EC2"]["count"],
            "Unit":       "Count",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "EBSFindings",
            "Value":      summary["by_type"]["EBS"]["count"],
            "Unit":       "Count",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "S3Findings",
            "Value":      summary["by_type"]["S3"]["count"],
            "Unit":       "Count",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "K8sFindings",
            "Value":      summary["by_type"]["K8S_POD"]["count"],
            "Unit":       "Count",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "EC2MonthlySaving",
            "Value":      summary["by_type"]["EC2"]["saving"],
            "Unit":       "None",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
        {
            "MetricName": "K8sMonthlySaving",
            "Value":      summary["by_type"]["K8S_POD"]["saving"],
            "Unit":       "None",
            "Dimensions": [{"Name": "Tool", "Value": "FinOps"}]
        },
    ]

    # CloudWatch accepts max 20 metrics per call
    cloudwatch.put_metric_data(
        Namespace="FinOps/CostOptimization",
        MetricData=[
            {**m, "Timestamp": timestamp} for m in metrics
        ]
    )

    print("  Pushed " + str(len(metrics)) + " metrics to CloudWatch namespace: FinOps/CostOptimization")


if __name__ == "__main__":
    # Test with dummy data
    test_summary = {
        "total_findings":       10,
        "total_monthly_saving": 80.25,
        "by_type": {
            "EC2":     {"count": 1, "saving": 0},
            "EBS":     {"count": 0, "saving": 0},
            "S3":      {"count": 1, "saving": 0},
            "K8S_POD": {"count": 9, "saving": 80.25},
        }
    }
    push_metrics([], test_summary)
    print("  Done — check CloudWatch console under custom namespace FinOps/CostOptimization")
