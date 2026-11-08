
from pathlib import Path
import json
import pandas as pd

# ========== 1. 基础配置 ==========
ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "raw" / "Greenhouse-1.xlsx"
OUTPUT_DIR = ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "greenhouse_sample.csv"
REPORT_FILE = OUTPUT_DIR / "greenhouse_sample_info.json"

NODES = ["AF16", "AF17", "AF18", "AF19", "AF20", "AF21"]
ROWS_PER_NODE = 2000

REQUIRED_COLUMNS = [
    "Onboard Temperature",
    "Onboard Humidity",
    "RSSI",
    "SNR"
]


# ========== 2. 时间字段解析 ==========
def parse_timestamps(df):
    """
    兼容两种Excel时间结构：
    1. Date列本身包含完整日期时间
    2. Date和Time分别保存日期与时间
    """
    date = pd.to_datetime(df["Date"], errors="coerce")

    if "Time" not in df.columns:
        return date

    time_text = df["Time"].astype("string").str.strip()
    valid_time = (
        time_text.notna()
        & ~time_text.isin(["", "NaT", "nan", "None"])
    )

    if not valid_time.any():
        return date

    date_text = date.dt.strftime("%Y-%m-%d")
    combined = pd.to_datetime(
        date_text + " " + time_text,
        errors="coerce"
    )

    # 如果Date已有时分秒，则保留原有时间；
    # 否则优先使用Date + Time。
    has_clock = (
        date.dt.hour.ne(0)
        | date.dt.minute.ne(0)
        | date.dt.second.ne(0)
    )

    return date.where(has_clock | ~valid_time, combined)


# ========== 3. 读取单个节点 ==========
def load_node(excel, node):
    print(f"\n正在读取节点：{node}")

    df = pd.read_excel(
        excel,
        sheet_name=node,
        usecols=lambda col: str(col).strip() in (
            ["Date", "Time"] + REQUIRED_COLUMNS
        )
    )

    df.columns = df.columns.astype(str).str.strip()

    required = ["Date"] + REQUIRED_COLUMNS
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"{node} 缺少必要字段：{missing}"
        )

    df["timestamp"] = parse_timestamps(df)
    df["node_id"] = node

    rename_map = {
        "Onboard Temperature": "temperature",
        "Onboard Humidity": "humidity",
        "RSSI": "rssi",
        "SNR": "snr"
    }

    df = df.rename(columns=rename_map)

    columns = [
        "timestamp", "node_id",
        "temperature", "humidity",
        "rssi", "snr"
    ]

    df = df[columns].copy()

    for col in ["temperature", "humidity", "rssi", "snr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 无法解析时间的记录不能用于时间序列分析
    invalid_time = int(df["timestamp"].isna().sum())
    df = df.dropna(subset=["timestamp"])

    df = df.sort_values("timestamp")
    df = df.drop_duplicates(
        subset=["timestamp", "node_id"],
        keep="first"
    )

    # 选择最早的连续2000条观测记录，
    # 不采用随机抽样，以保留时间序列结构。
    df = df.head(ROWS_PER_NODE).copy()

    print(f"成功提取：{len(df)} 条")
    print(f"无效时间记录：{invalid_time} 条")

    return df, invalid_time


# ========== 4. 主程序 ==========
def main():
    print("=" * 60)
    print("AgriSensor-DQ 真实温室数据转换工具")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"原始数据不存在：{INPUT_FILE}"
        )

    all_data = []
    node_reports = []

    with pd.ExcelFile(INPUT_FILE) as excel:
        for node in NODES:
            if node not in excel.sheet_names:
                print(f"警告：工作表 {node} 不存在，跳过")
                continue

            df, invalid_time = load_node(excel, node)

            if df.empty:
                print(f"警告：节点 {node} 没有有效数据")
                continue

            all_data.append(df)

            node_reports.append({
                "node_id": node,
                "rows": int(len(df)),
                "invalid_timestamp_rows": invalid_time,
                "missing_values": {
                    col: int(df[col].isna().sum())
                    for col in [
                        "temperature", "humidity",
                        "rssi", "snr"
                    ]
                },
                "start_time": str(df["timestamp"].min()),
                "end_time": str(df["timestamp"].max())
            })

    if not all_data:
        raise RuntimeError("没有成功读取任何节点数据")

    result = pd.concat(all_data, ignore_index=True)
    result = result.sort_values(
        ["timestamp", "node_id"]
    ).reset_index(drop=True)

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d %H:%M:%S"
    )

    report = {
        "source": "Zenodo Greenhouse-1",
        "source_url": "https://zenodo.org/records/5793685",
        "sample_method": "earliest chronological observations",
        "total_rows": int(len(result)),
        "node_count": int(result["node_id"].nunique()),
        "nodes": node_reports
    }

    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("数据转换成功！")
    print("=" * 60)

    print(f"总记录数：{len(result)}")
    print(f"节点数量：{result['node_id'].nunique()}")
    print(f"CSV文件：{OUTPUT_FILE}")
    print(f"质量摘要：{REPORT_FILE}")

    print("\n各节点记录数量：")
    print(result.groupby("node_id").size())

    print("\n前5行：")
    print(result.head().to_string(index=False))


if __name__ == "__main__":
    main()
