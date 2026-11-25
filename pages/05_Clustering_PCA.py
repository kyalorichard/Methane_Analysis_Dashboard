import streamlit as st, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.unsupervised import CLUSTERERS
from analysis_engine.service_registry import get_service
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.settings_config import load_active_settings
render_sidebar_navigation()
_cfg = load_active_settings(st.session_state)
_cluster_cfg = _cfg.get("clustering", {})

header('Animal-level PCA & clustering','Explore multivariate phenotype structure using animal-level profiles. Select the clustering algorithms to compare.')
df=get_data();animal=get_roles(df).get('animal_id')
if not animal: st.error('Map an animal identifier in Data Management.');st.stop()
nums=numeric_cols(df);features=st.multiselect('Phenotype features',nums,default=[c for c in ['mean_methane','AUC_full','mean_resp','mean_eruct','weight'] if c in nums] or nums[:5])
if len(features)<2: st.stop()
profiles=get_service("animal_profiles")(df,animal,features);profiles=profiles.dropna(how='all')
if len(profiles)<5: st.error('At least five animal-level profiles are required.');st.stop()
metric_row([('ANIMALS',f'{len(profiles):,}','Animal-level profiles'),('FEATURES',str(len(features)),'Selected numeric features')])
scores,pca=get_service("pca_scores")(profiles, settings=_cfg);scores['animal_id']=scores.index.astype(str)
fig=px.scatter(scores,x='PC1',y='PC2',hover_name='animal_id',title='PCA of animal-level median phenotypes',color_discrete_sequence=[BLUE]);st.plotly_chart(fig,use_container_width=True)
st.write('Variance explained:',[round(float(v)*100,1) for v in pca.explained_variance_ratio_])
st.subheader('Clustering algorithm selection')
mode=st.radio('Algorithms to evaluate',['Compare all available algorithms','Select specific algorithms'],horizontal=True,key='cluster_selection_mode')
selected=CLUSTERERS if mode.startswith('Compare') else st.multiselect('Clustering algorithms',CLUSTERERS,default=CLUSTERERS[:2],key='cluster_selected_algorithms')
c1,c2,c3=st.columns(3)
with c1: k=st.slider('Clusters / mixture components',2,min(10,len(profiles)-1),min(max(2,int(_cluster_cfg.get('min_clusters',2))),min(10,len(profiles)-1)))
with c2: eps=st.slider('DBSCAN epsilon',0.1,3.0,0.8,0.1)
with c3: min_samples=st.slider('DBSCAN minimum samples',2,20,5)
if st.button('Compare selected clustering algorithms',type='primary',disabled=not selected):
    try:
        metrics,labels=get_service("compare_clusterers")(profiles,selected,k,eps,min_samples,settings=_cfg)
        st.session_state['cluster_metrics']=metrics
        st.session_state['cluster_labels']=labels
    except Exception as e: st.error(str(e))
metrics=st.session_state.get('cluster_metrics')
if metrics is not None:
    st.subheader('Clustering comparison')
    st.dataframe(metrics,use_container_width=True)
    st.caption('Higher silhouette and Calinski–Harabasz are generally preferred; lower Davies–Bouldin is generally preferred. DBSCAN noise points are excluded from internal validation metrics.')
    labs=st.session_state.get('cluster_labels',{})
    for name,lab in labs.items():
        view=scores.copy();view['cluster']=lab.reindex(view.index).astype(str)
        st.plotly_chart(px.scatter(view,x='PC1',y='PC2',color='cluster',hover_name='animal_id',title=f'{name}: PCA projection of assigned clusters'),use_container_width=True)
        st.download_button(f'Download {name} cluster assignments',lab.rename('cluster').reset_index().to_csv(index=False).encode(),f'{name.lower().replace(" ","_")}_clusters.csv','text/csv',key=f'dl_{name}')
with st.expander('K-means cluster-number diagnostics'):
    diag,x=get_service("cluster_diagnostics")(profiles, settings=_cfg)
    st.dataframe(diag,use_container_width=True)
    if not diag.empty: st.plotly_chart(px.line(diag,x='n_clusters',y=['silhouette','davies_bouldin','calinski_harabasz'],markers=True),use_container_width=True)
st.warning('Clusters are exploratory statistical groupings. Internal metrics do not establish biological classes. Assess resampling stability, sensitivity to scaling/features, and external biological validity before assigning class labels.')
