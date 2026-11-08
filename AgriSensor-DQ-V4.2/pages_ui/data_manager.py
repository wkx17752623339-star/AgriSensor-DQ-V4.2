import os
import pandas as pd
import streamlit as st
from ui.theme import heading, feature_intro
from services.data_io import read_upload, csv_bytes
from services.workflow import (save_dataset,load_dataset,list_datasets,set_active_dataset,
    clear_active_dataset,delete_dataset,export_backup,import_backup)
from engine import demo_data


def render(df):
    cloud=os.getenv('AGRISENSOR_CLOUD_DEMO','1')=='1'
    heading('数据集管理中心','多数据集导入、质量校验、持久化管理与可移植备份')
    feature_intro('database','科研数据资产管理','本地多数据集持久保存 · 公网会话隔离 · 数据集备份与恢复')
    if cloud:
        st.info('当前为公网演示：上传文件仅在当前会话中分析，不跨重启保存。请及时下载CSV备份。')
    else:
        st.success('本地持久化已启用：数据集保存在本机 data/datasets/，目录已从Git跟踪中排除。建议定期导出ZIP备份。')
    tabs=st.tabs(['📥 数据导入','🗃️ 数据集仓库','📈 数据预览与导出','🧪 模拟数据'])
    with tabs[0]:
        st.subheader('上传温室传感器数据')
        st.caption('支持CSV、XLSX、XLS；字段需包含 timestamp、node_id、temperature、humidity。文件不超过12MB，最多100,000条记录。')
        file=st.file_uploader('选择数据文件',type=['csv','xlsx','xls'],key='dq_upload')
        if file is not None:
            st.caption(f'待导入：{file.name} · {file.size/1024:.1f} KB')
            if st.button('校验、导入并应用',type='primary',use_container_width=True):
                try:
                    with st.spinner('正在校验字段和加载数据…'):
                        d=read_upload(file)
                        did=None if cloud else save_dataset(d,file.name,file.name)
                        if did:set_active_dataset(did)
                    st.session_state.dataset=d
                    st.session_state.source=file.name
                    if did:st.session_state.dataset_id=did
                    else:st.session_state.pop('dataset_id',None)
                    st.session_state.pop('experiment',None)
                    st.success(f'导入成功：{len(d):,}条记录，{d.node_id.nunique()}个节点')
                    st.rerun()
                except Exception as exc:st.error(f'导入失败：{exc}')
    with tabs[1]:
        if cloud:
            st.info('公网演示不使用共享数据库，避免不同访客之间的数据互相覆盖。切换到本地模式可管理多个历史数据集。')
        else:
            catalog=list_datasets()
            if catalog.empty:
                st.info('还没有本地历史数据集，请先在“数据导入”中上传文件，或保存当前数据。')
            else:
                st.metric('本地已保存数据集',len(catalog))
                st.dataframe(catalog.rename(columns={'id':'数据集ID','name':'名称','source':'来源','created':'保存时间','rows':'记录数','nodes':'节点数'}),use_container_width=True,hide_index=True)
                choices=catalog.set_index('id')['name'].to_dict()
                selected=st.selectbox('选择历史数据集',catalog.id.tolist(),format_func=lambda x:f'{choices.get(x,x)} · {x}')
                c1,c2=st.columns(2)
                if c1.button('加载所选数据集',type='primary',use_container_width=True):
                    st.session_state.dataset=load_dataset(selected)
                    st.session_state.dataset_id=selected
                    st.session_state.source='本地数据集 '+choices[selected]
                    set_active_dataset(selected)
                    st.session_state.pop('experiment',None)
                    st.rerun()
                with c2:
                    confirm=st.checkbox('确认删除所选数据集',key='confirm_delete')
                    if st.button('删除所选数据集',disabled=not confirm,use_container_width=True):
                        delete_dataset(selected)
                        if st.session_state.get('dataset_id')==selected:st.session_state.pop('dataset_id',None)
                        st.success('数据集已删除');st.rerun()
            st.divider()
            save_name=st.text_input('当前数据集保存名称',value='温室传感器数据集')
            if st.button('将当前数据另存到本地仓库'):
                did=save_dataset(df,save_name,st.session_state.get('source','未知'))
                set_active_dataset(did);st.session_state.dataset_id=did
                st.success('保存成功：'+did);st.rerun()
            st.divider();st.subheader('批量备份与恢复')
            st.caption('ZIP包含历史数据集及元数据，不包含密钥和SQLite运行日志。请妥善保管。')
            st.download_button('下载所有历史数据集ZIP备份',data=export_backup(),file_name='AgriSensor-DQ-datasets-backup.zip',mime='application/zip',use_container_width=True)
            backup=st.file_uploader('恢复历史数据集ZIP备份',type=['zip'],key='dq_restore')
            if backup and st.button('校验并恢复备份'):
                try:
                    restored=import_backup(backup.getvalue())
                    st.success(f'成功恢复{restored}个数据集');st.rerun()
                except Exception as exc:st.error('备份恢复失败：'+str(exc))
    with tabs[2]:
        c1,c2,c3=st.columns(3)
        c1.metric('数据记录',f'{len(df):,}')
        c2.metric('传感器节点',df.node_id.nunique())
        c3.metric('时间范围',str(pd.to_datetime(df.timestamp).dt.date.nunique())+' 天')
        st.dataframe(df.head(500),use_container_width=True,hide_index=True,height=390)
        st.download_button('下载当前数据集 CSV',csv_bytes(df),'AgriSensor-DQ-current-data.csv','text/csv',type='primary')
    with tabs[3]:
        c1,c2,c3=st.columns(3)
        nodes=c1.slider('节点数量',2,20,8)
        days=c2.slider('模拟天数',1,14,3)
        seed=c3.number_input('随机种子',0,99999,42)
        if st.button('生成并应用模拟数据',use_container_width=True):
            st.session_state.dataset=demo_data(nodes=nodes,days=days,seed=int(seed))
            st.session_state.source='模拟数据'
            st.session_state.pop('dataset_id',None)
            if not cloud:clear_active_dataset()
            st.session_state.pop('experiment',None)
            st.rerun()
