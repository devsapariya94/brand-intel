"""Chart and visualization components"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def hits_timeline(timeline_data: list, title: str = "Hits Over Time"):
    """Display hits timeline chart"""
    if not timeline_data:
        st.info("No timeline data available")
        return
    
    df = pd.DataFrame(timeline_data)
    df["date"] = pd.to_datetime(df["date"])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["count"],
        mode="lines+markers",
        name="Hits",
        line=dict(color="#1E88E5", width=2),
        marker=dict(size=6, color="#1E88E5")
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Number of Hits",
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def severity_pie_chart(stats: dict, title: str = "Enrichment Decisions"):
    """Display pie chart of enrichment decisions"""
    labels = ["Alerts", "Suppressed", "Escalated"]
    values = [
        stats.get("alerts_sent", 0),
        stats.get("suppressed", 0),
        stats.get("escalated", 0),
    ]
    
    if sum(values) == 0:
        st.info("No enrichment data available")
        return
    
    colors = ["#E53935", "#43A047", "#FB8C00"]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors
    )])
    
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def source_bar_chart(by_source: dict, title: str = "Hits by Source"):
    """Display bar chart of hits by source"""
    if not by_source:
        st.info("No source data available")
        return
    
    fig = go.Figure(data=[go.Bar(
        x=list(by_source.keys()),
        y=list(by_source.values()),
        marker_color=["#1E88E5", "#43A047", "#FB8C00", "#8E24AA"][:len(by_source)]
    )])
    
    fig.update_layout(
        title=title,
        xaxis_title="Source",
        yaxis_title="Number of Hits",
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)
