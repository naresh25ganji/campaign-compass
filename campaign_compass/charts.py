"""Shared chart styling and accessible units."""
import plotly.express as px
import plotly.graph_objects as go

COLORS = ["#147D71", "#6478AD", "#D89437", "#9B6CAB"]
CHANNEL_COLORS = dict(zip(["Facebook", "Instagram", "Pinterest", "Twitter/X"], COLORS))


def finish(fig, height=340, money=False):
    fig.update_layout(template="plotly_white", height=height,
                      margin=dict(l=25, r=25, t=30, b=25),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial, sans-serif", color="#34445A", size=12),
                      colorway=COLORS, legend=dict(orientation="h", y=1.12, x=0),
                      hovermode="x unified")
    fig.update_xaxes(showgrid=False, automargin=True)
    fig.update_yaxes(gridcolor="#E7ECF1", zerolinecolor="#CED7E1", automargin=True)
    if money:
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def line(df, x, y, label, color=None, money=False):
    fig = px.line(df, x=x, y=y, color=color, labels={x: "", y: label, "channel": "Channel"},
                  color_discrete_map=CHANNEL_COLORS if color == "channel" else None)
    return finish(fig, money=money)


def waterfall(m):
    return finish(go.Figure(go.Waterfall(
        x=["Gross revenue", "Discounts", "Refunds", "Product costs", "Fulfillment", "Advertising", "Contribution"],
        y=[m["gross_revenue"], -m["discount"], -m["refund"], -m["net_product_cost"], -m["fulfillment_cost"], -m["spend"], 0],
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
        increasing=dict(marker_color="#147D71"), decreasing=dict(marker_color="#B76C5E"),
        totals=dict(marker_color="#314761"), connector=dict(line_color="#B8C3CF"),
        hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")), height=360, money=True)
