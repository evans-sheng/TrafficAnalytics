import json
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.notebook import tqdm  


# === 配置部分 ===
FILE_PATH = "spat_323_20250307000000_20250308000000.txt"
MAX_SEARCH = 5000
TIME_THRESHOLD_MS = 1000

LIGHT_MAP = {1: "错误", 2: "错误", 4: "错误", 6: "错误", 8: "错误", 3: "红灯", 5: "绿灯", 7: "黄灯"}

# === 数据提取与过滤 ===
def extract_signal_timing(line):
    data = json.loads(line)
    recs = []
    for msg in data.get("message", []):
        for entry in msg.get("data", []):
            for inter in entry.get("intersections", []):
                r, n = inter["regionId"], inter["nodeId"]
                for ph in inter.get("phases", []):
                    pid = ph["phaseId"]
                    for st in ph.get("phaseStates", []):
                        color = LIGHT_MAP.get(st["light"], f"未知({st['light']})")
                        s, e = st["startUTCTime"], st["likelyEndUTCTime"]
                        recs.append({
                            "regionId": r,
                            "nodeId": n,
                            "phaseId": pid,
                            "light": color,
                            "st_ms": s,
                            "end_ms": e,
                            "startTime": datetime.utcfromtimestamp(s / 1000),
                            "endTime": datetime.utcfromtimestamp(e / 1000)
                        })
    return recs

# === 查找逻辑 ===
def find_sequence_for_group(entries):
    """
    在分组数据中查找完整的信号灯变化序列（红->绿->黄或红->绿）
    
    参数:
        entries: 同一分组的所有信号灯记录
        
    返回:
        按时间顺序排列的完整信号周期序列
    """
    entries = sorted(entries, key=lambda x: x['st_ms'])


    # 判断是否存在黄灯记录，决定信号周期模式
    has_y = any(e['light'] == '黄灯' for e in entries)
    cycle = ['红灯', '绿灯', '黄灯'] if has_y else ['红灯', '绿灯']

    results = []
    start_pos = 0
    n = len(entries)

    while True:
        # 查找下一个红灯记录作为序列起点
        idx = next((i for i in range(start_pos, n) if entries[i]['light'] == '红灯'), None)
        if idx is None:  # 没有更多红灯记录则结束
            break
            
        cur = entries[idx]  # 当前红灯记录
        temp_seq = [cur]    # 临时存储当前找到的序列
        last_end = cur['end_ms']  # 记录当前状态的结束时间
        
        # 计算周期中下一个期望的状态索引
        next_cycle_idx = (cycle.index('红灯') + 1) % len(cycle)
        found_next = False  # 标记是否找到完整序列

        while True:
            target = cycle[next_cycle_idx]  # 期望的下一个状态
            # 在后续记录中搜索（限制搜索范围）
            window = entries[idx + 1: idx + 1 + MAX_SEARCH]
            
            # 查找匹配的下一个状态记录（时间连续性检查）
            match = next((e for e in window if 
                          e['light'] == target and 
                          abs(e['st_ms'] - last_end) < TIME_THRESHOLD_MS), None)
            
            if not match:  # 未找到匹配则终止当前序列
                break
                
            # 找到匹配则添加到序列
            temp_seq.append(match)
            idx = entries.index(match)  # 更新当前位置
            last_end = match['end_ms']   # 更新最后结束时间
            next_cycle_idx = (next_cycle_idx + 1) % len(cycle)  # 更新期望状态
            found_next = True  # 标记找到有效序列

        if found_next:  # 如果找到完整序列则保存
            results.extend(temp_seq)
            
        start_pos = idx + 1  # 更新搜索起始位置
        
    return results


# === 并发处理封装 ===
def process_group(key_recs):
    key, recs = key_recs
    seq = find_sequence_for_group(recs)
    return key, seq

# === 1. 载入数据并一次性处理 ===
all_lines = []
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            all_lines.append(line)

# 提取并合并所有记录
all_records = []
for line in all_lines:
    all_records.extend(extract_signal_timing(line))
print(f"共提取 {len(all_records)} 条原始记录")

# === 去重 ===
before_dedup = len(all_records)
seen = set()
unique_records = []
for r in all_records:
    key = (r["regionId"], r["nodeId"], r["phaseId"], r["light"], r["st_ms"])
    if key not in seen:
        seen.add(key)
        unique_records.append(r)
after_dedup = len(unique_records)
print(f"✅ 去重前记录数：{before_dedup}，去重后：{after_dedup}，去除了 {before_dedup - after_dedup} 条重复记录")

# === 过滤 ===
data = [r for r in unique_records if 3 <= (r['end_ms'] - r['st_ms']) / 1000 <= 1000]
print(f"✅ 过滤后剩余 {len(data)} 条有效记录")

# === 2. 分组 ===
groups = defaultdict(list)
for rec in data:
    groups[(rec['regionId'], rec['nodeId'], rec['phaseId'])].append(rec)

# === 3. 多线程处理 + 进度条 ===
results = {}
group_items = list(groups.items())
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(process_group, item) for item in group_items]
    for f in tqdm(as_completed(futures), total=len(futures), desc="查找序列中"):
        key, seq = f.result()
        results[key] = seq
        print(f"组 {key} 匹配 {len(seq)} 条记录")


# 确保 record 文件夹存在
os.makedirs('record', exist_ok=True)

# 5. 从 results 中计算 green-occ
greenocc = []
csv_rows = []
for (region_id, node_id, phase_id), events in results.items():
    events.sort(key=lambda x: x["startTime"])
    red_idxs = [i for i, ev in enumerate(events) if ev["light"] == "红灯"]
    for i in range(len(red_idxs) - 1):
        s = events[red_idxs[i]]["startTime"]
        e = events[red_idxs[i+1]]["startTime"]
        total = (e - s).total_seconds()
        green_sec = sum(
            (ev["endTime"] - ev["startTime"]).total_seconds()
            for ev in events
            if ev["light"] == "绿灯"
            and ev["startTime"] >= s
            and ev["endTime"] <= e + timedelta(seconds=4)
        )
        ratio = green_sec / total if green_sec > 0 and total > 0 else None
        greenocc.append({
            "regionId":  region_id,
            "nodeId":    node_id,
            "phaseId":   phase_id,
            "green-occ": ratio,
            "startTime": s,
            "endTime":   e
        })
        # 加入 CSV 行
        csv_rows.append({
            "startTime": s,
            "regionId": region_id,
            "nodeId": node_id,
            "phaseId": phase_id,
            "green_ratio": ratio,
            "cycle_time_sec": total
        })

# 输出 CSV 到 record 目录
FILE_OUT_PATH = "record/green_ratio_cycles_323.csv"
pd.DataFrame(csv_rows).to_csv(FILE_OUT_PATH, index=False, encoding='utf-8')
print(f"✅ 已保存 CSV 到: {FILE_OUT_PATH}")
