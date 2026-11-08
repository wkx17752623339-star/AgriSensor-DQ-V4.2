import os
import streamlit as st
from ui.theme import heading
from services.workflow import list_runs,list_datasets
from services.data_io import csv_bytes
from services.storage import events

def render(df,det):
    heading('报告与实验档案','查看持久化数据集、诊断实验记录和操作日志')
    if os.getenv('AGRISENSOR_CLOUD_DEMO','1') == '1':
        st.info('公网模式不保存或展示其他访客的实验记录；请在算法实验页下载HTML和CSV报告。')
        st.download_button('下载当前检测结果CSV',csv_bytes(det),'current_detection.csv','text/csv')
        return
    st.subheader('历史实验记录')
    runs=list_runs()
    if runs.empty:st.info('暂无已保存的诊断实验。请先到故障诊断页运行并保存。')
    else:
        st.dataframe(runs,use_container_width=True,hide_index=True)
        st.download_button('下载实验记录CSV',csv_bytes(runs),'experiment_history.csv','text/csv')
    st.subheader('已保存数据集')
    datasets=list_datasets();st.dataframe(datasets,use_container_width=True,hide_index=True)
    st.subheader('故障操作日志')
    ev=events();st.dataframe(ev,use_container_width=True,hide_index=True)
    st.download_button('下载当前检测结果CSV',csv_bytes(det),'current_detection.csv','text/csv')
