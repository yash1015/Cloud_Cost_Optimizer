import json
from datetime import datetime, timezone
from engine.waste_detector  import run_all_collectors
from engine.cost_calculator import calculate_savings, summarize


def build_report():
    """
    Master function — runs everything end to end:
    1. Runs all 4 collectors
    2. Calculates savings for each finding
    3. Sorts by impact
    4. Prints a clean final report
    5. Returns the full report as a dict
    """

    # Step 1 — collect all findings
    findings = run_all_collectors()

    # Step 2 — calculate and sort savings
    findings = calculate_savings(findings)

    # Step 3 — summarize
    summary  = summarize(findings)

    # Step 4 — build report dict
    report = {
        "generated_at":       datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "summary":            summary,
        "findings":           findings,
    }

    # Step 5 — print clean report
    print("\n")
    print("=" * 55)
    print("  FINOPS COST OPTIMIZATION REPORT")
    print(f"  Generated : {report['generated_at']}")
    print("=" * 55)

    print(f"\n  Total findings       : {summary['total_findings']}")
    print(f"  Total monthly waste  : ${summary['total_monthly_saving']}")
    print(f"  Total annual waste   : ${round(summary['total_monthly_saving'] * 12, 2)}")

    print("\n  Breakdown by service:")
    for rtype, data in summary["by_type"].items():
        if data["count"] > 0:
            print(f"    {rtype:<10} → {data['count']} finding(s)  |  "
                  f"${data['saving']}/month")

    print("\n  Top recommendations (highest saving first):")
    print(f"  {'#':<3} {'TYPE':<10} {'RESOURCE':<45} {'SAVING'}")
    print(f"  {'-'*3} {'-'*10} {'-'*45} {'-'*10}")

    for i, f in enumerate(findings[:10], 1):  # top 10
        rtype    = f.get("resource_type", "?")
        rid      = f.get("resource_id", "?")[:44]
        saving   = f.get("estimated_monthly_saving", 0)
        print(f"  {i:<3} {rtype:<10} {rid:<45} ${saving}/month")

    print("\n  Full recommendations:")
    for f in findings:
        rec = f.get("recommendation", "No recommendation")
        rid = f.get("resource_id", "?")
        print(f"\n  → [{f.get('resource_type')}] {rid}")
        print(f"     {rec}")

    print("\n" + "=" * 55)

    return report


if __name__ == "__main__":
    report = build_report()

    # Optionally save to a local JSON file for inspection
    with open("last_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print("\n  Report saved to last_report.json")