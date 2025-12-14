"""
返回：
    lane_df：每个 link_id 的 lane_count
    final_df：最终 demand 结果（66Demand）
"""

import requests
import pandas as pd
from tqdm import tqdm
import json
import re

# ------------------------------
#         配置常量
# ------------------------------
URL_INTERS = "http://172.30.11.143:8086/yzsfq/getIntersConns.do"
URL_ROAD = "http://172.30.11.143:8086/yzsfq/getRoadControlInfo.do"
URL_LANE = "http://172.30.11.143:8086/yzsfq/getLaneById.do"


# ------------------------------
# 角度 → 方向
# ------------------------------
def angle_to_direction(angle):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int(((angle + 22.5) % 360) // 45)
    return dirs[idx]


# ------------------------------
# 总入口函数
# ------------------------------
def run_pipeline(inters_ids, kafka_file_path):

    # ====================================================
    # 1. 获取 inLinks / outLinks
    # ====================================================
    inter_records = []

    for iid in tqdm(inters_ids, desc="Fetching intersection info"):
        try:
            resp = requests.post(f"{URL_INTERS}?intersId={iid}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("state") != 1 or "data" not in data:
                continue

            d = data["data"]
            juncId = d.get("juncId", iid)
            in_links = d.get("inLinks", [])
            out_links = d.get("outLinks", [])

            for link in in_links:
                inter_records.append({"intersId": juncId, "linkId": link, "linkType": "inLink"})

            for link in out_links:
                inter_records.append({"intersId": juncId, "linkId": link, "linkType": "outLink"})

        except:
            continue

    df_inter = pd.DataFrame(inter_records)

    # allowed only inLink
    allowed_links = set(df_inter.loc[df_inter["linkType"] == "inLink", "linkId"])

    # ====================================================
    # 2. 获取 roadId → lane 列表
    # ====================================================
    road_ids = df_inter["linkId"].unique().tolist()
    lane_records = []

    for rid in tqdm(road_ids, desc="Fetching road control info"):
        try:
            resp = requests.post(f"{URL_ROAD}?linkId={rid}", timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("state") == 1 and "data" in data:
                heading = data["data"].get("heading")
                lanes = data["data"].get("lanes", [])
                for lane in lanes:
                    lane_records.append({
                        "roadId": rid,
                        "heading": heading,
                        "laneId": lane.get("laneId"),
                        "turnInfo": lane.get("turnInfo")
                    })

        except:
            continue

    df_lane = pd.DataFrame(lane_records)
    df_lane["direction"] = df_lane["heading"].apply(angle_to_direction)

    # ====================================================
    # 3. 解析 Kafka txt
    # ====================================================
    records = []
    buffer = ""

    with open(kafka_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if "Received message:" in line and "value=" in line:
                match = re.search(r'value=({.*}),\s*partition', line)
                if match:
                    buffer = match.group(1)
                else:
                    buffer = line[line.find("value=") + 6:]
                    continue

            elif buffer:
                buffer += line

            # 若 JSON 括号匹配，解析
            if buffer and buffer.count("{") == buffer.count("}"):
                try:
                    data = json.loads(buffer)
                except:
                    buffer = ""
                    continue

                timestamp = data.get("timestamp")
                targets = data.get("targets", [])

                for t in targets:
                    records.append({
                        "longitude": t.get("longitude"),
                        "latitude": t.get("latitude"),
                        "uuid": t.get("uuid"),
                        "laneId": t.get("laneId"),
                        "turnInfo": t.get("turnInfo"),
                        "timestamp": timestamp
                    })

                buffer = ""

    data = pd.DataFrame(records)
    data = data[["timestamp", "uuid", "longitude", "latitude", "laneId", "turnInfo"]]

    # ====================================================
    # 4. laneId → link_id 映射
    # ====================================================
    unique_lanes = data["laneId"].dropna().astype(str).unique()
    link_records = []

    for lid in tqdm(unique_lanes, desc="Fetching lane->link_id"):
        try:
            r = requests.post(f"{URL_LANE}?laneId={lid}", timeout=10)
            j = r.json()
            if j.get("state") == 1:
                link_id = j["data"].get("link_id")
            else:
                link_id = None
        except:
            link_id = None
        link_records.append({"laneId": str(lid), "link_id": link_id})

    lane_link_df = pd.DataFrame(link_records).drop_duplicates()

    data["laneId"] = data["laneId"].astype(str)
    lane_link_df["laneId"] = lane_link_df["laneId"].astype(str)

    data = data.merge(lane_link_df, on="laneId", how="left")

    # 过滤只保留 allowed_links
    data["link_id"] = data["link_id"].astype(str)
    data = data[data["link_id"].isin(allowed_links)]

    # 转成北京时间
    data["time_beijing"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai")

    # ====================================================
    # 5. turnInfo → 文本
    # ====================================================
    turninfo_map = {
        1: "直", 2: "右", 3: "左", 4: "直右", 5: "直左", 6: "左右", 7: "左直右",
        8: "调头", 9: "调头右", 10: "调头左", 11: "调头直右", 12: "调头左直",
        13: "调头左右", 14: "调头左直右", 15: "斜右", 16: "斜左", 17: "直斜右",
        18: "直斜左", 19: "左斜右", 20: "右斜右", 21: "右斜左", 22: "左斜左",
        23: "调头斜右", 24: "调头斜左", 25: "斜左斜右", 26: "直右斜左",
        27: "直右斜右", 28: "直左斜左", 29: "直左斜右", 30: "调直",
        99: "其他",
    }

    turn_num = pd.to_numeric(data["turnInfo"], errors="coerce")
    data = data[turn_num.notna()]
    turn_num = pd.to_numeric(data["turnInfo"], errors="coerce")
    data = data[turn_num != 99]

    data["turn_name"] = turn_num.map(turninfo_map)
    data["direction"] = data["link_id"].astype(str) + "_" + data["turn_name"]

    # ====================================================
    # 6. 统计每 15min demand
    # ====================================================
    data["time_bin"] = data["time_beijing"].dt.floor("15min")

    first_appearance = (
        data.sort_values("time_bin")
        .drop_duplicates(subset="uuid", keep="first")
    )

    demand_df = (
        first_appearance
        .groupby(["time_bin", "turn_name", "laneId"])
        .agg(
            demand=("uuid", "count"),
            link_id=("link_id", "first"),
            direction=("direction", "first"),
        )
        .reset_index()
    )

    # 乘以 4 恢复到 1 小时流量
    demand_df["demand"] = demand_df["demand"] * 4

    turn_map = {
        "左": "Left Turn",
        "直": "Through",
        "右": "Right Turn",
        "直右": "Through",
        "调头左": "Left Turn",
    }
    demand_df["turn_action"] = demand_df["turn_name"].map(turn_map)

    # 合并 road 方向
    direction_map = df_lane[["roadId", "direction"]].drop_duplicates()
    demand_df = demand_df.drop(columns=["direction"])
    demand_df = demand_df.merge(
        direction_map,
        how="left",
        left_on="link_id",
        right_on="roadId"
    )

    # ====================================================
    # 7. 统计每 link 的 lane 数
    # ====================================================
    lane66_df = (
        demand_df.groupby(["link_id", "direction", "turn_action"])["laneId"]
        .nunique()
        .reset_index(name="lane_count")
    )

    # ====================================================
    # 8. 计算最终 demand（平滑）
    # ====================================================
    demand_sum = (
        demand_df.groupby(["time_bin", "link_id", "direction", "turn_action"])["demand"]
        .sum()
        .reset_index()
    )

    demand_sum["demand"] = demand_sum["demand"] * 12  # 1h
    demand_sum["smoothed_demand"] = demand_sum["demand"].rolling(window=3, center=True).mean()

    final_df = demand_sum.rename(
        columns={
            "direction": "Direction",
            "turn_action": "movement",
        }
    )

    return lane66_df, final_df


# ------------------------------
# END
# ------------------------------
