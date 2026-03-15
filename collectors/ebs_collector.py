import boto3
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ── AWS client ───────────────────────────────────────────
ec2 = boto3.client(
    "ec2",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)


def get_volume_name(volume):
    """
    Extracts the Name tag from a volume.
    If no Name tag exists, returns 'unnamed'.
    """
    for tag in volume.get("Tags", []):
        if tag["Key"] == "Name":
            return tag["Value"]
    return "unnamed"


def estimate_monthly_cost(size_gb, volume_type):
    """
    Estimates monthly cost of an EBS volume.
    Pricing is for ap-south-1 (Mumbai) per GB/month.

    Common volume types:
      gp2 → general purpose SSD (old default)
      gp3 → general purpose SSD (new, cheaper)
      io1 → high performance SSD
      io2 → high performance SSD (newer)
      st1 → throughput optimized HDD
      sc1 → cold HDD (cheapest)
    """
    price_per_gb = {
        "gp2": 0.114,
        "gp3": 0.096,
        "io1": 0.131,
        "io2": 0.131,
        "st1": 0.051,
        "sc1": 0.029,
    }

    rate    = price_per_gb.get(volume_type, 0.10)  # default if type unknown
    monthly = size_gb * rate
    return round(monthly, 2)


def collect_unattached_ebs():
    """
    Main function.
    Finds all EBS volumes in 'available' state — meaning not attached
    to any EC2 instance. These are pure waste.
    Returns a list of findings.
    """
    print("\n" + "=" * 55)
    print("  EBS Unattached Volume Detector")
    print(f"  Region : {os.getenv('AWS_REGION')}")
    print("=" * 55)

    # 'available' means the volume exists but is not attached to anything
    response = ec2.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )

    volumes = response["Volumes"]
    print(f"\nFound {len(volumes)} unattached volume(s).\n")

    findings = []
    total_waste = 0

    for vol in volumes:
        vol_id      = vol["VolumeId"]
        vol_type    = vol["VolumeType"]
        size_gb     = vol["Size"]
        name        = get_volume_name(vol)
        create_time = vol["CreateTime"].strftime("%Y-%m-%d")
        monthly_cost = estimate_monthly_cost(size_gb, vol_type)
        total_waste += monthly_cost

        print(f"  {vol_id}  |  {vol_type:4}  |  {size_gb:4} GB  |  "
              f"{name:20}  |  Created: {create_time}  |  "
              f"${monthly_cost}/month")

        findings.append({
            "resource_type":    "EBS",
            "resource_id":      vol_id,
            "resource_name":    name,
            "volume_type":      vol_type,
            "size_gb":          size_gb,
            "created_on":       create_time,
            "monthly_cost_usd": monthly_cost,
            "recommendation": (
                f"Volume is unattached (status: available). "
                f"Not connected to any instance since creation. "
                f"Delete it to save ${monthly_cost}/month."
            ),
            "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        })

    # ── Summary ──────────────────────────────────────────
    print(f"\nTotal monthly waste from unattached volumes: ${round(total_waste, 2)}")

    if findings:
        print("\nRecommendations:")
        for f in findings:
            print(f"  → {f['resource_id']} ({f['volume_type']}, {f['size_gb']} GB) "
                  f"| ${f['monthly_cost_usd']}/month")
            print(f"     {f['recommendation']}")
    else:
        print("\nNo unattached EBS volumes found. Nothing to clean up.")

    return findings


# ── Run directly for testing ─────────────────────────────
if __name__ == "__main__":
    results = collect_unattached_ebs()
    print(f"\nTotal findings returned: {len(results)}")