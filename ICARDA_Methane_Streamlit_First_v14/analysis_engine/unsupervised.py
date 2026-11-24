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

def pca_scores(profiles):
    x=SimpleImputer(strategy='median').fit_transform(profiles)
    x=StandardScaler().fit_transform(x)
    model=PCA(n_components=min(5,x.shape[0]-1,x.shape[1]))
    scores=model.fit_transform(x)
    return pd.DataFrame(scores,index=profiles.index,columns=[f"PC{i+1}" for i in range(scores.shape[1])]),model

def cluster_diagnostics(profiles,k_values=range(2,8)):
    x=RobustScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(profiles))
    rows=[]
    for k in k_values:
        if k>=len(profiles): continue
        labels=KMeans(n_clusters=k,n_init=30,random_state=42).fit_predict(x)
        if len(set(labels))<2: continue
        rows.append({'algorithm':'K-means','n_clusters':k,'silhouette':silhouette_score(x,labels),
          'davies_bouldin':davies_bouldin_score(x,labels),'calinski_harabasz':calinski_harabasz_score(x,labels)})
    return pd.DataFrame(rows),x

def compare_clusterers(profiles, selected_models, k=3, dbscan_eps=0.8, dbscan_min_samples=5):
    x=RobustScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(profiles))
    rows=[]; labels_out={}
    for name in selected_models:
        if name=='K-means': labels=KMeans(n_clusters=k,n_init=30,random_state=42).fit_predict(x)
        elif name=='Agglomerative': labels=AgglomerativeClustering(n_clusters=k).fit_predict(x)
        elif name=='Gaussian mixture': labels=GaussianMixture(n_components=k,random_state=42,n_init=5).fit_predict(x)
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
