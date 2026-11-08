"""One-click three-algorithm comparison and standalone HTML report."""
import hashlib
import html
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from ui.theme import heading
from services.experiments import batch_compare, METHODS
from services.faults import KINDS
from services.data_io import csv_bytes


def report_html(summary, detail, meta):
    """Portable offline HTML report with tables and CSS bar charts."""
    esc = lambda x: html.escape(str(x), quote=True)
    def tbl(frame):
        columns = ''.join(f'<th>{esc(c)}</th>' for c in frame.columns)
        rows = ''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in row)+'</tr>'
                       for row in frame.itertuples(index=False, name=None))
        return '<table><thead><tr>'+columns+'</tr></thead><tbody>'+rows+'</tbody></table>'
    bars = []
    for _,r in summary.iterrows():
        rate = float(r['平均注入点检出率']) if pd.notna(r['平均注入点检出率']) else 0
        pct = max(0,min(100,rate*100))
        bars.append(f'<div class="barrow"><div>{esc(r["故障类型"])} · {esc(r["算法"])} — {pct:.1f}%</div>'
                    f'<div class="track"><div class="fill" style="width:{pct:.2f}%"></div></div></div>')
    meta_html=''.join(f'<li><b>{esc(k)}：</b>{esc(v)}</li>' for k,v in meta.items())
    header = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>AgriSensor-DQ多算法对比实验报告</title>
<style>body{font-family:"Microsoft YaHei",Arial,sans-serif;max-width:1100px;margin:35px auto;padding:0 24px;color:#18344a;line-height:1.7}h1{color:#126476}h2{border-bottom:2px solid #e0edf1;padding-bottom:7px}table{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0 25px}th,td{border:1px solid #dbe4e8;padding:8px;text-align:left}th{background:#eaf4f5}tr:nth-child(even){background:#f8fafb}ul{columns:2}.barrow{margin:9px 0}.track{background:#e9eef1;height:14px;border-radius:9px;overflow:hidden}.fill{background:#168d91;height:100%}.note{background:#fff6df;padding:14px;border-radius:8px}small{color:#64748b}</style></head><body>"""
    sections = [
        header,
        '<h1>AgriSensor-DQ · 多算法联合检测实验报告</h1><p>生成时间：'+esc(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))+'</p>',
        '<h2>1. 实验设置</h2><ul>'+meta_html+'</ul>',
        '<h2>2. 故障注入点检出率对比</h2>'+''.join(bars),
        '<h2>3. 结果汇总</h2>'+tbl(summary.round(4)),
        '<h2>4. 逐次实验明细</h2>'+tbl(detail.round(5)),
        '<h2>5. 结果解释与局限</h2><p class="note">本实验在原始传感器数据副本上人工注入故障。'
        '“新增注入点检出率”仅衡量相对未注入基线新出现的命中；“注入点检出率”仅衡量已知注入位置的命中情况，不等同于完整Recall；原始数据缺少独立核实的正常/故障标签，'
        '因此其他位置检出数不能直接认定为误报，也不能据此计算可信的Precision、F1。'
        '实验对比反映本次数据、参数和故障注入方式下的结果，不代表算法在所有场景下的优劣。</p>',
        '<small>AgriSensor-DQ | 可直接用浏览器打开、打印为PDF的离线HTML报告</small></body></html>'
    ]
    return ''.join(sections)



