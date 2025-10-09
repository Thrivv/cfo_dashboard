import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st


def render_kpi_chart(data, title, x_col, y_col, chart_type="line"):
    """Render KPI chart with various types"""
    try:
        if chart_type == "line":
            fig = px.line(data, x=x_col, y=y_col, title=title)
        elif chart_type == "bar":
            fig = px.bar(data, x=x_col, y=y_col, title=title)
        elif chart_type == "area":
            fig = px.area(data, x=x_col, y=y_col, title=title)

        fig.update_layout(
            showlegend=False, margin=dict(l=0, r=0, t=40, b=0), height=300
        )

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering chart: {str(e)}")


def render_forecast_chart(historical_data, forecast_data, title):
    """Render forecast chart with confidence intervals"""
    try:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=historical_data.index,
                y=historical_data.values,
                mode="lines",
                name="Historical",
                line=dict(color="blue"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=forecast_data.index,
                y=forecast_data["forecast"],
                mode="lines",
                name="Forecast",
                line=dict(color="red", dash="dash"),
            )
        )

        if "upper" in forecast_data.columns and "lower" in forecast_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=forecast_data.index,
                    y=forecast_data["upper"],
                    fill=None,
                    mode="lines",
                    line_color="rgba(0,0,0,0)",
                    showlegend=False,
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=forecast_data.index,
                    y=forecast_data["lower"],
                    fill="tonexty",
                    mode="lines",
                    line_color="rgba(0,0,0,0)",
                    name="Confidence Interval",
                    fillcolor="rgba(255,0,0,0.2)",
                )
            )

        fig.update_layout(
            title=title, xaxis_title="Date", yaxis_title="Value", height=400
        )

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering forecast chart: {str(e)}")


def render_metric_cards(metrics):
    """Render metric cards in columns"""
    cols = st.columns(len(metrics))

    for i, (label, value, delta) in enumerate(metrics):
        with cols[i]:
            st.metric(label=label, value=value, delta=delta)
