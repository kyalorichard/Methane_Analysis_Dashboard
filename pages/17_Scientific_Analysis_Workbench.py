import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from analysis_engine.ui import header, get_data, get_roles
from analysis_engine.service_registry import get_service
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header("Scientific Analysis Workbench",
       "Advanced workflows: reliability, agreement, group inference, allometry, quantile regression, duration sensitivity, equivalence and clustering stability.")

df=get_data().copy()
roles=get_roles(df)
animal=roles.get("animal_id")
group=roles.get("breed")
weight=roles.get("weight")
session=roles.get("round")
methane=roles.get("methane")
numeric=df.select_dtypes(include="number").columns.tolist()
allcols=list(df.columns)

def pick(label, options, default=None, key=None):
    opts=["—"]+list(options)
    idx=opts.index(default) if default in opts else 0
    val=st.selectbox(label,opts,index=idx,key=key)
    return None if val=="—" else val

tabs=st.tabs(["Reliability & agreement","Group inference","Allometry & quantiles",
              "Duration sensitivity","Equivalence testing","Cluster stability","Analysis record"])

with tabs[0]:
    st.subheader("Animal-level repeatability")
    st.caption("One-way random-effects ICC is provided as an exploratory estimate. If measurement sessions are fixed and fully crossed, use a prespecified two-way ICC model.")
    c1,c2=st.columns(2)
    with c1: aid=pick("Animal identifier",allcols,animal,"wb_icc_animal")
    with c2: y=pick("Continuous phenotype",numeric,methane,"wb_icc_y")
    if st.button("Estimate ICC",key="wb_run_icc",type="primary"):
        try:
            result=get_service("repeatability_long_format")(df,aid,y)
            boot=get_service("bootstrap_icc")(df,aid,y,n_boot=300)
            st.session_state["wb_icc_result"]={**result,"bootstrap":boot,"phenotype":y,"animal_id":aid}
            st.json(st.session_state["wb_icc_result"])
            st.metric("ICC(1,1)",f"{result['ICC_single']:.3f}")
            st.metric("Animal-bootstrap 95% interval",f"{boot['ci_low']:.3f} to {boot['ci_high']:.3f}")
            st.info(result["design_note"])
        except Exception as e: st.error(str(e))
    st.divider()
    st.subheader("Bland–Altman agreement across sessions")
    c1,c2,c3,c4=st.columns(4)
    with c1: baid=pick("Animal identifier",allcols,animal,"wb_ba_id")
    with c2: by=pick("Phenotype",numeric,methane,"wb_ba_y")
    with c3: sess=pick("Session / round",allcols,session,"wb_ba_session")
    levels=sorted(df[sess].dropna().astype(str).unique()) if sess else []
    with c4:
        sa=st.selectbox("Session A",levels,key="wb_ba_a") if levels else None
        sb=st.selectbox("Session B",levels,index=1 if len(levels)>1 else 0,key="wb_ba_b") if levels else None
    if st.button("Calculate agreement",key="wb_run_ba"):
        try:
            pts,summary=get_service("bland_altman")(df,baid,by,sess,sa,sb)
            st.json(summary)
            fig=px.scatter(pts,x="animal_mean",y="difference_b_minus_a",labels={"animal_mean":"Mean of paired sessions","difference_b_minus_a":"B − A"})
            fig.add_hline(y=summary["bias"],line_dash="solid")
            fig.add_hline(y=summary["loa_lower"],line_dash="dash")
            fig.add_hline(y=summary["loa_upper"],line_dash="dash")
            st.plotly_chart(fig,use_container_width=True)
            st.download_button("Download paired agreement data",pts.to_csv().encode(), "bland_altman_pairs.csv","text/csv")
        except Exception as e: st.error(str(e))

with tabs[1]:
    st.subheader("Between-group inference")
    c1,c2,c3=st.columns(3)
    with c1: gy=pick("Outcome",numeric,methane,"wb_group_y")
    with c2: gc=pick("Grouping variable",allcols,group,"wb_group_col")
    with c3: method=st.selectbox("Test",["auto","welch","kruskal"],key="wb_group_method")
    if st.button("Run group comparison",key="wb_group_run",type="primary"):
        try:
            res=get_service("group_comparison")(df,gy,gc,method)
            st.json(res)
            if "pairwise_mann_whitney" in res and res["pairwise_mann_whitney"]:
                st.dataframe(pd.DataFrame(res["pairwise_mann_whitney"]),use_container_width=True)
            fig=px.box(df,x=gc,y=gy,points="outliers",title=f"{gy} by {gc}")
            st.plotly_chart(fig,use_container_width=True)
            st.session_state["wb_group_result"]=res
        except Exception as e: st.error(str(e))
    st.caption("Welch's test is used for two independent groups; Kruskal–Wallis and BH-adjusted pairwise Mann–Whitney tests are available for multiple groups. Repeated records are not independent: aggregate per animal or use a repeated-measures model before interpreting these tests.")

