import boto3
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ── AWS clients ──────────────────────────────────────────
ec2 = boto3.client(
    "ec2",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

cloudwatch = boto3.client(
    "cloudwatch",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# ── Thresholds ───────────────────────────────────────────
CPU_THRESHOLD = float(os.getenv("EC2_CPU_IDLE_THRESHOLD", 5))  # percent

# ── Testing flag ─────────────────────────────────────────
# Set TESTING = True  → checks last 5 minutes  (for now)
# Set TESTING = False → checks last 7 days     (for production)
TESTING = True

if TESTING:
    LOOKBACK_MINUTES = 5
    PERIOD_SECONDS   = 60       # 1 data point per minute
    LOOKBACK_LABEL   = "5 minutes"
else:
    LOOKBACK_MINUTES = 7 * 24 * 60   # 7 days in minutes
    PERIOD_SECONDS   = 86400          # 1 data point per day
    LOOKBACK_LABEL   = "7 days"


def get_all_instances():
    """
    Returns a flat list of all running EC2 instances.
    """
    instances = []

    response = ec2.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )

    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:

            name = "unnamed"
            for tag in inst.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]

            instances.append({
                "instance_id":   inst["InstanceId"],
                "instance_type": inst["InstanceType"],
                "name":          name,
                "launch_time":   inst["LaunchTime"].strftime("%Y-%m-%d"),
            })

    return instances


def get_average_cpu(instance_id):
    """
    Gets average CPU % for the lookback window.
    In TESTING mode: last 5 minutes.
    In production mode: last 7 days.
    """
    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=LOOKBACK_MINUTES)

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=PERIOD_SECONDS,
        Statistics=["Average"]
    )

    data_points = response["Datapoints"]

    if not data_points:
        # No data points in this window = treat as idle
        return 0.0

    total = sum(dp["Average"] for dp in data_points)
    return round(total / len(data_points), 2)


def estimate_monthly_cost(instance_type):
    """
    Rough monthly cost estimate for ap-south-1 (Mumbai).
    """
    pricing = {
        "t2.micro":   0.0116,
        "t2.small":   0.023,
        "t2.medium":  0.0464,
        "t2.large":   0.0928,
        "t3.micro":   0.0104,
        "t3.small":   0.0208,
        "t3.medium":  0.0416,
        "t3.large":   0.0832,
        "t3.xlarge":  0.1664,
        "m5.large":   0.096,
        "m5.xlarge":  0.192,
        "m5.2xlarge": 0.384,
        "c5.large":   0.085,
        "c5.xlarge":  0.17,
        "r5.large":   0.126,
        "r5.xlarge":  0.252,
    }

    hourly  = pricing.get(instance_type, 0.05)
    monthly = hourly * 24 * 30
    return round(monthly, 2)


def collect_idle_ec2():
    """
    Main function — loops all running instances, checks CPU, flags idle ones.
    Returns a list of findings.
    """
    print("\n" + "=" * 55)
    print("  EC2 Idle Instance Detector")
    print(f"  Mode      : {'TESTING' if TESTING else 'PRODUCTION'}")
    print(f"  Threshold : CPU < {CPU_THRESHOLD}% over last {LOOKBACK_LABEL}")
    print(f"  Region    : {os.getenv('AWS_REGION')}")
    print("=" * 55)

    instances = get_all_instances()
    print(f"\nFound {len(instances)} running instance(s). Checking CPU...\n")

    findings = []

    for inst in instances:
        iid   = inst["instance_id"]
        itype = inst["instance_type"]
        name  = inst["name"]

        avg_cpu      = get_average_cpu(iid)
        monthly_cost = estimate_monthly_cost(itype)
        status       = "IDLE" if avg_cpu < CPU_THRESHOLD else "OK"

        print(f"  {iid}  |  {itype:12}  |  {name:20}  |  CPU: {avg_cpu:5.1f}%  |  {status}")

        if status == "IDLE":
            findings.append({
                "resource_type":   "EC2",
                "resource_id":     iid,
                "resource_name":   name,
                "instance_type":   itype,
                "avg_cpu_percent": avg_cpu,
                "lookback":        LOOKBACK_LABEL,
                "monthly_cost_usd": monthly_cost,
                "recommendation":  (
                    f"Instance idle for last {LOOKBACK_LABEL} (CPU < {CPU_THRESHOLD}%). "
                    f"Consider stopping or terminating. "
                    f"Estimated saving: ${monthly_cost}/month."
                ),
                "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })

    print(f"\nResult: {len(findings)} idle instance(s) found.")

    if findings:
        print("\nIdle instances:")
        for f in findings:
            print(f"  → {f['resource_id']} ({f['instance_type']}) "
                  f"| CPU: {f['avg_cpu_percent']}% "
                  f"| Saving: ${f['monthly_cost_usd']}/month")
            print(f"     {f['recommendation']}")

    return findings


# ── Run directly for testing ─────────────────────────────
if __name__ == "__main__":
    results = collect_idle_ec2()
    print(f"\nTotal findings returned: {len(results)}")