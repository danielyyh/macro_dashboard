import yfinance as yf
import dash
from dash import dcc, html
import plotly.graph_objs as go
import pandas as pd
import datetime
import numpy as np
import requests
import os

from pandas_datareader import wb

app = dash.Dash(__name__)
app.title = 'Global Macro Dashboard'

today = datetime.datetime.today().strftime('%Y-%m-%d')

def get_macro_change(latest, prev, indicator=""):
    if latest is None or prev is None or pd.isna(latest) or pd.isna(prev):
        return "N/A"
    
    diff = latest - prev

    if indicator == "Lending Rate":
        return f"{int(diff * 100):+} bps"  
    elif indicator in ["GDP Growth", "Inflation"]:
        return f"{diff:+.1f}%"  
    else:
        return f"{diff:+.2f}" 
    
def get_latest_label(series):
    if series is not None and not series.empty:
        last_index = series.index[-1]
        if isinstance(last_index, (int, float)):
            return f"[{int(last_index)}]"
        elif isinstance(last_index, (str)):
            return f"j[{last_index}]"
        else:
            try:
                return f"[{last_index.strftime('%Y-%m-%d')}]"
            except:
                return f"[{last_index}]"
    return ""

# World Bank indicator codes
WB_INDICATORS = {
    'GDP Growth (%)': 'NY.GDP.MKTP.KD.ZG',
    'Inflation (CPI %)': 'FP.CPI.TOTL.ZG',
    'Lending Rate (%)': 'FR.INR.LEND',
    'Real Interest Rate (%)': 'FR.INR.RINR'
}

def get_macro_data(country_iso='USA'):
    data = {}
    for label, indicator in WB_INDICATORS.items():
        df = wb.download(indicator=indicator, country=country_iso, start=2000, end=today)
        df = df.reset_index().sort_values(by='year', ascending=True)
        data[label] = df
    return data