with tabs[2]:
    st.subheader("Allometric scaling")
    c1,c2,c3=st.columns(3)
    with c1: ay=pick("Positive phenotype outcome",numeric,methane,"wb_allom_y")
    with c2: aw=pick("Body weight",numeric,weight,"wb_allom_w")
    with c3: ac=pick("Optional adjustment variable",allcols,None,"wb_allom_cov")
    if st.button("Fit log–log allometric model",key="wb_allom_run"):
        try:
            fit=get_service("fit_allometry")(df,ay,aw,[ac] if ac else [])
            st.text(fit.summary().as_text())
            st.metric("Allometric exponent",f"{fit.params.iloc[1]:.3f}")
            st.caption("The log–log slope is the estimated scaling exponent. HC3 standard errors are used; inspect residuals, leverage and biological plausibility.")
            st.session_state["wb_allometry_summary"]=fit.summary().as_text()
        except Exception as e: st.error(str(e))
    st.divider()
    st.subheader("Quantile regression")
    qy=pick("Outcome",numeric,methane,"wb_q_y")
    qpred=st.multiselect("Predictors", [c for c in allcols if c!=qy], default=[c for c in [weight,group] if c and c!=qy],key="wb_q_pred")
    q=st.slider("Target quantile",0.10,0.90,0.50,0.05,key="wb_quantile")
    if st.button("Fit quantile regression",key="wb_q_run"):
        try:
            fit=get_service("fit_quantile_regression")(df,qy,qpred,q,st.session_state.get("analysis_settings", {}))
            st.text(fit.summary().as_text())
        except Exception as e: st.error(str(e))

with tabs[3]:
    st.subheader("Recording-duration sensitivity")
    c1,c2=st.columns(2)
    with c1: dy=pick("Phenotype",numeric,methane,"wb_dur_y")
    with c2: dc=pick("Recording duration variable",numeric,roles.get("recording_duration"),"wb_dur_col")
    thresholds=st.multiselect("Minimum duration thresholds (seconds)",[60,90,120,150,180,210,240,270,300],[120,150,180,210,240],key="wb_dur_thresholds")
    if st.button("Evaluate duration thresholds",key="wb_dur_run"):
        try:
            result=get_service("duration_sensitivity")(df,dy,dc,thresholds,animal)
            st.dataframe(result,use_container_width=True)
            st.plotly_chart(px.line(result,x="minimum_duration_seconds",y="mean",markers=True),use_container_width=True)
            st.download_button("Download duration sensitivity",result.to_csv(index=False).encode(),"duration_sensitivity.csv","text/csv")
        except Exception as e: st.error(str(e))

with tabs[4]:
    st.subheader("Two one-sided tests (TOST)")
    st.warning("Define the equivalence margin before examining group differences. Statistical equivalence does not imply biological equivalence unless the margin is scientifically justified.")
    c1,c2,c3=st.columns(3)
    with c1: ey=pick("Outcome",numeric,methane,"wb_eq_y")
    with c2: eg=pick("Two-level grouping variable",allcols,group,"wb_eq_group")
    levels=sorted(df[eg].dropna().unique(),key=str) if eg else []
    with c3:
        if len(levels)>=2:
            ea=st.selectbox("Reference group",levels,key="wb_eq_a")
            eb=st.selectbox("Comparison group",[x for x in levels if x!=ea],key="wb_eq_b")
        else: ea=eb=None
    margin=st.number_input("Equivalence margin in outcome units",min_value=0.000001,value=1.0,format="%.6f",key="wb_eq_margin")
    if st.button("Run TOST",key="wb_eq_run"):
        try:
            res=get_service("tost_independent")(df,ey,eg,ea,eb,margin)
            st.json(res)
            st.metric("TOST p-value",f"{res['p_tost']:.4f}")
            st.success("Equivalence supported at alpha=0.05.") if res["equivalent_at_0.05"] else st.warning("Equivalence not demonstrated at alpha=0.05.")
        except Exception as e: st.error(str(e))

with tabs[5]:
    st.subheader("Animal-profile cluster stability")
    c1,c2=st.columns(2)
    with c1: ca=pick("Animal identifier",allcols,animal,"wb_clust_animal")
    with c2: k=st.number_input("Number of clusters",min_value=2,max_value=10,value=3,key="wb_cluster_k")
    cf=st.multiselect("Animal-level numeric phenotype features",numeric,default=[c for c in ["mean_methane","AUC_full","mean_resp","mean_eruct","weight"] if c in numeric],key="wb_cluster_features")
    reps=st.slider("Bootstrap resamples",50,300,100,25,key="wb_cluster_boot")
    if st.button("Assess cluster stability",key="wb_cluster_run"):
        try:
            res=get_service("cluster_stability")(df,ca,cf,int(k),int(reps))
            st.json(res)
            st.metric("Mean bootstrap adjusted Rand index",f"{res['mean_ari']:.3f}")
            st.caption(res["note"])
        except Exception as e: st.error(str(e))

with tabs[6]:
    st.subheader("Reproducibility record")
    record={"dataset_name":st.session_state.get("data_name","active dataset"),
            "species":st.session_state.get("species","unspecified"),
            "n_records":int(len(df)),"n_variables":int(df.shape[1]),
            "animal_id_role":animal,"group_role":group,"round_role":session,
            "phenotype_role":methane,"analysis_environment":"Streamlit local research workspace",
            "scientific_caveat":"Instrument-derived signals are not methane mass flux without validated calibration; repeated records require animal-aware inference and validation.",
            "saved_analysis_outputs":{k:v for k,v in st.session_state.items() if k.startswith("wb_") and isinstance(v,(dict,str,int,float))}}
    st.json(record)
    st.download_button("Download analysis manifest (JSON)",json.dumps(record,indent=2,default=str).encode(),"analysis_manifest.json","application/json")
    st.download_button("Download active dataset (Parquet)",df.to_parquet(index=False),"active_dataset.parquet","application/octet-stream")
