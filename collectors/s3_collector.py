import boto3
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ── AWS clients ───────────────────────────────────────────
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# ── Thresholds ────────────────────────────────────────────
DAYS_THRESHOLD = int(os.getenv("S3_DAYS_SINCE_LAST_ACCESS", 90))

# ── Testing flag ──────────────────────────────────────────
# TESTING = True  → flags objects older than 1 day   (for now)
# TESTING = False → flags objects older than 90 days  (production)
TESTING = True

if TESTING:
    DAYS_THRESHOLD  = 1
    LOOKBACK_LABEL  = "1 day (testing mode)"
else:
    LOOKBACK_LABEL  = f"{DAYS_THRESHOLD} days"

# ── S3 pricing per GB/month (ap-south-1) ─────────────────
STORAGE_PRICING = {
    "STANDARD":            0.023,
    "STANDARD_IA":         0.0125,
    "INTELLIGENT_TIERING": 0.023,
    "ONEZONE_IA":          0.01,
    "GLACIER_IR":          0.004,
    "GLACIER":             0.0036,
    "DEEP_ARCHIVE":        0.00099,
}

# Classes we want to flag — these are expensive for old data
EXPENSIVE_CLASSES = {"STANDARD", "INTELLIGENT_TIERING"}

# What we recommend moving to based on age
def recommended_class(days_old):
    if days_old > 365:
        return "DEEP_ARCHIVE"
    elif days_old > 180:
        return "GLACIER"
    elif days_old > 90:
        return "STANDARD_IA"
    else:
        return "STANDARD_IA"


def get_all_buckets():
    """Returns list of all S3 bucket names."""
    response = s3.list_buckets()
    return [b["Name"] for b in response["Buckets"]]


def check_lifecycle_policy(bucket_name):
    """
    Checks if a bucket already has a lifecycle rule set up.
    Returns True if lifecycle rules exist, False if not.
    """
    try:
        s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        return True
    except s3.exceptions.ClientError:
        # NoSuchLifecycleConfiguration error means no rules exist
        return False
    except Exception:
        return False


def get_bucket_objects(bucket_name):
    """
    Lists all objects in a bucket.
    Handles pagination — buckets can have thousands of objects,
    AWS returns them in pages of 1000.
    """
    objects = []

    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages     = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            for obj in page.get("Contents", []):
                objects.append(obj)

    except Exception as e:
        print(f"    Could not read bucket {bucket_name}: {e}")

    return objects


def analyze_bucket(bucket_name):
    """
    Looks at all objects in a bucket and finds ones that:
    1. Are in an expensive storage class (STANDARD or INTELLIGENT_TIERING)
    2. Haven't been modified in longer than DAYS_THRESHOLD

    Returns a summary dict for the bucket.
    """
    cutoff_date  = datetime.now(timezone.utc) - timedelta(days=DAYS_THRESHOLD)
    objects      = get_bucket_objects(bucket_name)
    has_lifecycle = check_lifecycle_policy(bucket_name)

    flagged_objects  = []
    total_size_bytes = 0
    total_waste_cost = 0

    for obj in objects:
        key            = obj["Key"]
        size_bytes     = obj["Size"]
        last_modified  = obj["LastModified"]
        storage_class  = obj.get("StorageClass", "STANDARD")

        days_old = (datetime.now(timezone.utc) - last_modified).days

        # Only flag if: expensive storage class AND old enough
        if storage_class in EXPENSIVE_CLASSES and last_modified < cutoff_date:
            size_gb      = size_bytes / (1024 ** 3)
            current_cost = size_gb * STORAGE_PRICING.get(storage_class, 0.023)
            rec_class    = recommended_class(days_old)
            new_cost     = size_gb * STORAGE_PRICING.get(rec_class, 0.0125)
            saving       = current_cost - new_cost

            total_size_bytes += size_bytes
            total_waste_cost += saving

            flagged_objects.append({
                "key":             key,
                "size_gb":         round(size_gb, 4),
                "days_old":        days_old,
                "storage_class":   storage_class,
                "recommended":     rec_class,
                "current_cost":    round(current_cost, 4),
                "saving_per_month": round(saving, 4),
            })

    return {
        "bucket_name":      bucket_name,
        "total_objects":    len(objects),
        "flagged_objects":  len(flagged_objects),
        "has_lifecycle":    has_lifecycle,
        "total_size_gb":    round(total_size_bytes / (1024 ** 3), 2),
        "monthly_saving":   round(total_waste_cost, 4),
        "objects":          flagged_objects,
    }