app.layout = html.Div([

    html.H1('🌐 Global Macro Dashboard', style={
        'textAlign': 'center',
        'color': 'white',
        'marginBottom': '40px'
    }),

   dcc.Dropdown(
    id='country-dropdown',
    options=[
        {'label': 'United States (S&P 500)', 'value': 'USA'},
        {'label': 'Japan (Nikkei 225)', 'value': 'JPN'},
        {'label': 'Singapore (STI)', 'value': 'SGP'},
        {'label': 'European Union (Euro Stoxx 50)', 'value': 'EU'},
        {'label': 'China (SSE Composite)', 'value': 'CHN'}
    ],
    value='USA',
    style={
        'color': '#102542',
        'backgroundColor': '#F0F0F0',
        'borderRadius': '8px',
        'padding': '8px',
        'width': '400px',
        'margin': 'auto',
        'fontWeight': 'bold'
        }
    ),

    html.Div(id='summary-cards', style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px', 'justifyContent': 'center', 'marginTop': '20px'}),

    html.H2("Stock Index"),
    dcc.Graph(id='stock-index-graph'),

    html.Div([
        html.Div([
            html.H3("GDP Growth"),
            dcc.Graph(id='macro-gdp', style={'height': '400px', 'width': '100%'})
        ], style={'flex': '1', 'padding': '10px', 'minWidth': '400px'}),
        
        html.Div([
            html.H3("Inflation"),
            dcc.Graph(id='macro-inflation', style={'height': '400px', 'width': '100%'}),
        ], style={'flex': '1', 'padding': '10px', 'minWidth': '400px'})
    ], style={'display': 'flex', 'flexWrap': 'wrap'}),

    html.Div([
        html.Div([
            html.H3("Lending Rate"),
            dcc.Graph(id='macro-lend', style={'height': '400px', 'width': '100%'})
        ], style={'flex': '1', 'padding': '10px', 'minWidth': '400px'}),

        html.Div([
            html.H3("Real Interest Rate (RINR)"),
            dcc.Graph(id='macro-rinr', style={'height': '400px', 'width': '100%'})
        ], style={'flex': '1', 'padding': '10px', 'minWidth': '400px'})
    ], style={'display': 'flex', 'flexWrap': 'wrap'}),
    
    html.H2("FX Rate vs USD"),
    dcc.Graph(id='fx-graph'),

], style={
    'backgroundColor': '#102542',
    'padding': '40px',
    'fontFamily': 'Segoe UI, sans-serif',
    'color': '#F0F0F0',
    'minHeight': '100vh'
})

from dash.dependencies import Input, Output

def get_trend_symbol(current, previous):
    if current is None or previous is None:
        return ''
    try:
        if current > previous:
            return '▲'
        elif current < previous:
            return '▼'
        else: 
            return '➖'
    except:
        return ''

def format_card(label, value, trend='', pct='', unit=''):
    if trend == '▲':
        color = '#2ECC71'
    elif trend == '▼':
        color = '#F87060'
    else:
        color = '#999999'

    return html.Div([
        html.H4(label),
        html.P(f"{value:.2f} {unit} {trend} {pct}" if isinstance(value, (int, float, np.number)) else f"{value} {trend} {pct}")
    ], title=f"{label}: {value} {unit} {pct}", style={
        'backgroundColor': '#1B3B5F',
        'padding': '15px 20px',
        'borderRadius': '10px',
        'color': color,
        'minWidth': '160px',
        'boxShadow': f'0px 0px 8px {color}',
        'textAlign': 'center'
    })

@app.callback(
    [
        Output('stock-index-graph', 'figure'),
        Output('macro-gdp', 'figure'),
        Output('macro-inflation', 'figure'),
        Output('macro-lend', 'figure'),
        Output('macro-rinr', 'figure'),
        Output('fx-graph', 'figure'),
        Output('summary-cards', 'children')
    ],
    [Input('country-dropdown', 'value')]
)
def update_dashboard(selected_country):
    ticker_map = {
        'USA': '^GSPC',
        'JPN': '^N225',
        'SGP': '^STI',
        'EU': '^STOXX50E',
        'CHN': '000001.SS'
    }
    selected_ticker = ticker_map[selected_country]

    fx_ticker_map = {
    'USA': None, 
    'JPN': 'USDJPY=X',
    'SGP': 'USDSGD=X',
    'EU': 'USDEUR=X',
    'CHN': 'USDCNY=X'
    }
    selected_fx_ticker = fx_ticker_map[selected_country]

    stock_data = yf.download(selected_ticker, start='2000-01-01', end=today, interval='1d')

    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)

    stock_data = stock_data[~stock_data.index.duplicated(keep='first')]
    stock_data = stock_data.sort_index()

    stock_fig = go.Figure()

    if not stock_data.empty and 'Close' in stock_data.columns:
        print("Stock Data Loaded:", stock_data.shape)
        print(stock_data[['Close']].head())

        stock_fig.add_trace(go.Scatter(
            x=stock_data.index,
            y=stock_data['Close'],
            mode='lines',
            line=dict(color='#F87060', width=2),
            name='Closing Price'
        ))

        ticker_names = {
            'USA': 'S&P 500',
            'JPN': 'Nikkei 225',
            'SGP': 'STI',
            'EU': 'Euro Stoxx 50',
            'CHN': 'Shanghai Composite'
        }
        ticker_name = ticker_names[selected_country]

        stock_fig.update_layout(
            title=f'Stock Index - {ticker_name}',
            xaxis_title='Date',
            yaxis_title='Close Price',
            xaxis=dict(
                tickformat='%b %Y',
                tickangle=45,
                rangeslider=dict(visible=True)
            ),
            template='plotly_dark',
            height=400
        )
    else:
        stock_fig.update_layout(
            title='Stock Index (No Data Available)',
            template='plotly_dark'
        )

    wb_country_codes = {
    'USA': 'USA',
    'JPN': 'JPN',
    'SGP': 'SGP',
    'EU': 'EUU',
    'CHN': 'CHN'
    }
    macro_data = get_macro_data(wb_country_codes[selected_country])

    fx_fig = go.Figure()
    fx_data = None
    if selected_fx_ticker:
        fx_data = yf.download(selected_fx_ticker, start='2000-01-01', end=today, interval='1d')
        if isinstance(fx_data.columns, pd.MultiIndex):
            fx_data.columns = fx_data.columns.get_level_values(0)
        fx_data = fx_data[~fx_data.index.duplicated(keep='first')]
        fx_data = fx_data.sort_index()

        if not fx_data.empty and 'Close' in fx_data.columns:
            fx_value = fx_data['Close'].dropna().iloc[-1]
            fx_fig.add_trace(go.Scatter(
                x=fx_data.index,
                y=fx_data['Close'],
                mode='lines',
                line=dict(color='orange', width=2),
                name='FX Rate'
            ))
            fx_fig.update_layout(
                title='FX Rate vs USD',
                xaxis_title='Date',
                yaxis_title='Exchange Rate',
                xaxis=dict(tickformat='%b %Y', tickangle=45),
                template='plotly_dark'
            )
        else:
            fx_value = 'N/A'
            fx_fig.update_layout(
                title='FX Rate: No Data',
                template='plotly_dark'
            )
    else:
        fx_value = 'Base Currency (USD)'
        fx_fig.update_layout(
            title='FX Rate: N/A for Base Currency (USD)',
            template='plotly_dark'
        )

    latest_close = stock_data['Close'].dropna().iloc[-1] if not stock_data.empty else 'N/A'

    gdp_latest = macro_data['GDP Growth (%)'].dropna(subset=['NY.GDP.MKTP.KD.ZG'])
    gdp_value = gdp_latest['NY.GDP.MKTP.KD.ZG'].iloc[-1] if not gdp_latest.empty else 'N/A'

    cpi_latest = macro_data['Inflation (CPI %)'].dropna(subset=['FP.CPI.TOTL.ZG'])
    cpi_value = cpi_latest['FP.CPI.TOTL.ZG'].iloc[-1] if not cpi_latest.empty else 'N/A'

    lend_latest = macro_data['Lending Rate (%)'].dropna(subset=['FR.INR.LEND'])
    lend_value = lend_latest['FR.INR.LEND'].iloc[-1] if not lend_latest.empty else 'N/A'

    rinr_latest = macro_data['Real Interest Rate (%)'].dropna(subset=['FR.INR.RINR'])
    rinr_value = rinr_latest['FR.INR.RINR'].iloc[-1] if not rinr_latest.empty else 'N/A'

    stock_series = stock_data['Close'].dropna()
    stock_prev = stock_series.iloc[-2] if len(stock_series) >= 2 else None
    stock_trend = get_trend_symbol(latest_close, stock_prev)
    stock_pct = get_macro_change(latest_close, stock_prev, "Stock Index") + "%"

    gdp_series = macro_data['GDP Growth (%)']['NY.GDP.MKTP.KD.ZG'].dropna()
    gdp_value = gdp_series.iloc[-1] if not gdp_series.empty else 'N/A'
    gdp_prev = gdp_series.iloc[-2] if len(gdp_series) >= 2 else None
    gdp_trend = get_trend_symbol(gdp_value, gdp_prev)
    gdp_pct = get_macro_change(gdp_value, gdp_prev, "GDP Growth")

    cpi_series = macro_data['Inflation (CPI %)']['FP.CPI.TOTL.ZG'].dropna()
    cpi_value = cpi_series.iloc[-1] if not cpi_series.empty else 'N/A'
    cpi_prev = cpi_series.iloc[-2] if len(cpi_series) >= 2 else None
    cpi_trend = get_trend_symbol(cpi_value, cpi_prev)
    cpi_pct = get_macro_change(cpi_value, cpi_prev, "Inflation")

    lend_series = macro_data['Lending Rate (%)']['FR.INR.LEND'].dropna()
    lend_value = lend_series.iloc[-1] if not lend_series.empty else 'N/A'
    lend_prev = lend_series.iloc[-2] if len(lend_series) >= 2 else None
    lend_trend = get_trend_symbol(lend_value, lend_prev)
    lend_pct = get_macro_change(lend_value, lend_prev, "Lending Rate")

    rinr_series = macro_data['Real Interest Rate (%)']['FR.INR.RINR'].dropna()
    rinr_value = rinr_series.iloc[-1] if not rinr_series.empty else 'N/A'
    rinr_prev = rinr_series.iloc[-2] if len(rinr_series) >= 2 else None
    ## rinr_trend = get_trend_symbol(rinr_value, rinr_prev)
    ## rinr_pct = get_macro_change(rinr_value, rinr_prev, "Real Interest Rate")

    if selected_fx_ticker and fx_data is not None and not fx_data.empty:
        fx_series = fx_data['Close'].dropna()
        fx_value = fx_series.iloc[-1]
        fx_prev = fx_series.iloc[-2] if len(fx_series) >= 2 else None
        fx_trend = get_trend_symbol(fx_value, fx_prev)
        fx_pct = get_macro_change(fx_value, fx_prev, "FX Rate") + "%"
    else:
        fx_value = 'Base Currency (USD)'
        fx_trend = ''
        fx_pct = ''

    summary_cards = [
        format_card(f'Stock Index ({selected_ticker}) {get_latest_label(stock_series)}', latest_close, stock_trend, stock_pct),
        format_card(f'GDP Growth (%) [{int(gdp_latest["year"].iloc[-1])}]' if not gdp_latest.empty else 'GDP Growth (%)', gdp_value, gdp_trend, gdp_pct),
        format_card(f'Inflation (CPI %) [{int(cpi_latest["year"].iloc[-1])}]' if not cpi_latest.empty else 'Inflation (CPI %)', cpi_value, cpi_trend, cpi_pct),
        format_card(f'Lending Rate (%) [{int(lend_latest["year"].iloc[-1])}]' if not lend_latest.empty else 'Lending Rate (%)', lend_value, lend_trend, lend_pct),
        format_card(f'FX Rate {get_latest_label(fx_series) if selected_fx_ticker else ""}', fx_value, fx_trend, fx_pct)
    ]

    gdp_fig = go.Figure()
    gdp_fig.add_trace(go.Bar(x=macro_data['GDP Growth (%)']['year'], y=macro_data['GDP Growth (%)']['NY.GDP.MKTP.KD.ZG']))
    gdp_fig.update_layout(title='GDP Growth (%)', template='plotly_dark')

    inf_fig = go.Figure()
    inf_fig.add_trace(go.Bar(x=macro_data['Inflation (CPI %)']['year'], y=macro_data['Inflation (CPI %)']['FP.CPI.TOTL.ZG']))
    inf_fig.update_layout(title='Inflation (CPI %)', template='plotly_dark')

    ir_fig = go.Figure()
    ir_fig.add_trace(go.Bar(x=macro_data['Lending Rate (%)']['year'], y=macro_data['Lending Rate (%)']['FR.INR.LEND']))
    ir_fig.update_layout(title='Lending Rate (%)', template='plotly_dark')

    rinr_fig = go.Figure()
    rinr_fig.add_trace(go.Bar(x=macro_data['Real Interest Rate (%)']['year'], y=macro_data['Real Interest Rate (%)']['FR.INR.RINR']))
    rinr_fig.update_layout(title='Real Interest Rate (%)', template='plotly_dark')
        
    print(stock_data.head())
    return stock_fig, gdp_fig, inf_fig, ir_fig, rinr_fig, fx_fig, summary_cards

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

