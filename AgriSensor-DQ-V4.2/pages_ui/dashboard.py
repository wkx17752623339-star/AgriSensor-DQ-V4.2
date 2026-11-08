import streamlit as st
import plotly.express as px
from engine import quality
from ui.theme import heading

def render(df,det):
 heading('科研分析总览','历史温室多节点数据 · 自适应诊断 · 可复现实验')
 st.caption('📚 数据来自历史样本，非实时设备在线状态；下方异常标记由当前检测算法产生。')
 q=quality(det)
 a,b,c,d=st.columns(4)
 a.metric('数据覆盖节点',len(q));b.metric('累计采集记录',f'{len(df):,}');c.metric('数据缺失率',f'{100*(df.temperature.isna()|df.humidity.isna()).mean():.2f}%');d.metric('平均健康评分',f'{q.health_score.mean():.1f}/100')
 st.write('')
 left,right=st.columns([1.65,1])
 with left:
  st.subheader('环境传感趋势')
  node=st.selectbox('选择节点',sorted(df.node_id.unique()),key='home_node')
  metric=st.selectbox('监测指标',['temperature','humidity','rssi'],format_func=lambda x:{'temperature':'温度 °C','humidity':'湿度 %','rssi':'RSSI dBm'}[x],key='home_metric')
  g=det[det.node_id==node]
  fig=px.line(g,x='timestamp',y=metric,template='plotly_white')
  bad=g[g.detected_fault.eq(1)]
  fig.add_scatter(x=bad.timestamp,y=bad[metric],mode='markers',name='诊断异常',marker=dict(color='#e46a58',size=8))
  fig.update_layout(height=370,margin=dict(l=5,r=5,t=12,b=5),legend=dict(orientation='h'))
  st.plotly_chart(fig,use_container_width=True)
 with right:
  st.subheader('节点健康度排行')
  fig=px.bar(q.sort_values('health_score'),x='health_score',y='node_id',orientation='h',range_x=[0,100],color='health_score',color_continuous_scale='Teal',template='plotly_white')
  fig.update_layout(height=370,margin=dict(l=5,r=5,t=12,b=5),coloraxis_showscale=False)
  st.plotly_chart(fig,use_container_width=True)
 st.subheader('监测网络概况')
 x,y=st.columns([1,1])
 with x:
  st.dataframe(q.rename(columns={'node_id':'节点','records':'记录数','missing_rate':'缺失率','detected_rate':'异常率','health_score':'健康分'}),hide_index=True,use_container_width=True)
 with y:
  fault=det.loc[det.detected_fault.eq(1),'diagnosis'].value_counts().reset_index();fault.columns=['类型','数量']
  if not fault.empty:st.plotly_chart(px.pie(fault,names='类型',values='数量',hole=.55,color_discrete_sequence=['#0e9384','#e5a24c','#df665f']),use_container_width=True)
  else:st.info('当前诊断算法未标记异常。可进入故障注入页面生成测试场景。')