def collect_s3_waste():
    """
    Main function.
    Loops through all S3 buckets, analyzes each one,
    and returns findings for buckets with optimization opportunities.
    """
    print("\n" + "=" * 55)
    print("  S3 Storage Class Optimizer")
    print(f"  Mode      : {'TESTING' if TESTING else 'PRODUCTION'}")
    print(f"  Flagging  : Objects not modified in {LOOKBACK_LABEL}")
    print(f"  Region    : {os.getenv('AWS_REGION')}")
    print("=" * 55)

    buckets = get_all_buckets()
    print(f"\nFound {len(buckets)} bucket(s). Analyzing...\n")

    findings      = []
    total_saving  = 0

    for bucket_name in buckets:
        print(f"  Scanning: {bucket_name}")
        result = analyze_bucket(bucket_name)

        lifecycle_status = "has lifecycle rules" if result["has_lifecycle"] \
                           else "NO lifecycle rules"

        print(f"    Objects     : {result['total_objects']}")
        print(f"    Flagged     : {result['flagged_objects']} old objects in expensive storage")
        print(f"    Lifecycle   : {lifecycle_status}")
        print(f"    Est. saving : ${result['monthly_saving']}/month")
        print()

        if result["flagged_objects"] > 0 or not result["has_lifecycle"]:
            total_saving += result["monthly_saving"]

            recommendation_parts = []

            if result["flagged_objects"] > 0:
                recommendation_parts.append(
                    f"{result['flagged_objects']} object(s) can be moved to cheaper storage."
                )

            if not result["has_lifecycle"]:
                recommendation_parts.append(
                    "No lifecycle policy found — add one to automate future savings."
                )

            findings.append({
                "resource_type":    "S3",
                "resource_id":      bucket_name,
                "resource_name":    bucket_name,
                "total_objects":    result["total_objects"],
                "flagged_objects":  result["flagged_objects"],
                "total_size_gb":    result["total_size_gb"],
                "has_lifecycle":    result["has_lifecycle"],
                "monthly_saving":   result["monthly_saving"],
                "recommendation":   " ".join(recommendation_parts),
                "top_objects":      result["objects"][:5],  # top 5 flagged objects
                "detected_at":      datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })

    # ── Summary ───────────────────────────────────────────
    print("=" * 55)
    print(f"  Total buckets scanned  : {len(buckets)}")
    print(f"  Buckets with findings  : {len(findings)}")
    print(f"  Total potential saving : ${round(total_saving, 2)}/month")
    print("=" * 55)

    if findings:
        print("\nTop recommendations:")
        for f in findings:
            print(f"\n  Bucket : {f['resource_id']}")
            print(f"  Saving : ${f['monthly_saving']}/month")
            print(f"  Note   : {f['recommendation']}")
            if f["top_objects"]:
                print(f"  Sample flagged objects:")
                for obj in f["top_objects"]:
                    print(f"    → {obj['key']} | {obj['days_old']} days old | "
                          f"{obj['storage_class']} → {obj['recommended']} | "
                          f"saves ${obj['saving_per_month']}/month")

    return findings


# ── Run directly for testing ──────────────────────────────
if __name__ == "__main__":
    results = collect_s3_waste()
    print(f"\nTotal findings returned: {len(results)}")