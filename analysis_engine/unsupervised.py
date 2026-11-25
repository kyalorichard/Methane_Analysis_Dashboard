import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler,StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans,AgglomerativeClustering,DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score,davies_bouldin_score,calinski_harabasz_score

CLUSTERERS = ['K-means', 'Agglomerative', 'Gaussian mixture', 'DBSCAN']

def animal_profiles(df,animal_id,features):
    x=df[features].apply(pd.to_numeric,errors='coerce')
    z=pd.concat([df[[animal_id]],x],axis=1)
    return z.groupby(animal_id,dropna=True)[features].median().dropna(how='all')

def pca_scores(profiles, settings=None):
    cfg=(settings or {}).get("clustering", {})
    x=SimpleImputer(strategy='median').fit_transform(profiles)
    x=StandardScaler().fit_transform(x)
    variance=float(cfg.get("pca_variance", 0.95))
    if not 0 < variance <= 1: raise ValueError("PCA variance threshold must be in (0, 1].")
    model=PCA(n_components=variance if variance < 1 else min(5,x.shape[0]-1,x.shape[1]), svd_solver="full")
    scores=model.fit_transform(x)
    return pd.DataFrame(scores,index=profiles.index,columns=[f"PC{i+1}" for i in range(scores.shape[1])]),model

def cluster_diagnostics(profiles,k_values=None,settings=None):
    cfg=(settings or {}).get("clustering", {})
    if k_values is None:
        k_values=range(int(cfg.get("min_clusters",2)), int(cfg.get("max_clusters",7))+1)
    x=RobustScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(profiles))
    rows=[]
    for k in k_values:
        if k>=len(profiles): continue
        labels=KMeans(n_clusters=k,n_init=30,random_state=int((settings or {}).get("comparison", {}).get("random_state",42))).fit_predict(x)
        if len(set(labels))<2: continue
        rows.append({'algorithm':'K-means','n_clusters':k,'silhouette':silhouette_score(x,labels),
          'davies_bouldin':davies_bouldin_score(x,labels),'calinski_harabasz':calinski_harabasz_score(x,labels)})
    return pd.DataFrame(rows),x

def compare_clusterers(profiles, selected_models=None, k=None, dbscan_eps=0.8, dbscan_min_samples=5, settings=None):
    cfg=(settings or {}).get("clustering", {})
    selected_models=list(selected_models or cfg.get("algorithms", CLUSTERERS))
    k=int(k if k is not None else cfg.get("min_clusters",3))
    distance=str(cfg.get("distance","euclidean")); linkage=str(cfg.get("linkage","ward"))
    if linkage == "ward" and distance != "euclidean":
        raise ValueError("Ward linkage requires Euclidean distance.")
    x=RobustScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(profiles))
    seed=int((settings or {}).get("comparison", {}).get("random_state",42))
    rows=[]; labels_out={}
    for name in selected_models:
        if name=='K-means': labels=KMeans(n_clusters=k,n_init=30,random_state=seed).fit_predict(x)
        elif name=='Agglomerative': labels=AgglomerativeClustering(n_clusters=k,metric=distance,linkage=linkage).fit_predict(x)
        elif name=='Gaussian mixture': labels=GaussianMixture(n_components=k,random_state=seed,n_init=5).fit_predict(x)
        elif name=='DBSCAN': labels=DBSCAN(eps=dbscan_eps,min_samples=dbscan_min_samples).fit_predict(x)
        else: raise ValueError(f'Unknown clustering algorithm: {name}')
        labels_out[name]=pd.Series(labels,index=profiles.index,name=name)
        mask=labels!=-1
        n_clusters=len(set(labels[mask]))
        noise=int((labels==-1).sum()) if name=='DBSCAN' else 0
        if n_clusters>=2 and mask.sum()>n_clusters:
            rows.append({'algorithm':name,'clusters':n_clusters,'noise_points':noise,
              'silhouette':silhouette_score(x[mask],labels[mask]),
              'davies_bouldin':davies_bouldin_score(x[mask],labels[mask]),
              'calinski_harabasz':calinski_harabasz_score(x[mask],labels[mask])})
        else:
            rows.append({'algorithm':name,'clusters':n_clusters,'noise_points':noise,
              'silhouette':np.nan,'davies_bouldin':np.nan,'calinski_harabasz':np.nan})
    return pd.DataFrame(rows),labels_out
