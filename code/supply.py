"""
获取信号灯信息 → 相位名称映射 → 信号分析 → 计算流量 → 清洗产能 → 返回最终 DataFrame
"""

import requests
import pandas as pd
from TFlight import SignalAnalyzer, calculate_green_occ


# ============================================================
# 1. 获取交通灯与相位映射
# ============================================================
def fetch_phase_mapping(base_url: str, cross_id: str, phase_map_path: str):
    """
    调用接口，获取 phaseId-road_id 关系，
    并与 phase_map.xlsx 做字段补充 (PhaseName, Angle)
    """

    resp = requests.post(f"{base_url}?crossId={cross_id}", timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("state") != 1:
        raise ValueError(f"接口 state != 1: {data}")

    # 整理 JSON
    records = [
        {
            "crossId": cross_id,
            "phaseId": item.get("phaseId"),
            "road_id": item.get("road_id")
        }
        for item in data.get("data", [])
    ]

    mapping_df = pd.DataFrame(records).drop_duplicates()

    # 合并 phase_map.xlsx
    phase_map = pd.read_excel(phase_map_path)
    phase_map["PhaseId"] = phase_map["PhaseId"].astype(int)
    mapping_df["phaseId"] = mapping_df["phaseId"].astype(int)

    merged = mapping_df.merge(
        phase_map,
        left_on="phaseId",
        right_on="PhaseId",
        how="left"
    )
    merged = merged[["phaseId", "road_id", "PhaseName", "Angle"]]
    return merged, phase_map


# ============================================================
# 2. 信号数据分析
# ============================================================
def analyze_signal(signal_file: str, phase_ids, phase_map, green_output_path: str):
    analyzer = SignalAnalyzer(
        file_path=signal_file,
        target_phase_ids=phase_ids
    )
    results = analyzer.run()

    # 使用外部传入的路径
    _, csv_rows = calculate_green_occ(results, output_path=green_output_path)

    df = pd.DataFrame(csv_rows)
    df["phaseId"] = df["phaseId"].astype(int)

    df = df.merge(
        phase_map,
        left_on="phaseId",
        right_on="PhaseId",
        how="left"
    )
    return df



# ============================================================
# 3. 方向/动作字段解析、15min 聚合
# ============================================================
def aggregate_to_15min(signal_df):
    df = signal_df.set_index("startTime")

    # 拆方向
    df[['direction_cn', 'movement_cn']] = df['PhaseName'].str.split('-', expand=True)

    direction_map = {
        '东': 'E', '西': 'W', '南': 'S', '北': 'N',
        '东北': 'NE', '东南': 'SE', '西北': 'NW', '西南': 'SW'
    }
    df['direction'] = df['direction_cn'].map(direction_map)

    movement_map = {
        '左转': 'Left Turn',
        '右转': 'Right Turn',
        '直行': 'Through',
        '机动车信号灯': 'Through'
    }
    df['movement'] = df['movement_cn'].map(movement_map)

    result = (
        df.groupby(['Angle', 'phaseId'])
          .resample("15T")
          .agg({
              'green_ratio': 'mean',
              'cycle_time_sec': 'mean',
              'regionId': 'first',
              'nodeId': 'first',
              'PhaseName': 'first',
              'direction': 'first',
              'movement': 'first'
          })
          .reset_index()
    )
    return result


# ============================================================
# 4. 车道数匹配 + cleaned_capacity
# ============================================================
def match_lane_and_capacity(result_df, lane_csv_path):
    lane_df = pd.read_csv(lane_csv_path)
    lane_df = lane_df.rename(columns={'turn_action': 'movement'})

    # 初次精确匹配
    merged = result_df.merge(
        lane_df[['direction', 'movement', 'lane_count']],
        on=['direction', 'movement'],
        how='left'
    )

    # 建立方向群组用于模糊匹配
    direction_groups = {
        "N": ["N", "NE", "NW"],
        "S": ["S", "SE", "SW"],
        "E": ["E", "NE", "SE"],
        "W": ["W", "NW", "SW"]
    }

    # 未匹配的数据
    unmatched = merged[merged['lane_count'].isna()].copy()

    # lane_df 中未被使用的行
    used_mask = merged['lane_count'].notna()
    used_pairs = set(zip(merged.loc[used_mask, 'direction'], merged.loc[used_mask, 'movement']))

    lane_remaining = lane_df[
        ~lane_df.apply(lambda r: (r.direction, r.movement) in used_pairs, axis=1)
    ]

    # 放宽匹配函数
    def relaxed_match(row):
        base_dir = row['direction']
        movement = row['movement']
        possible_dirs = direction_groups.get(base_dir, [])

        candidates = lane_remaining[
            (lane_remaining['direction'].isin(possible_dirs)) &
            (lane_remaining['movement'] == movement)
        ]
        if len(candidates) > 0:
            return candidates.iloc[0]['lane_count']
        return None

    # 应用放宽匹配
    merged.loc[merged['lane_count'].isna(), 'lane_count'] = unmatched.apply(relaxed_match, axis=1)

    # 计算 cleaned_capacity
    merged['cleaned_capacity'] = merged['green_ratio'] * merged['lane_count'] * 1200

    merged = merged.rename(columns={'startTime': 'time_bin'})
    return merged


# ============================================================
# 主函数，返回最终 dataframe
# ============================================================
def run_capacity_pipeline(
    base_url: str,
    cross_id: str,
    phase_map_path: str,
    signal_file: str,
    lane_csv_path: str,
    green_output_path: str = "temp_green_ratio_output.csv"   
):

    mapping, phase_map = fetch_phase_mapping(base_url, cross_id, phase_map_path)

    signal_df = analyze_signal(
    signal_file,
    mapping['phaseId'].tolist(),
    phase_map,
    green_output_path     # ★ 传入
)


    agg_df = aggregate_to_15min(signal_df)

    final_df = match_lane_and_capacity(agg_df, lane_csv_path)

    return final_df
