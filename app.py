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

NEWS_COUNTRY_CODES = {
    'USA': 'us',
    'JPN': 'jp',
    'SGP': 'sg',
    'EU': 'gb',   # using UK as proxy for EU
    'CHN': 'cn'
}

def get_news_headlines(country_code='us'):
    api_key = '0fa37405cbc747eb9aef0b157fc28568' 
    url = f'https://newsapi.org/v2/top-headlines?country={country_code}&apiKey={api_key}'
    try:
        r = requests.get(url)
        data = r.json()
        articles = data.get('articles', [])[:10]
        if not articles:
            fallback_url = f'https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={api_key}'
            data = requests.get(fallback_url).json()
            articles = data.get('articles', [])
        return [article['title'] for article in articles]
    except:
        return ["Unable to fetch news."]

def get_percent_change(current,previous):
    try:
        if isinstance(current, str) or isinstance(previous, str):
            return ''
        if current is None or previous is None or previous == 0:
            return ''
        pct = (current - previous) / previous * 100
        return f"({pct:+.2f}%)"
    except:
        return ''

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

    html.Div([
    html.H3("Market Headlines"),
    html.Div(id='news-section')
    ], style={'marginTop': '40px', 'padding': '20px', 'backgroundColor': '#1B3B5F', 'borderRadius': '8px'}),
    dcc.Interval(
    id='news-update-interval',
    interval=10 * 60 * 1000,  # every 10 minutes
    n_intervals=0
    )

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
    ], style={
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
    # Map country ISO to index
    ticker_map = {
        'USA': '^GSPC',
        'JPN': '^N225',
        'SGP': '^STI',
        'EU': '^STOXX50E',
        'CHN': '000001.SS'
    }
    selected_ticker = ticker_map[selected_country]

    fx_ticker_map = {
    'USA': None,  # Base currency
    'JPN': 'USDJPY=X',
    'SGP': 'USDSGD=X',
    'EU': 'USDEUR=X',
    'CHN': 'USDCNY=X'
    }
    selected_fx_ticker = fx_ticker_map[selected_country]

   # Fetch and clean stock data
    stock_data = yf.download(selected_ticker, start='2000-01-01', end=today, interval='1d')

    # If MultiIndex (e.g. columns like ("Close", "^GSPC")), flatten it
    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)

    # Clean data
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

    # Fetch macroeconomic data
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

    # Latest values (with safe fallback)
    latest_close = stock_data['Close'].dropna().iloc[-1] if not stock_data.empty else 'N/A'

    gdp_latest = macro_data['GDP Growth (%)'].dropna(subset=['NY.GDP.MKTP.KD.ZG'])
    gdp_value = gdp_latest['NY.GDP.MKTP.KD.ZG'].iloc[-1] if not gdp_latest.empty else 'N/A'

    cpi_latest = macro_data['Inflation (CPI %)'].dropna(subset=['FP.CPI.TOTL.ZG'])
    cpi_value = cpi_latest['FP.CPI.TOTL.ZG'].iloc[-1] if not cpi_latest.empty else 'N/A'

    lend_latest = macro_data['Lending Rate (%)'].dropna(subset=['FR.INR.LEND'])
    lend_value = lend_latest['FR.INR.LEND'].iloc[-1] if not lend_latest.empty else 'N/A'

    rinr_latest = macro_data['Real Interest Rate (%)'].dropna(subset=['FR.INR.RINR'])
    rinr_value = rinr_latest['FR.INR.RINR'].iloc[-1] if not rinr_latest.empty else 'N/A'

    #Stock index trend
    stock_series = stock_data['Close'].dropna()
    stock_prev = stock_series.iloc[-2] if len(stock_series) >= 2 else None
    stock_trend = get_trend_symbol(latest_close, stock_prev)
    stock_pct = get_percent_change(latest_close, stock_prev)

    # GDP trend
    gdp_series = macro_data['GDP Growth (%)']['NY.GDP.MKTP.KD.ZG'].dropna()
    gdp_value = gdp_series.iloc[-1] if not gdp_series.empty else 'N/A'
    gdp_prev = gdp_series.iloc[-2] if len(gdp_series) >= 2 else None
    gdp_trend = get_trend_symbol(gdp_value, gdp_prev)
    gdp_pct = get_percent_change(gdp_value, gdp_prev)

    # CPI trend
    cpi_series = macro_data['Inflation (CPI %)']['FP.CPI.TOTL.ZG'].dropna()
    cpi_value = cpi_series.iloc[-1] if not cpi_series.empty else 'N/A'
    cpi_prev = cpi_series.iloc[-2] if len(cpi_series) >= 2 else None
    cpi_trend = get_trend_symbol(cpi_value, cpi_prev)
    cpi_pct = get_percent_change(cpi_value, cpi_prev)

    # Lending rate trend
    lend_series = macro_data['Lending Rate (%)']['FR.INR.LEND'].dropna()
    lend_value = lend_series.iloc[-1] if not lend_series.empty else 'N/A'
    lend_prev = lend_series.iloc[-2] if len(lend_series) >= 2 else None
    lend_trend = get_trend_symbol(lend_value, lend_prev)
    lend_pct = get_percent_change(lend_value, lend_prev)

    # Real rate trend
    rinr_series = macro_data['Real Interest Rate (%)']['FR.INR.RINR'].dropna()
    rinr_value = rinr_series.iloc[-1] if not rinr_series.empty else 'N/A'
    rinr_prev = rinr_series.iloc[-2] if len(rinr_series) >= 2 else None
    rinr_trend = get_trend_symbol(rinr_value, rinr_prev)
    rinr_pct = get_percent_change(rinr_value, rinr_prev)

    # FX trend
    if selected_fx_ticker and fx_data is not None and not fx_data.empty:
        fx_series = fx_data['Close'].dropna()
        fx_value = fx_series.iloc[-1]
        fx_prev = fx_series.iloc[-2] if len(fx_series) >= 2 else None
        fx_trend = get_trend_symbol(fx_value, fx_prev)
        fx_pct = get_percent_change(fx_value, fx_prev)
    else:
        fx_value = 'Base Currency (USD)'
        fx_trend = ''
        fx_pct = ''

    summary_cards = [
        format_card(f'Stock Index ({selected_ticker}) [Daily]', latest_close, stock_trend, stock_pct),
        format_card('GDP Growth (%) [YoY]', gdp_value, gdp_trend, gdp_pct),
        format_card('Inflation (CPI %) [YoY]', cpi_value, cpi_trend, cpi_pct),
        format_card('Lending Rate (%) [YoY]', lend_value, lend_trend, lend_pct),
        format_card('FX Rate [Daily]', fx_value, fx_trend, fx_pct)
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

@app.callback(
    Output('news-section', 'children'),
    Input('news-update-interval', 'n_intervals'),
    Input('country-dropdown', 'value')
)
def update_news(n, selected_country):
    code = NEWS_COUNTRY_CODES.get(selected_country, 'us')
    headlines = get_news_headlines(code)
    return html.Ul([html.Li(h, style={'paddingBottom': '5px'}) for h in headlines])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

