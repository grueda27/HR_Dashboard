import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy import stats

st.set_page_config(page_title="PulsePoint Analytics", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .main {background-color: #0a0c24;}
    .stApp {background-color: #0a0c24;}
    h1, h2, h3 {color: #2dd4a8 !important;}
    .stMetric label {color: #9c9a92 !important; font-size: 14px !important;}
    .stMetric [data-testid="stMetricValue"] {color: #ffffff !important; font-size: 28px !important;}
    .stMetric [data-testid="stMetricDelta"] {font-size: 14px !important;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {background-color: #162050; color: #fff; border-radius: 8px;}
    .stTabs [aria-selected="true"] {background-color: #2dd4a8 !important; color: #0a0c24 !important;}
    div[data-testid="stSidebar"] {background-color: #0d0f2b;}
    .stSlider label, .stSelectbox label, .stMultiSelect label {color: #e0e0e0 !important;}
    .block-container {padding-top: 1rem;}
    .highlight-box {background: #162050; border: 1px solid #2dd4a8; border-radius: 12px; padding: 20px; margin: 10px 0;}
    .red-box {background: #2a1525; border: 1px solid #e24b4a; border-radius: 12px; padding: 20px; margin: 10px 0;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_excel("HR_Updated.xlsx")
    df['took_leave'] = ((df['Women_Leave']==1)|(df['Men_Leave']==1)|(df['NDandO_Leave']==1)).astype(int)
    df['heartbeat_bin'] = pd.cut(df['Sensor_Heartbeat(Average/Min)'], bins=[0,75,95,200], labels=['Low (<75)','Medium (75-95)','High (>95)'])
    df['step_quartile'] = pd.qcut(df['Sensor_StepCount'], 4, labels=['Q1 Low','Q2 Medium','Q3 High','Q4 Highest'])
    df['is_active'] = (df['Active']=='Y').astype(int)
    return df

df = load_data()

with st.sidebar:
    st.markdown("## 🎯 PulsePoint Analytics")
    st.markdown("---")
    st.markdown("### Filters")
    sel_dept = st.multiselect("Department", list(df['Department'].unique()), default=list(df['Department'].unique()))
    sel_geo = st.multiselect("Region", list(df['GEO'].unique()), default=list(df['GEO'].unique()))
    sel_gender = st.multiselect("Gender", list(df['Gender'].unique()), default=list(df['Gender'].unique()))
    st.markdown("---")
    st.markdown("### Simulation")
    sim_leave = st.slider("Leave Expansion (%)", 0, 100, 36)
    sim_step = st.slider("Step Reduction (%)", 0, 50, 0)
    sim_rest = st.slider("Rest Days / Month", 0, 4, 0)
    st.markdown("---")
    st.caption("BLS SOII 2024 | SHRM 2025 | n=14,999")

filt = df[(df['Department'].isin(sel_dept))&(df['GEO'].isin(sel_geo))&(df['Gender'].isin(sel_gender))]
base_rate = filt['Work_accident'].mean()
total_acc = int(filt['Work_accident'].sum())
leave_imp = max(0,(sim_leave-36)/100*0.019)
step_imp = sim_step/100*0.042
rest_imp = sim_rest*0.0035
sim_rate = max(base_rate - leave_imp - step_imp - rest_imp, 0.023)
prevented = int((base_rate - sim_rate)*len(filt))
saved = prevented * 1_000_000

st.markdown("# 🏥 Weekly Safety & Wellness Cockpit")
st.markdown("##### PulsePoint Analytics | BUS 150 Sprint 4")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard","🔬 Simulation","📈 Evidence","🎯 Recommendations"])

with tab1:
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Employees", f"{len(filt):,}")
    c2.metric("Accident Rate", f"{base_rate*100:.1f}%", delta=f"BLS: 2.3%", delta_color="inverse")
    c3.metric("Gap vs BLS", f"{base_rate/0.023:.1f}x", delta="above national", delta_color="inverse")
    hr95 = int((filt['Sensor_Heartbeat(Average/Min)']>=95).sum())
    c4.metric("HR >95 bpm", f"{hr95:,}", delta=f"{hr95/len(filt)*100:.0f}% of workforce", delta_color="inverse")
    c5.metric("Accidents", f"{total_acc:,}", delta=f"${total_acc}M exposure", delta_color="inverse")

    st.markdown("---")
    l,r = st.columns(2)
    with l:
        st.markdown("#### 🗺️ Accident Heatmap")
        hp = filt.groupby(['GEO','Department'])['Work_accident'].mean().reset_index().pivot(index='GEO',columns='Department',values='Work_accident')
        fig = px.imshow((hp.values*100).round(1), x=list(hp.columns), y=list(hp.index), color_continuous_scale='RdYlGn_r', text_auto='.1f', aspect='auto')
        fig.update_layout(paper_bgcolor='#0a0c24',plot_bgcolor='#0a0c24',font=dict(color='#e0e0e0'),height=400,margin=dict(l=20,r=20,t=10,b=20))
        st.plotly_chart(fig, use_container_width=True)
    with r:
        st.markdown("#### 💓 Heartbeat by Risk Zone")
        fig = px.histogram(filt, x='Sensor_Heartbeat(Average/Min)', color='heartbeat_bin', nbins=14,
            color_discrete_map={'Low (<75)':'#5DCAA5','Medium (75-95)':'#EF9F27','High (>95)':'#E24B4A'},
            category_orders={'heartbeat_bin':['Low (<75)','Medium (75-95)','High (>95)']})
        fig.add_vline(x=95, line_dash="dash", line_color="#E24B4A", line_width=2, annotation_text="95 bpm", annotation_font_color="#E24B4A")
        fig.update_layout(paper_bgcolor='#0a0c24',plot_bgcolor='#162050',font=dict(color='#e0e0e0'),height=400,margin=dict(l=20,r=20,t=10,b=20))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 🚨 Watch List — HR >95 & Sleep ≤5")
    w = filt[(filt['Sensor_Heartbeat(Average/Min)']>=95)&(filt['Sleep Hours']<=5)]
    if len(w)>0:
        ws = w.groupby(['Department','GEO']).agg(Count=('ID','count'),Acc_Rate=('Work_accident','mean'),Avg_HR=('Sensor_Heartbeat(Average/Min)','mean')).reset_index().sort_values('Acc_Rate',ascending=False).head(10)
        ws['Acc_Rate'] = (ws['Acc_Rate']*100).round(1).astype(str)+'%'
        ws['Avg_HR'] = ws['Avg_HR'].round(0).astype(int).astype(str)+' bpm'
        st.dataframe(ws, use_container_width=True, hide_index=True)

    l2,r2 = st.columns(2)
    with l2:
        st.markdown("#### 📋 Weekly Actions")
        st.markdown("1. **Flag** high-risk employees for wellness check-ins\n2. **Deploy** safety audit to Japan & UK\n3. **Mandate** rest days — presenteeism increases accidents\n4. **Intervene** ND in Operations (23.8% rate)\n5. **Target** 14.5% → 7% quarterly")
    with r2:
        st.markdown("#### 📊 Accidents by Step Quartile")
        sq = filt.groupby('step_quartile')['Work_accident'].mean().reset_index()
        sq['Work_accident'] = sq['Work_accident']*100
        fig = px.bar(sq, x='step_quartile', y='Work_accident', color='Work_accident', color_continuous_scale=['#5DCAA5','#EF9F27','#E24B4A'], text_auto='.1f')
        fig.update_layout(paper_bgcolor='#0a0c24',plot_bgcolor='#162050',font=dict(color='#e0e0e0'),height=280,margin=dict(l=20,r=20,t=10,b=20),showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### 🔬 What-If Simulation")
    st.markdown("*Move sidebar sliders to see projected impact in real time.*")
    st.markdown("---")
    c1,c2,c3 = st.columns(3)
    with c1:
        fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=round(sim_rate*100,1),
            delta={'reference':round(base_rate*100,1),'decreasing':{'color':'#5DCAA5'},'suffix':'%'},
            title={'text':"Projected Rate",'font':{'color':'#e0e0e0','size':16}},
            number={'suffix':'%','font':{'color':'#fff','size':36}},
            gauge={'axis':{'range':[0,20],'tickcolor':'#9c9a92'},'bar':{'color':'#2dd4a8'},'bgcolor':'#162050',
                'steps':[{'range':[0,2.3],'color':'#0F6E56'},{'range':[2.3,7],'color':'#1D9E75'},{'range':[7,12],'color':'#EF9F27'},{'range':[12,20],'color':'#E24B4A'}],
                'threshold':{'line':{'color':'#fff','width':3},'value':2.3}}))
        fig.update_layout(paper_bgcolor='#0a0c24',font=dict(color='#e0e0e0'),height=300,margin=dict(l=30,r=30,t=60,b=20))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown(f"""<div class='highlight-box'>
            <h3 style='color:#2dd4a8;margin-top:0;'>Results</h3>
            <p style='color:#e0e0e0;'>Current: <b>{base_rate*100:.1f}%</b></p>
            <p style='color:#5DCAA5;font-size:22px;'>Projected: <b>{sim_rate*100:.1f}%</b></p>
            <p style='color:#e0e0e0;'>Prevented: <b style='color:#2dd4a8;'>{prevented:,} accidents</b></p>
            <p style='color:#e0e0e0;'>Saved: <b style='color:#2dd4a8;'>${saved:,.0f}</b></p>
            <p style='color:#9c9a92;font-size:11px;'>@ $1M per accident</p></div>""", unsafe_allow_html=True)
    with c3:
        imp = pd.DataFrame({'Action':['Leave','Step Reduction','Rest Days','Gap to BLS'],'PP':[round(leave_imp*100,2),round(step_imp*100,2),round(rest_imp*100,2),round(max((sim_rate-0.023)*100,0),2)]})
        fig = px.bar(imp, x='PP', y='Action', orientation='h', color='Action',
            color_discrete_map={'Leave':'#2dd4a8','Step Reduction':'#378ADD','Rest Days':'#EF9F27','Gap to BLS':'#E24B4A'})
        fig.update_layout(paper_bgcolor='#0a0c24',plot_bgcolor='#162050',font=dict(color='#e0e0e0'),height=300,margin=dict(l=20,r=20,t=10,b=20),showlegend=False,xaxis_title="Percentage Points")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Leave Impact by Gender")
    lc = filt.groupby(['Gender','took_leave'])['Work_accident'].mean().reset_index()
    lc['Status'] = lc['took_leave'].map({0:'No Leave',1:'Took Leave'})
    lc['Rate'] = (lc['Work_accident']*100).round(1)
    fig = px.bar(lc, x='Gender', y='Rate', color='Status', barmode='group',
        color_discrete_map={'No Leave':'#E24B4A','Took Leave':'#2dd4a8'}, text_auto='.1f')
    fig.update_layout(paper_bgcolor='#0a0c24',plot_bgcolor='#162050',font=dict(color='#e0e0e0'),height=350,margin=dict(l=20,r=20,t=10,b=20))
    fig.update_traces(textposition='outside',textfont=dict(color='#e0e0e0'))
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### 📈 Hypothesis Testing")
    st.markdown("---")
    hyps = [
        {'id':'H1','t':'Accidents → Attrition','d':'Accidents are positively related to attrition.','x':'Work_accident','y':'is_active','xl':'Work Accident','yl':'Retention','c':'#E24B4A'},
        {'id':'H2','t':'Role → Accidents','d':'Role intensity predicts accident rates.','x':'Emp_Role','y':'Work_accident','xl':'Role Score','yl':'Accident Rate','c':'#EF9F27'},
        {'id':'H3','t':'Leave → Fewer Accidents','d':'Leave access reduces accidents.','x':'took_leave','y':'Work_accident','xl':'Leave Flag','yl':'Accident Rate','c':'#2dd4a8'},
        {'id':'H4','t':'Steps → Accidents','d':'Higher step count increases accidents.','x':'Sensor_StepCount','y':'Work_accident','xl':'Step Count','yl':'Accident Rate','c':'#378ADD'},
    ]
    for i in range(0,4,2):
        c1,c2 = st.columns(2)
        for j,col in enumerate([c1,c2]):
            h = hyps[i+j]
            with col:
                rv,pv = stats.pearsonr(filt[h['x']], filt[h['y']])
                sup = "✅ Supported" if pv<0.05 else "❌ Not Supported"
                sig = "***" if pv<0.001 else "**" if pv<0.01 else "*" if pv<0.05 else "ns"
                st.markdown(f"#### {h['id']}: {h['t']}")
                st.markdown(f"*{h['d']}*")
                st.markdown(f"**r = {rv:.4f} | p {'< .001' if pv<0.001 else f'= {pv:.4f}'} {sig} | {sup}**")
                g = filt.groupby(['Department','GEO','Gender']).agg(xv=(h['x'],'mean'),yv=(h['y'],'mean')).reset_index()
                fig = px.scatter(g, x='xv', y='yv', labels={'xv':h['xl'],'yv':h['yl']}, color_discrete_sequence=[h['c']])
                xa,ya = g['xv'].values, g['yv'].values
                m = np.isfinite(xa)&np.isfinite(ya)
                if m.sum()>2:
                    sl,ic,r2,p2,se = stats.linregress(xa[m],ya[m])
                    xl = np.linspace(xa[m].min(),xa[m].max(),50)
                    fig.add_trace(go.Scatter(x=xl,y=sl*xl+ic,mode='lines',line=dict(color=h['c'],width=2,dash='dash'),name=f'R²={r2**2:.3f}'))
                fig.update_layout(paper_bgcolor='#0a0c24',plot_bgcolor='#162050',font=dict(color='#e0e0e0'),height=280,margin=dict(l=20,r=20,t=10,b=20))
                fig.update_traces(marker=dict(size=6,opacity=0.6),selector=dict(mode='markers'))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("---")

    st.markdown("#### Correlation Matrix")
    cv = ['Work_accident','Sensor_StepCount','Emp_Role','took_leave','Sleep Hours','Sensor_Heartbeat(Average/Min)','Absenteeism rate','is_active']
    cl = ['Accidents','Steps','Role','Leave','Sleep','HR','Absent','Active']
    cm = filt[cv].corr()
    fig = px.imshow(cm.values, x=cl, y=cl, text_auto='.3f', color_continuous_scale='RdBu_r', zmin=-0.6, zmax=0.6)
    fig.update_layout(paper_bgcolor='#0a0c24',font=dict(color='#e0e0e0'),height=500,margin=dict(l=20,r=20,t=10,b=20))
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("### 🎯 Recommendations")
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("""<div class='highlight-box'><h4 style='color:#2dd4a8;margin-top:0;'>R1: Expand Leave — Target 9%</h4>
            <p style='color:#e0e0e0;'><b>H3:</b> Leave reduces accidents (p < .0001)</p>
            <ul style='color:#9c9a92;'><li>No-leave: 15.7% rate → Leave: 13.8%</li><li>ND: 22% → 3% with leave</li><li>Action: Universal eligibility + flex scheduling</li></ul></div>""", unsafe_allow_html=True)
        st.markdown("""<div class='highlight-box'><h4 style='color:#EF9F27;margin-top:0;'>R3: Safety Audits — Target 12%</h4>
            <p style='color:#e0e0e0;'><b>H1:</b> Accidents → attrition (p < .0001)</p>
            <ul style='color:#9c9a92;'><li>$1M per accident cost</li><li>Target HR & IT first</li><li>Benchmark: Australia 13.0%</li></ul></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='highlight-box'><h4 style='color:#378ADD;margin-top:0;'>R2: Activity Monitoring — Target 10%</h4>
            <p style='color:#e0e0e0;'><b>H4:</b> Steps predict accidents (p < .0001)</p>
            <ul style='color:#9c9a92;'><li>Q3: 17.1% vs Q1: 10.3%</li><li>Wearable fatigue alerts</li><li>Task rotation for high-activity roles</li></ul></div>""", unsafe_allow_html=True)
        st.markdown("""<div class='red-box'><h4 style='color:#E24B4A;margin-top:0;'>R4: Combined — Target 7%</h4>
            <p style='color:#e0e0e0;'><b>All evidence:</b> 14.5% → 7%</p>
            <ul style='color:#9c9a92;'><li>~1,100 accidents prevented</li><li>~$1.1B saved</li><li>Q1→12%, Q2→10%, Q3→8%, Q4→7%</li></ul></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Evidence → Recommendation Chain")
    st.dataframe(pd.DataFrame({
        'Evidence':['Leave reduces accidents','Steps predict accidents','Accidents drive attrition','Combined'],
        'Hypothesis':['H3 (p<.0001)','H4 (p<.0001)','H1 (p<.0001)','H1-H4'],
        'Recommendation':['R1: Leave','R2: Monitoring','R3: Audits','R4: Combined'],
        'Current':['14.5%']*4,'Target':['9%','10%','12%','7%'],
        'Impact':['~825 prevented','~675 prevented','~375 prevented','~1,100 prevented']
    }), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("<div style='text-align:center;color:#5f5e5a;font-size:12px;'>PulsePoint Analytics | BUS 150 | BLS 2024 | SHRM 2025 | n=14,999</div>", unsafe_allow_html=True)
