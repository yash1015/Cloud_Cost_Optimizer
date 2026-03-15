import os
import subprocess
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ── Thresholds from .env ──────────────────────────────────
CPU_THRESHOLD    = float(os.getenv("K8S_CPU_THRESHOLD", 30))     # percent
MEMORY_THRESHOLD = float(os.getenv("K8S_MEMORY_THRESHOLD", 30))  # percent

# ── Testing flag ──────────────────────────────────────────
# TESTING = True  → flags pods using less than 80% of requests (easier to trigger)
# TESTING = False → flags pods using less than 30% of requests (production)
TESTING = True

if TESTING:
    CPU_THRESHOLD    = 80
    MEMORY_THRESHOLD = 80
    MODE_LABEL       = "TESTING (threshold: < 80%)"
else:
    MODE_LABEL = f"PRODUCTION (threshold: < {CPU_THRESHOLD}%)"


def run_kubectl(command):
    """
    Runs a kubectl command and returns the output as a string.
    Example: run_kubectl("get pods --all-namespaces")
    """
    full_command = f"kubectl {command}"
    result = subprocess.run(
        full_command,
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"kubectl error: {result.stderr.strip()}")

    return result.stdout.strip()


def parse_cpu(value):
    """
    Converts kubectl CPU values to millicores (m).
    Examples:
      "500m"  → 500    (already in millicores)
      "1"     → 1000   (1 full core = 1000 millicores)
      "0"     → 0
    """
    if not value or value == "0":
        return 0
    if value.endswith("m"):
        return int(value[:-1])
    # No unit = whole cores
    return int(float(value) * 1000)


def parse_memory(value):
    """
    Converts kubectl memory values to MiB (Mi).
    Examples:
      "128Mi" → 128
      "1Gi"   → 1024
      "512Ki" → 0.5
    """
    if not value or value == "0":
        return 0
    if value.endswith("Ki"):
        return round(int(value[:-2]) / 1024, 2)
    if value.endswith("Mi"):
        return int(value[:-2])
    if value.endswith("Gi"):
        return int(value[:-2]) * 1024
    if value.endswith("M"):
        return int(value[:-1])
    if value.endswith("G"):
        return int(value[:-1]) * 1024
    return int(value)


def get_pod_requests():
    """
    Gets CPU and memory REQUESTS for all pods across all namespaces.
    Requests = what K8s reserves on the node for this pod.

    Uses kubectl get pods -o custom-columns to get clean output.
    Returns a dict: { "namespace/pod-name": {"cpu": 500, "memory": 256} }
    """
    output = run_kubectl(
        "get pods --all-namespaces "
        "-o custom-columns="
        "NAMESPACE:.metadata.namespace,"
        "NAME:.metadata.name,"
        "CPU_REQ:.spec.containers[0].resources.requests.cpu,"
        "MEM_REQ:.spec.containers[0].resources.requests.memory "
        "--no-headers"
    )

    requests = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue

        namespace = parts[0]
        name      = parts[1]
        cpu_req   = parts[2] if parts[2] != "<none>" else "0"
        mem_req   = parts[3] if parts[3] != "<none>" else "0"

        key = f"{namespace}/{name}"
        requests[key] = {
            "cpu_requested_m":    parse_cpu(cpu_req),
            "memory_requested_mb": parse_memory(mem_req),
        }

    return requests


def get_pod_usage():
    """
    Gets actual CPU and memory USAGE for all pods.
    Usage = what the pod is actually consuming right now.

    Uses kubectl top pods to get live metrics.
    Returns a dict: { "namespace/pod-name": {"cpu": 10, "memory": 50} }
    """
    output = run_kubectl("top pods --all-namespaces --no-headers")

    usage = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue

        namespace  = parts[0]
        name       = parts[1]
        cpu_use    = parts[2]
        memory_use = parts[3]

        key = f"{namespace}/{name}"
        usage[key] = {
            "cpu_used_m":    parse_cpu(cpu_use),
            "memory_used_mb": parse_memory(memory_use),
        }

    return usage