def render(df):
    heading('算法实验中心', '一键运行多种算法 · 故障类型对比 · 自动生成实验报告')
    st.info('实验在数据副本上运行；新增场景自适应算法使用因果滚动中位数与MAD阈值，不利用未来采样点。')
    if df is None or df.empty:
        st.warning('请先在数据管理页面加载真实数据。')
        return
    node=st.selectbox('实验节点',sorted(df.node_id.astype(str).unique()),key='oneclick_node')
    kinds=st.multiselect('选择要比较的故障类型',KINDS,default=['尖峰','缓慢漂移','卡死'],key='oneclick_kinds')
    a,b,c=st.columns(3)
    repeats=int(a.number_input('每种故障重复次数',min_value=1,max_value=5,value=1,step=1,key='oneclick_repeats'))
    strength=float(b.slider('故障强度',1.0,25.0,8.0,key='oneclick_strength'))
    seed=int(c.number_input('随机种子',min_value=0,max_value=999999,value=21,key='oneclick_seed'))
    a,b,c=st.columns(3)
    field=a.selectbox('注入字段',['temperature','humidity','rssi'],key='oneclick_field')
    start=int(b.slider('故障开始位置（%）',0,90,30,key='oneclick_start'))
    duration=int(c.slider('持续长度（%）',2,50,12,key='oneclick_duration'))
    with st.expander('高级检测参数（默认即可）'):
        window=int(st.slider('Hampel窗口',5,31,11,2,key='oneclick_window'))
        threshold=float(st.slider('Hampel敏感度',1.5,6.0,3.0,.5,key='oneclick_threshold'))
        contamination=float(st.slider('Isolation Forest异常比例',.01,.30,.08,.01,key='oneclick_contamination'))
    methods=st.multiselect('参与对比的算法',METHODS,default=METHODS,key='v4_methods')
    st.write('本次参与对比：'+('、'.join(methods) if methods else '未选择'))
    st.caption(f'预计 {len(kinds)} 类故障 × {len(methods)} 种算法 × {repeats} 次 = {len(kinds)*len(methods)*repeats} 组检测。')
    if st.button('一键运行多算法并生成报告',type='primary',disabled=not kinds or not methods):
        bar=st.progress(0,text='正在准备实验')
        def progress(done,total):
            bar.progress(min(1.0,done/total),text=f'已完成 {done}/{total} 组')
        try:
            with st.spinner('正在执行，请稍候...'):
                r=batch_compare(df,node,kinds,methods=methods,repeats=repeats,strength=strength,
                                start_fraction=start/100,duration_fraction=duration/100,
                                field=field,seed=seed,window=window,threshold=threshold,
                                contamination=contamination,progress=progress)
            summary=r.groupby(['故障类型','算法'],as_index=False).agg(
                平均注入点检出率=('注入点检出率','mean'),
                平均注入点数=('注入点数','mean'),
                平均命中数=('命中注入点数','mean'),
                平均新增注入点检出率=('新增注入点检出率','mean'),
                平均其他位置检出数=('其他位置检出数','mean'),
                平均检测耗时秒=('检测耗时(秒)','mean'),
                实验次数=('重复序号','count'))
            meta={'数据集节点':node,'数据总记录数':len(df),'故障类型':'、'.join(kinds),
                  '检测算法':'、'.join(methods),'每类重复次数':repeats,'故障强度':strength,
                  '注入字段':field,'开始位置':f'{start}%','持续长度':f'{duration}%',
                  '随机种子':seed,'Hampel窗口':window,'Hampel敏感度':threshold,
                  'IF异常比例':contamination}
            st.session_state.oneclick_results=(r,summary,meta)
            st.session_state.oneclick_source=hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
            st.success(f'已完成 {len(r)} 组检测，报告已自动生成。')
        except Exception as exc:
            st.error(f'实验失败：{exc}')
    saved=st.session_state.get('oneclick_results')
    if saved is None:
        st.info('设置故障类型后点击上方按钮，结果表、对比图和报告下载按钮会自动出现。')
        return
    r,summary,meta=saved
    if st.session_state.get('oneclick_source')!=hashlib.sha256(df.to_csv(index=False).encode()).hexdigest():
        st.warning('当前数据集与上次实验不同，以下是历史结果。请重新运行以更新报告。')
    st.subheader('多算法对比结果表')
    display=summary.copy();display['平均注入点检出率']= (display['平均注入点检出率']*100).round(2)
    st.caption('表中“平均注入点检出率”单位为%；其他位置检出数不等于误报数。')
    st.dataframe(display,hide_index=True,use_container_width=True)
    st.subheader('不同故障类型的多算法对比图')
    chart=display.rename(columns={'平均注入点检出率':'注入点检出率(%)'})
    fig=px.bar(chart,x='故障类型',y='注入点检出率(%)',color='算法',barmode='group',
               range_y=[0,100],text='注入点检出率(%)',template='plotly_white')
    fig.update_traces(texttemplate='%{text:.1f}%',textposition='outside')
    st.plotly_chart(fig,use_container_width=True)
    st.subheader('实验明细')
    st.dataframe(r,hide_index=True,use_container_width=True)
    st.subheader('自动生成实验报告')
    st.download_button('下载完整HTML实验报告（含图表和结论说明）',
                       data=report_html(summary,r,meta).encode('utf-8'),
                       file_name='AgriSensor-DQ_多算法实验报告.html',mime='text/html')
    x,y=st.columns(2)
    x.download_button('下载汇总结果CSV',csv_bytes(display),'three_algorithm_summary.csv','text/csv')
    y.download_button('下载逐次实验CSV',csv_bytes(r),'three_algorithm_details.csv','text/csv')
    st.caption('HTML报告可用浏览器打开，再按Ctrl+P打印或另存为PDF。')
