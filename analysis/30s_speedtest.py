import subprocess

TSHARK_PATH = r"C:\Program Files\Wireshark\tshark.exe"  
def measured_throughput_mbps(pcap_path, display_filter=""):
    cmd = [
        TSHARK_PATH,
        "-r", pcap_path,
        "-T", "fields",
        "-E", "separator=,",
        "-e", "frame.time_epoch",
        "-e", "frame.len",
    ]
    if display_filter:
        cmd += ["-Y", display_filter]

    out = subprocess.check_output(cmd, text=True, errors="ignore")

    t_min = None
    t_max = None
    total_bytes = 0.0
    pkt_cnt = 0

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            t = float(parts[0])
            ln = float(parts[1])
        except ValueError:
            continue

        pkt_cnt += 1
        total_bytes += ln
        if t_min is None or t < t_min:
            t_min = t
        if t_max is None or t > t_max:
            t_max = t

    if pkt_cnt == 0 or t_min is None or t_max is None:
        raise ValueError("No packets parsed. pcap_path or display_filter 확인해봐.")

    delta_t = t_max - t_min
    if delta_t <= 0:
        raise ValueError(f"delta_t가 이상함: {delta_t}. 캡처 시간이 너무 짧을 수 있음.")

    t_measured_mbps = (total_bytes * 8.0) / (delta_t * 1e6)

    return {
        "packets": pkt_cnt,
        "total_bytes": total_bytes,
        "delta_t_sec": delta_t,
        "t_measured_mbps": t_measured_mbps,
    }

if __name__ == "__main__":
    res = measured_throughput_mbps(
        pcap_path=r"C:\Users\yanguseok\Documents\user1_speedtest_30s.pcapng",
        display_filter="ip.addr==192.168.0.9"
    )
    print(res)