def collect_overprovisioned_pods():
    """
    Main function.
    Compares requested vs actual usage for every pod.
    Flags pods where usage is below the threshold.
    Returns a list of findings.
    """
    print("\n" + "=" * 55)
    print("  K8s Over-Provisioned Pod Detector")
    print(f"  Mode      : {MODE_LABEL}")
    print("=" * 55)

    # Step 1 — get requests and usage
    print("\nFetching pod resource requests...")
    try:
        requests = get_pod_requests()
    except Exception as e:
        print(f"  Error fetching requests: {e}")
        return []

    print(f"  Found {len(requests)} pod(s)")

    print("\nFetching live pod usage (kubectl top)...")
    try:
        usage = get_pod_usage()
    except Exception as e:
        print(f"  Error fetching usage: {e}")
        print("  Is the metrics server running? Try: kubectl top pods --all-namespaces")
        return []

    print(f"  Got usage for {len(usage)} pod(s)\n")

    findings  = []
    all_pods  = set(requests.keys()) | set(usage.keys())

    print(f"  {'POD':<55} {'CPU%':>6}  {'MEM%':>6}  STATUS")
    print(f"  {'-'*55} {'-----':>6}  {'-----':>6}  ------")

    for pod_key in sorted(all_pods):
        req = requests.get(pod_key, {})
        use = usage.get(pod_key, {})

        namespace, pod_name = pod_key.split("/", 1)

        cpu_req = req.get("cpu_requested_m", 0)
        mem_req = req.get("memory_requested_mb", 0)
        cpu_use = use.get("cpu_used_m", 0)
        mem_use = use.get("memory_used_mb", 0)

        # Calculate usage percentage — avoid division by zero
        cpu_pct = round((cpu_use / cpu_req) * 100, 1) if cpu_req > 0 else None
        mem_pct = round((mem_use / mem_req) * 100, 1) if mem_req > 0 else None

        cpu_label = f"{cpu_pct}%" if cpu_pct is not None else "no req"
        mem_label = f"{mem_pct}%" if mem_pct is not None else "no req"

        # A pod is over-provisioned if EITHER cpu OR memory is below threshold
        cpu_over = cpu_pct is not None and cpu_pct < CPU_THRESHOLD
        mem_over = mem_pct is not None and mem_pct < MEMORY_THRESHOLD
        is_over  = cpu_over or mem_over

        status = "OVER-PROVISIONED" if is_over else "OK"

        print(f"  {pod_key:<55} {cpu_label:>6}  {mem_label:>6}  {status}")

        if is_over:
            issues = []
            if cpu_over:
                issues.append(
                    f"CPU using {cpu_pct}% of requested {cpu_req}m "
                    f"(suggest reducing to {max(10, cpu_use * 2)}m)"
                )
            if mem_over:
                issues.append(
                    f"Memory using {mem_pct}% of requested {mem_req}Mi "
                    f"(suggest reducing to {max(64, mem_use * 2)}Mi)"
                )

            findings.append({
                "resource_type":        "K8S_POD",
                "resource_id":          pod_key,
                "resource_name":        pod_name,
                "namespace":            namespace,
                "cpu_requested_m":      cpu_req,
                "cpu_used_m":           cpu_use,
                "cpu_percent":          cpu_pct,
                "memory_requested_mb":  mem_req,
                "memory_used_mb":       mem_use,
                "memory_percent":       mem_pct,
                "recommendation":       " | ".join(issues),
                "detected_at":          datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })

    # ── Summary ───────────────────────────────────────────
    print(f"\nResult: {len(findings)} over-provisioned pod(s) found out of {len(all_pods)} total.\n")

    if findings:
        print("Recommendations:")
        for f in findings:
            print(f"\n  → {f['resource_id']}")
            print(f"     {f['recommendation']}")

    return findings


# ── Run directly for testing ──────────────────────────────
if __name__ == "__main__":
    results = collect_overprovisioned_pods()
    print(f"\nTotal findings returned: {len(results)}")