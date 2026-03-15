def get_monthly_cost(finding):
    """
    Extracts the monthly cost/saving from a finding.
    Different collectors store this under different keys —
    this normalizes them all into one number.
    """
    # EC2 and EBS store it as monthly_cost_usd
    if "monthly_cost_usd" in finding:
        return float(finding["monthly_cost_usd"])

    # S3 stores it as monthly_saving
    if "monthly_saving" in finding:
        return float(finding["monthly_saving"])

    # K8s doesn't have a direct dollar saving yet — we estimate
    # based on the CPU and memory that could be freed up
    if finding.get("resource_type") == "K8S_POD":
        cpu_waste_m  = finding.get("cpu_requested_m", 0)  - finding.get("cpu_used_m", 0)
        mem_waste_mb = finding.get("memory_requested_mb", 0) - finding.get("memory_used_mb", 0)

        # Rough estimate: $0.048 per vCPU/hour, $0.006 per GB/hour (on-demand)
        cpu_saving  = (cpu_waste_m / 1000) * 0.048 * 24 * 30
        mem_saving  = (mem_waste_mb / 1024) * 0.006 * 24 * 30
        return round(cpu_saving + mem_saving, 2)

    return 0.0


def calculate_savings(findings):
    """
    Takes the raw findings list and adds a normalized
    'estimated_monthly_saving' field to each one.
    Then sorts them highest saving first.
    """
    for finding in findings:
        finding["estimated_monthly_saving"] = get_monthly_cost(finding)

    # Sort by saving — biggest wins at the top
    findings.sort(key=lambda x: x["estimated_monthly_saving"], reverse=True)

    return findings


def summarize(findings):
    """
    Produces a summary dict with totals broken down by resource type.
    """
    summary = {
        "total_findings":       len(findings),
        "total_monthly_saving": 0,
        "by_type": {
            "EC2":     {"count": 0, "saving": 0},
            "EBS":     {"count": 0, "saving": 0},
            "S3":      {"count": 0, "saving": 0},
            "K8S_POD": {"count": 0, "saving": 0},
        }
    }

    for f in findings:
        rtype  = f.get("resource_type", "UNKNOWN")
        saving = f.get("estimated_monthly_saving", 0)

        summary["total_monthly_saving"] += saving

        if rtype in summary["by_type"]:
            summary["by_type"][rtype]["count"]  += 1
            summary["by_type"][rtype]["saving"] += saving

    # Round all saving values
    summary["total_monthly_saving"] = round(summary["total_monthly_saving"], 2)
    for rtype in summary["by_type"]:
        summary["by_type"][rtype]["saving"] = round(
            summary["by_type"][rtype]["saving"], 2
        )

    return summary


if __name__ == "__main__":
    # Quick test with dummy data
    test_findings = [
        {"resource_type": "EC2",     "monthly_cost_usd": 119.81},
        {"resource_type": "EBS",     "monthly_cost_usd": 11.50},
        {"resource_type": "S3",      "monthly_saving":   0.002},
        {"resource_type": "K8S_POD", "cpu_requested_m": 500,
         "cpu_used_m": 0, "memory_requested_mb": 512, "memory_used_mb": 4},
    ]

    results  = calculate_savings(test_findings)
    summary  = summarize(results)

    print("\nSorted findings (highest saving first):")
    for f in results:
        print(f"  {f['resource_type']:8} → ${f['estimated_monthly_saving']}/month")

    print(f"\nTotal monthly saving: ${summary['total_monthly_saving']}")
    print(f"Breakdown: {summary['by_type']}")