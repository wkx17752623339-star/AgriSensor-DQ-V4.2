
from pathlib import Path
import pandas as pd

# 自动定位项目根目录
ROOT = Path(__file__).resolve().parents[1]

FILE_PATH = (
    ROOT / "data" / "raw" / "Greenhouse-1.xlsx"
)

if not FILE_PATH.exists():
    raise FileNotFoundError(
        f"没有找到数据文件：{FILE_PATH}"
    )

print("正在检查温室传感器数据...")

# 读取工作簿结构
excel = pd.ExcelFile(FILE_PATH)

print("\nExcel工作表：")
print(excel.sheet_names)

for sheet in excel.sheet_names:
    print(f"\n===== 工作表：{sheet} =====")

    # 只读取前5行，避免一次加载整个文件
    df = pd.read_excel(
        excel,
        sheet_name=sheet,
        nrows=5
    )

    print("\n列名：")
    for col in df.columns:
        print(repr(col))

    print("\n前5行数据：")
    print(df.to_string(index=False))

print("\n检查完成！")

print("\n========== 传感器节点结构检查 ==========")

print(f"工作表总数：{len(excel.sheet_names)}")

for i, sheet in enumerate(excel.sheet_names, start=1):
    print(f"{i}. {sheet}")

print("\n检查完成！")
