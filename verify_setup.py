import boto3
import os
from dotenv import load_dotenv

# This line reads your .env file and loads all the values into the environment
load_dotenv()

def verify_aws_connection():
    print("Checking AWS connection...")

    # Create a connection to AWS using your credentials from .env
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

    # Try to list your EC2 instances — if this works, credentials are correct
    response = ec2.describe_instances()
    instance_count = sum(
        len(r["Instances"]) for r in response["Reservations"]
    )
    print(f"  AWS connection successful!")
    print(f"  Found {instance_count} EC2 instance(s) in {os.getenv('AWS_REGION')}")


def verify_s3_connection():
    print("\nChecking S3 connection...")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

    response = s3.list_buckets()
    bucket_count = len(response["Buckets"])
    print(f"  S3 connection successful!")
    print(f"  Found {bucket_count} S3 bucket(s)")


def verify_env_variables():
    print("Checking .env variables...")

    required = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "EC2_CPU_IDLE_THRESHOLD",
        "EC2_IDLE_DAYS",
        "K8S_CPU_THRESHOLD",
        "K8S_MEMORY_THRESHOLD",
        "S3_DAYS_SINCE_LAST_ACCESS"
    ]

    all_good = True
    for var in required:
        value = os.getenv(var)
        if value:
            print(f"  {var} = OK")
        else:
            print(f"  {var} = MISSING!")
            all_good = False

    return all_good


if __name__ == "__main__":
    print("=" * 40)
    print("  FinOps Tool — Setup Verification")
    print("=" * 40)

    env_ok = verify_env_variables()

    if env_ok:
        verify_aws_connection()
        verify_s3_connection()
        print("\nAll checks passed! Ready to build.")
    else:
        print("\nFix the missing variables in .env first.")