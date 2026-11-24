import plotly.express as px


def _polish(fig):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="DM Sans, Arial, sans-serif", color="#183247", size=12),
        title=dict(font=dict(size=16, color="#183247"), x=0.02, xanchor="left"),
        margin=dict(l=18, r=18, t=55, b=18),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        hoverlabel=dict(bgcolor="#123B35", font=dict(color="#FFFFFF")),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#DCE7E1")
    fig.update_yaxes(gridcolor="#EDF2EF", zeroline=False)
    return fig


def missingness_plot(df):
    import pandas as pd
    m=(df.isna().mean()*100).sort_values(ascending=False).reset_index()
    m.columns=["variable","missing_percent"]
    fig=px.bar(m,x="variable",y="missing_percent",title="Missing observations by variable",color_discrete_sequence=["#176B5B"])
    return _polish(fig)


def numeric_distribution(df,col):
    fig=px.histogram(df,x=col,marginal="box",title=f"Distribution: {col}",color_discrete_sequence=["#23866F"])
    return _polish(fig)


def correlation_plot(df):
    fig=px.imshow(df.corr(numeric_only=True),text_auto=".2f",aspect="auto",title="Pearson correlation matrix",color_continuous_scale=["#F5F8F6","#A8D2C1","#176B5B"])
    return _polish(fig)
