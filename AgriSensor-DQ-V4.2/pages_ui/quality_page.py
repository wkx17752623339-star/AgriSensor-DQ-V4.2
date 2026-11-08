"""Data quality evaluation; render(df, det) remains compatible with app.py."""
import streamlit as st
import plotly.express as px
from ui.theme import heading
from engine import quality
from services.analytics import extra_quality


def render(df, det):
    heading('数据质量评价中心', '原有评分、扩展评分与逐项扣分依据')
    with st.expander('探索性检测参数（仅改变扩展评分，不修改原始数据）', expanded=False):
        a, b = st.columns(2)
        stuck_min = a.slider('疑似恒值最短连续记录数', 3, 20, 6)
        gap_factor = b.slider('异常采样间隔倍数', 1.5, 6.0, 3.0, step=0.5)
    q = quality(det)
    e = extra_quality(df, stuck_min_samples=stuck_min, gap_multiplier=gap_factor)
    joined = q.merge(e, on='node_id', how='left')
    if joined.empty:
        st.info('当前没有可用于评价的数据。')
        return
    a, b, c, d = st.columns(4)
    a.metric('平均缺失率', f"{100 * q['missing_rate'].mean():.2f}%")
    b.metric('检测异常率', f"{100 * q['detected_rate'].mean():.2f}%")
    c.metric('原有健康分', f"{q['health_score'].mean():.1f}")
    d.metric('扩展数据质量分', f"{joined['扩展数据质量分'].mean():.2f}")
    chart = joined[['node_id', 'health_score', '扩展数据质量分']].melt(
        id_vars='node_id', var_name='评分类型', value_name='分数'
    ).replace({'health_score': '原有健康分'})
    st.plotly_chart(px.bar(chart, x='node_id', y='分数', color='评分类型',
                           barmode='group', range_y=[0, 105], template='plotly_white'),
                    use_container_width=True)
    st.subheader('逐节点质量评价明细')
    st.dataframe(joined, hide_index=True, use_container_width=True)
    st.subheader('扩展评分扣分构成')
    penalty_cols = ['缺失扣分', '重复扣分', '间隔扣分', '恒值扣分']
    penalties = joined[['node_id'] + penalty_cols].melt(
        id_vars='node_id', var_name='扣分原因', value_name='扣分')
    st.plotly_chart(px.bar(penalties, x='node_id', y='扣分', color='扣分原因',
                           barmode='stack', template='plotly_white'),
                    use_container_width=True)
    if (joined[penalty_cols].fillna(0).sum(axis=1) == 0).all():
        st.info('所有节点的扩展扣分均为0：在当前阈值下，没有触发缺失、重复时间戳、异常间隔或连续恒值扣分条件。100分不代表设备绝对健康。')
    st.caption('扩展评分 = max(0, 100 - 50×缺失率 - 10×重复率 - 20×异常间隔率 - 20×恒值记录率)。')
    st.caption('异常间隔：相邻正时间差超过本节点正间隔中位数的指定倍数。恒值片段：连续完全相同的有效温度读数。')
    st.warning('这些是探索性数据质量指标，不是经过验证的设备可靠性评分；RSSI、SNR与温度标准差仅作描述，不参与扣分。')
