import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

###########################################################
# 1. 计算 Backlog + Utilized Supply
###########################################################
def compute_utilized_supply_with_backlog(df):
    df = df.sort_values("time_bin").copy()
    unsatisfied = 0
    utilized_list = []
    backlog_list = []

    for _, row in df.iterrows():
        total_demand = row["smoothed_demand"] + unsatisfied
        capacity = row["cleaned_capacity"] * 1.5

        utilized = min(capacity, total_demand)
        unsatisfied = max(0, total_demand - capacity)

        utilized_list.append(utilized)
        backlog_list.append(unsatisfied)

    df["utilized_supply"] = utilized_list
    df["unsatisfied_demand"] = backlog_list
    return df


###########################################################
# 2. 计算韧性指标
###########################################################
def compute_resilience_metrics(df):
    df = df.copy()
    df = df.sort_values("time_bin").reset_index(drop=True)
    df["gap"] = df["smoothed_demand"] - df["utilized_supply"]

    baseline_df = df[df["time_bin"].dt.hour == 5]
    baseline = baseline_df["smoothed_demand"].mean()

    gap_series = df["gap"] > 0
    if not gap_series.any():
        return {
            "PR_preparation": 0,
            "OR_operational": 0,
            "DR_design": 0,
            "RR_recovery": 0,
            "General_Resilience": 0,
        }

    imbalance_index = (df['utilized_supply'] < df['smoothed_demand']).idxmax()
    t1_index = max(0, imbalance_index - 1)
    t1_row = df.loc[t1_index]

    PR_preparation = t1_row["smoothed_demand"] - baseline

    t2_index = t1_index
    for i in range(t1_index + 1, len(df)):
        if df["utilized_supply"].iloc[i] < df["utilized_supply"].iloc[i - 1]:
            break
        t2_index = df.index[i - 1]

    designed_supply = df.loc[t2_index, "utilized_supply"]
    subset = df.loc[t1_index:t2_index]
    designed_demand = np.minimum(subset["smoothed_demand"], designed_supply)
    OR_operational = np.sum(designed_demand - subset["utilized_supply"])

    seg1 = df.loc[:t2_index + 1]
    gap1 = (seg1["smoothed_demand"] - designed_supply).clip(lower=0)
    dr1 = gap1.sum()
    len1 = (gap1 > 0).sum()

    seg2 = df.loc[t2_index + 2:]
    gap2 = (seg2["smoothed_demand"] - seg2["utilized_supply"]).clip(lower=0)
    dr2 = gap2.sum()
    len2 = (gap2 > 0).sum()

    total_time = len1 + len2
    DR_design = (dr1 + dr2) / total_time if total_time > 0 else 0

    recover = df[df["utilized_supply"] > df["smoothed_demand"]]
    rr_gap = (recover["utilized_supply"] - recover["smoothed_demand"]).sum()
    rr_time = len(recover)
    RR_recovery = rr_gap / rr_time if rr_time > 0 else 0

    General_Resilience = df["gap"].clip(lower=0).sum()

    return {
        "PR_preparation": PR_preparation,
        "OR_operational": OR_operational,
        "DR_design": DR_design,
        "RR_recovery": RR_recovery,
        "General_Resilience": General_Resilience,
    }


###########################################################
# 3. 总流程函数
###########################################################
def run_resilience_analysis(capacity_df, demand_df, start_hour, end_hour):
    """
    输入：
        - capacity_df（DataFrame）
        - demand_df（DataFrame）
        - 时间窗 start_hour-end_hour（如6, 10）

    输出：
        - 绘图 + 返回韧性指标 DataFrame
    """

    # 统一日期格式
    capacity_df["time_bin"] = pd.to_datetime(capacity_df["time_bin"], utc=True)\
        .dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)

    demand_df["time_bin"] = pd.to_datetime(demand_df["time_bin"]).dt.tz_localize(None)
    demand_df = demand_df.rename(columns={"Direction": "direction"})

    # 合并
    supply_demand = pd.merge(
        demand_df,
        capacity_df,
        how="inner",
        on=["time_bin", "direction", "movement"]
    )
    supply_demand["recalculated_capacity"] = supply_demand["cleaned_capacity"]

    # backlog 计算
    supply_demand = (
        supply_demand
        .sort_values("time_bin")
        .groupby(["direction", "movement"], group_keys=False)
        .apply(compute_utilized_supply_with_backlog)
    )

    # 过滤时间窗
    filtered = supply_demand[
        supply_demand["time_bin"].dt.hour.between(start_hour, end_hour)
    ]

    ###########################################################
    # 绘图（供需对比）
    ###########################################################
    groups = filtered.groupby(["direction", "movement"])
    group_keys = list(groups.groups.keys())
    n = len(group_keys)

    ncols = 4
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 5, nrows * 3), sharex=True)
    axes = axes.flatten()

    ymax = filtered[["smoothed_demand", "utilized_supply"]].max().max()
    ymax = math.ceil(ymax / 100.0) * 100

    legend_handles = None

    for idx, ((direction, movement), df) in enumerate(groups):
        ax = axes[idx]
        df = df.sort_values("time_bin")

        line1, = ax.plot(df["time_bin"], df["smoothed_demand"], label="Smoothed Demand", marker='o')
        line3, = ax.plot(df["time_bin"], df["utilized_supply"], label="Utilized Supply", linestyle=':', marker='.')

        ax.set_title(f"{direction} - {movement}")
        ax.grid(True)
        ax.tick_params(axis='x', rotation=45)
        ax.set_ylim(0, ymax)

        if legend_handles is None:
            legend_handles = [line1, line3]

    for j in range(idx + 1, len(axes)):
        fig.delaxes(axes[j])

    fig.legend(handles=legend_handles, loc="lower center", ncol=3,
               bbox_to_anchor=(0.5, -0.01), frameon=False)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.suptitle("Supply vs Demand by Direction & Movement", fontsize=16)
    plt.show()

    ###########################################################
    # 计算韧性指标
    ###########################################################
    metrics_results = []
    for (direction, movement), group_df in filtered.groupby(['direction', 'movement']):
        metrics = compute_resilience_metrics(group_df)
        metrics.update({'direction': direction, 'movement': movement})
        metrics_results.append(metrics)

    metrics_df = pd.DataFrame(metrics_results)
    return metrics_df


###########################################################
# 主程序示例
###########################################################
if __name__ == "__main__":
    cap = pd.read_csv("117Capacity.csv")
    dem = pd.read_csv("117Demand.csv")

    metrics = run_resilience_analysis(cap, dem, start_hour=21, end_hour=24)
    print(metrics)
    metrics.to_csv("ResilienceResults.csv", index=False)
