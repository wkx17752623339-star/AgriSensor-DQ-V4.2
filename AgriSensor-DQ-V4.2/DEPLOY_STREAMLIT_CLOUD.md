# AgriSensor-DQ 云端部署说明

## 已完成的云端适配
- 保留原有 Streamlit 页面和算法。
- 默认云端演示模式：从 `data/processed/greenhouse_sample.csv` 加载温室样本。
- 用户上传数据仅保留在当前 Streamlit 会话，不设置全局活动数据集。
- 移除约 32 MB 的原始 Excel 和原有 SQLite 文件，避免上传不必要数据。
- 实验结果请直接下载；云端免费托管的本地文件和 SQLite **不保证持久化**。
- 目前故障诊断的日志/实验历史仍使用服务器端临时 SQLite，可能被不同访问者看到；请仅使用公开的演示数据，不要上传敏感资料。

## 部署步骤
1. 在 GitHub 新建仓库，上传**本 ZIP 中 `AgriSensor-DQ-V2` 文件夹里的内容**（确保 `app.py` 位于仓库根目录）。
2. 访问 https://share.streamlit.io ，使用 GitHub 登录，选择 **Create app / Deploy**。
3. 选择刚创建的仓库和分支，入口文件填 `app.py`。
4. 在 Advanced settings / 环境变量中可设置 `AGRISENSOR_CLOUD_DEMO=1`（默认已经是 1）。
5. 点击部署，等待安装 requirements.txt，成功后复制 `.streamlit.app` 网址。
6. 依次测试：系统总览、节点监控、数据管理、故障诊断、质量评价、算法实验、报告下载。

## 本地运行
安装依赖：`python -m pip install -r requirements.txt`。
本地持久化模式：Windows `双击启动网页.bat`，或在命令行设置 `AGRISENSOR_CLOUD_DEMO=0` 后运行 `python -m streamlit run app.py`。
云端演示模式本地验证：`python -m streamlit run app.py`。

## 注意
- 免费托管会休眠或重启；云端SQLite数据和上传内容不能当作长期记录。
- 这是一套历史数据分析与算法验证原型，不具备实时LoRaWAN接入。
- 若需要长期保存或多人私有数据隔离，后续应使用持久化数据库及鉴权。
