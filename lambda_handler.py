import json
import boto3
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from engine.waste_detector import run_all_collectors
from engine.cost_calculator import calculate_savings, summarize
from engine.cloudwatch_metrics import push_metrics


def save_report_to_dynamodb(report):
    dynamodb = boto3.resource(
        "dynamodb",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    table = dynamodb.Table("finops-reports")
    table.put_item(Item={
        "report_id":      report["generated_at"],
        "generated_at":   report["generated_at"],
        "total_findings": report["summary"]["total_findings"],
        "total_saving":   str(report["summary"]["total_monthly_saving"]),
        "report_json":    json.dumps(report, default=str),
    })
    print("  Report saved to DynamoDB finops-reports table")


def save_findings_to_dynamodb(findings):
    dynamodb = boto3.resource(
        "dynamodb",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    table = dynamodb.Table("finops-findings")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for finding in findings:
        table.put_item(Item={
            "finding_id":     finding["resource_id"] + "_" + timestamp,
            "resource_type":  finding.get("resource_type", "UNKNOWN"),
            "resource_id":    finding.get("resource_id", ""),
            "resource_name":  finding.get("resource_name", ""),
            "monthly_saving": str(finding.get("estimated_monthly_saving", 0)),
            "recommendation": finding.get("recommendation", ""),
            "detected_at":    finding.get("detected_at", timestamp),
            "report_date":    timestamp[:10],
        })
    print("  " + str(len(findings)) + " finding(s) saved to DynamoDB")


def handler(event, context):
    sep = "=" * 55
    print(sep)
    print("  FinOps Lambda Handler Starting")
    print("  Time: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    print(sep)

    findings = run_all_collectors()
    findings = calculate_savings(findings)
    summary  = summarize(findings)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "summary":      summary,
        "findings":     findings,
    }

    print("  Total findings  : " + str(summary["total_findings"]))
    print("  Monthly waste   : $" + str(summary["total_monthly_saving"]))
    print("  Annual waste    : $" + str(round(summary["total_monthly_saving"] * 12, 2)))

    print("  Saving to DynamoDB...")
    try:
        save_report_to_dynamodb(report)
        save_findings_to_dynamodb(findings)
    except Exception as e:
        print("  DynamoDB save failed: " + str(e))

    print("  Pushing to CloudWatch...")
    try:
        push_metrics(findings, summary)
    except Exception as e:
        print("  CloudWatch push failed: " + str(e))

    print("  Lambda handler complete.")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":        "FinOps scan complete",
            "total_findings": summary["total_findings"],
            "monthly_saving": summary["total_monthly_saving"],
            "annual_saving":  round(summary["total_monthly_saving"] * 12, 2),
        })
    }


if __name__ == "__main__":
    result = handler({}, {})
    print("  Lambda response:")
    print(json.dumps(json.loads(result["body"]), indent=2))