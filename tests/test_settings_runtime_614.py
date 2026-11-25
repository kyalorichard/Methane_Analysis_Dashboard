import numpy as np
import pandas as pd
from analysis_engine.settings_config import defaults
from analysis_engine.unsupervised import pca_scores, cluster_diagnostics, compare_clusterers
from analysis_engine.time_series_forecasting import compare_forecasters


def test_pca_variance_setting_controls_component_count():
    rng=np.random.default_rng(11)
    x=pd.DataFrame(rng.normal(size=(40,6)),columns=list('abcdef'))
    low=defaults(); low['clustering']['pca_variance']=0.70
    high=defaults(); high['clustering']['pca_variance']=0.99
    _, m_low=pca_scores(x,low); _,m_high=pca_scores(x,high)
    assert m_low.n_components_ <= m_high.n_components_
    assert m_low.n_components_ != m_high.n_components_


def test_cluster_diagnostic_range_uses_settings():
    rng=np.random.default_rng(12)
    x=pd.DataFrame(rng.normal(size=(50,4)),columns=list('abcd'))
    cfg=defaults(); cfg['clustering'].update({'min_clusters':2,'max_clusters':4})
    result,_=cluster_diagnostics(x,settings=cfg)
    assert set(result.n_clusters).issubset({2,3,4})
    assert set(result.n_clusters).issuperset({2,3})


def test_agglomerative_distance_and_linkage_settings_are_applied():
    rng=np.random.default_rng(13)
    x=pd.DataFrame(rng.normal(size=(30,4)),columns=list('abcd'))
    cfg=defaults(); cfg['clustering'].update({'distance':'manhattan','linkage':'average'})
    metrics,labels=compare_clusterers(x,['Agglomerative'],k=3,settings=cfg)
    assert len(labels['Agglomerative'])==len(x)
    assert metrics.iloc[0]['clusters'] >= 2


def test_forecasting_uses_configured_model_list_when_models_omitted():
    idx=pd.date_range('2020-01-05',periods=30,freq='W')
    s=pd.Series(np.sin(np.arange(30)/3)+10,index=idx)
    cfg=defaults(); cfg['forecasting'].update({'models':['Naive'],'horizon':2,'test_fraction':0.2})
    result=compare_forecasters(s,settings=cfg)
    assert result['metrics']['model'].tolist()==['Naive']
    assert len(result['future']['Naive'])==2
