# AgriSensor-DQ V2.0 — 智慧农业传感器网络数据质量与故障诊断平台

## 最简运行（Windows + PyCharm）
1. 解压整个工程到 `D:\chuangganqi\AgriSensor-DQ-V2`（路径可自行调整）。
2. PyCharm 打开此文件夹，配置已有Python解释器，例如 `D:\python\python.exe`。
3. 首次使用请安装 `requirements.txt` 中的依赖。可以在PyCharm终端执行 `D:\python\python.exe -m pip install -r requirements.txt`，或双击 `首次安装依赖.bat`（要求 `python` 命令可用）。
4. 在PyCharm直接右键运行 **`启动系统.py`**。它会自动启动服务、打开浏览器，**无需输入Streamlit命令或邮箱**。
5. 不用PyCharm时也可双击 `双击启动网页.bat`（要求系统 `python` 命令可用）。
6. 关闭启动窗口或按Ctrl+C停止服务。若默认8501端口被占用，自动尝试后续端口。

## 七个页面
系统总览、节点监控、数据管理、故障诊断、数据质量评价、算法实验、报告导出。

## 数据字段
`timestamp,node_id,temperature,humidity` 必需；`rssi,fault_type,is_fault` 可选。
`is_fault` 必须是真值标签才能计算Precision/Recall/F1；没有真值标签时不会伪造指标。

## 文件夹结构
- `app.py`：统一网页入口；`启动系统.py`：自动启动器
- `pages_ui/`：七个独立页面模块
- `services/`：导入、故障注入、质量分析、实验、SQLite日志
- `ui/` + `assets/`：网页样式与组件
- `engine.py`：核心检测、质量评价、模拟数据
- `tests/`：算法回归测试
- `data/`：SQLite操作日志；`results/`：供未来论文实验存档

## 研究边界
本项目以模拟数据和用户导入数据为主，无真实硬件连接。阈值和健康评分用于课程演示，不代表农业设备认证。故障注入的标签用于算法教学评价，后续论文需设计重复实验和独立验证。


## 第一轮功能补丁（增量升级）
覆盖 pages_ui/data_manager.py、diagnosis.py、reports.py、services/faults.py，新增 services/workflow.py。
原启动方式保持不变。首次打开数据管理页会创建 SQLite 数据集及实验记录表。
故障注入不再为无标签真实数据伪造完整真值；已有标注数据可继续评价。
数据集存储于 data/datasets，实验索引在 data/agrisensor.db；请定期备份 data 目录。


## V4.2 数据管理与视觉升级

- 本地模式：`AGRISENSOR_CLOUD_DEMO=0`，支持多数据集持久保存、选择、删除、完整ZIP备份及恢复。数据位于 `data/agrisensor.db` 与 `data/datasets/`，均不应提交到Git。
- 云端模式（默认）：`AGRISENSOR_CLOUD_DEMO=1`，上传数据仅在访客当前会话中使用，支持下载当前CSV；重启、重新部署后不保证保留。
- 本地Windows PowerShell运行：`$env:AGRISENSOR_CLOUD_DEMO='0'; python -m streamlit run app.py`。
- 如需跨电脑迁移本地历史数据集，请在“数据管理 → 数据集仓库”下载ZIP备份，在新环境使用恢复功能。
- UI：科研蓝/农业青绿主题，放大功能标题、导航、指标和图标；保留V4.1性能缓存和研究算法。
