import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.ec2_collector import collect_idle_ec2
from collectors.ebs_collector import collect_unattached_ebs
from collectors.s3_collector  import collect_s3_waste
from collectors.k8s_collector import collect_overprovisioned_pods


def run_all_collectors():
    """
    Runs all 4 collectors one by one.
    Returns a single list of every finding across all resource types.
    """
    print("\n" + "=" * 55)
    print("  FinOps Waste Detector — Running All Collectors")
    print("=" * 55)

    all_findings = []

    # ── EC2 ───────────────────────────────────────────────
    print("\n[1/4] Running EC2 collector...")
    try:
        ec2_findings = collect_idle_ec2()
        all_findings.extend(ec2_findings)
        print(f"  EC2 done → {len(ec2_findings)} finding(s)")
    except Exception as e:
        print(f"  EC2 collector failed: {e}")

    # ── EBS ───────────────────────────────────────────────
    print("\n[2/4] Running EBS collector...")
    try:
        ebs_findings = collect_unattached_ebs()
        all_findings.extend(ebs_findings)
        print(f"  EBS done → {len(ebs_findings)} finding(s)")
    except Exception as e:
        print(f"  EBS collector failed: {e}")

    # ── S3 ────────────────────────────────────────────────
    print("\n[3/4] Running S3 collector...")
    try:
        s3_findings = collect_s3_waste()
        all_findings.extend(s3_findings)
        print(f"  S3 done → {len(s3_findings)} finding(s)")
    except Exception as e:
        print(f"  S3 collector failed: {e}")

    # ── K8s ───────────────────────────────────────────────
    print("\n[4/4] Running K8s collector...")
    try:
        k8s_findings = collect_overprovisioned_pods()
        all_findings.extend(k8s_findings)
        print(f"  K8s done → {len(k8s_findings)} finding(s)")
    except Exception as e:
        print(f"  K8s collector failed: {e}")

    print(f"\nTotal findings across all collectors: {len(all_findings)}")
    return all_findings


if __name__ == "__main__":
    findings = run_all_collectors()