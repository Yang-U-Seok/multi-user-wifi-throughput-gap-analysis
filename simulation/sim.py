import argparse
import csv
import os
import random
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class WifiDCFParams:
    # DCF contention window
    cw_min: int = 16
    cw_max: int = 1024

    # timing (seconds)
    slot_time: float = 9e-6
    difs: float = 34e-6
    sifs: float = 16e-6

    # ACK / PHY overhead (very simplified)
    mac_ack_time: float = 30e-6          # "ACK" or "Block ACK" time (simplified fixed)
    phy_overhead: float = 80e-6          # preamble + headers (simplified fixed)

    # PHY rate (Mbps)
    r_phy_mbps: float = 150.0

    # Base payload sizes
    ap_payload_bytes: int = 1500         # one MSDU size
    sta_ack_bytes: int = 64              # small uplink TCP ACK-like frame

    # Aggregation factor (how many 1500B frames AP packs per TXOP-like event)
    agg_k: int = 8


def jains_fairness(x: List[float]) -> float:
    if not x:
        return 0.0
    s = sum(x)
    ss = sum(v * v for v in x)
    if ss == 0:
        return 0.0
    return (s * s) / (len(x) * ss)


def airtime_for_bits(bits: int, p: WifiDCFParams) -> float:
    r_bps = p.r_phy_mbps * 1e6
    return p.phy_overhead + (bits / r_bps)


def simulate_ap_downlink_with_aggregation_one_trial(
    n_sta: int,
    sim_time_s: float,
    p: WifiDCFParams,
    seed: int,
) -> Dict[str, float]:
    """
    AP downlink + STA uplink ACK 경쟁 모델 + AP aggregation(A-MPDU 근사)

    노드:
      - node 0: AP (downlink, payload = 1500B * agg_k 를 1회 전송에 실어보냄)
      - node 1..n: STA들 (uplink small ACK-like frame, saturation)

    집계:
      - downlink throughput: AP가 전달한 "유효 payload bits"만 합산
    """
    rnd = random.Random(seed)

    n_nodes = 1 + n_sta
    cw = [p.cw_min] * n_nodes
    backoff = [rnd.randrange(0, cw[i]) for i in range(n_nodes)]

    # Frame bits per node
    ap_payload_bits = p.ap_payload_bytes * 8
    ap_agg_payload_bits = ap_payload_bits * p.agg_k  # aggregated payload carried in one AP success

    sta_ack_bits = p.sta_ack_bytes * 8

    # Airtime per node for its "DATA-like" transmission
    # AP: aggregated payload bits
    t_data_ap = airtime_for_bits(ap_agg_payload_bits, p)
    # STA: small ACK-like frame bits
    t_data_sta = airtime_for_bits(sta_ack_bits, p)

    # Success durations (simplified)
    # AP success: DIFS + DATA(agg) + SIFS + BlockACK(=mac_ack_time)
    t_succ_ap = p.difs + t_data_ap + p.sifs + p.mac_ack_time
    # STA success: DIFS + DATA(small) + SIFS + ACK
    t_succ_sta = p.difs + t_data_sta + p.sifs + p.mac_ack_time

    # Collision durations: assume the longest transmitter dominates the busy time
    t_col_ap = p.difs + t_data_ap
    t_col_sta = p.difs + t_data_sta

    time = 0.0
    collisions = 0
    successes = 0

    ap_delivered_bits = 0
    per_node_success_bits = [0.0] * n_nodes  # fairness 참고용

    while time < sim_time_s:
        m = min(backoff)
        time += m * p.slot_time
        backoff = [b - m for b in backoff]

        tx = [i for i, b in enumerate(backoff) if b == 0]
        k = len(tx)

        if k == 1:
            i = tx[0]
            successes += 1

            if i == 0:
                # AP success
                time += t_succ_ap
                ap_delivered_bits += ap_agg_payload_bits
                per_node_success_bits[i] += ap_agg_payload_bits
            else:
                # STA success (uplink small frame)
                time += t_succ_sta
                per_node_success_bits[i] += sta_ack_bits

            # CW reset
            cw[i] = p.cw_min
            backoff[i] = rnd.randrange(0, cw[i])

        elif k >= 2:
            collisions += 1

            # collision time: longest among colliders (AP agg frame is usually longest)
            has_ap = (0 in tx)
            time += (t_col_ap if has_ap else t_col_sta)

            for i in tx:
                cw[i] = min(p.cw_max, cw[i] * 2)
                backoff[i] = rnd.randrange(0, cw[i])

        if time >= sim_time_s:
            break

    downlink_mbps = (ap_delivered_bits / time) / 1e6 if time > 0 else 0.0
    eta = downlink_mbps / p.r_phy_mbps if p.r_phy_mbps > 0 else 0.0
    collision_rate = collisions / (collisions + successes) if (collisions + successes) > 0 else 0.0

    per_node_rate = [(b / time) for b in per_node_success_bits] if time > 0 else [0.0] * n_nodes
    fairness = jains_fairness(per_node_rate)

    return {
        "downlink_mbps": downlink_mbps,
        "eta": eta,
        "collision_rate": collision_rate,
        "jain_fairness": fairness,
        "elapsed_s": time,
    }


def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_min", type=int, default=1)
    ap.add_argument("--n_max", type=int, default=3)
    ap.add_argument("--sim_time", type=float, default=20.0)
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)

    ap.add_argument("--r_phy_mbps", type=float, default=150.0)
    ap.add_argument("--ap_payload_bytes", type=int, default=1500)
    ap.add_argument("--sta_ack_bytes", type=int, default=64)
    ap.add_argument("--agg_k", type=int, default=8, help="aggregation factor (e.g., 4,8,16,32)")
    ap.add_argument("--out_csv", type=str, default="outputs/sim_ap_downlink_agg.csv")
    args = ap.parse_args()

    p = WifiDCFParams(
        r_phy_mbps=args.r_phy_mbps,
        ap_payload_bytes=args.ap_payload_bytes,
        sta_ack_bytes=args.sta_ack_bytes,
        agg_k=args.agg_k,
    )

    rows: List[Dict[str, float]] = []
    for n in range(args.n_min, args.n_max + 1):
        thrs, etas, cols, fairs = [], [], [], []

        for t in range(args.trials):
            r = simulate_ap_downlink_with_aggregation_one_trial(
                n_sta=n,
                sim_time_s=args.sim_time,
                p=p,
                seed=args.seed + 1000 * n + t,
            )
            thrs.append(r["downlink_mbps"])
            etas.append(r["eta"])
            cols.append(r["collision_rate"])
            fairs.append(r["jain_fairness"])

        thr_mean = mean(thrs)
        rows.append({
            "n": n,
            "downlink_mbps_mean": thr_mean,
            "per_user_mbps_mean": thr_mean / n,
            "eta_mean": mean(etas),
            "collision_rate_mean": mean(cols),
            "jain_fairness_mean": mean(fairs),
            "r_phy_mbps": p.r_phy_mbps,
            "ap_payload_bytes": p.ap_payload_bytes,
            "sta_ack_bytes": p.sta_ack_bytes,
            "agg_k": p.agg_k,
            "trials": args.trials,
            "sim_time_s": args.sim_time,
        })

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"[OK] wrote: {args.out_csv}")
    for r in rows[:5]:
        print(r)


if __name__ == "__main__":
    main()