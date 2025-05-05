import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, ctx
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
from datetime import datetime
import json
import webbrowser
import threading
import time
import argparse
import base64
from io import BytesIO

class AmazonDashboard:
    def __init__(self, data_file=None, results_file=None, port=8050):
        """Initialize the dashboard."""
        self.data_file = data_file
        self.results_file = results_file
        self.port = port
        self.df = None
        self.results = None
        self.app = None
        
        # Başlatma bilgisi
        print(f"Dashboard starting  ...")
        print(f"Data file: {self.data_file}")
        print(f"Results file: {self.results_file}")
        print(f"Port: {self.port}")
        
        # Önce CSV dosyasını yüklemeyi dene
        if self.data_file and os.path.exists(self.data_file):
            try:
                self.df = pd.read_csv(self.data_file)
                print(f"CSV data loaded: {self.data_file} ({len(self.df)} rows)")
                
                # Veri kontrolü
                if self.df.empty:
                    print("Warning: CSV file is empty")
                else:
                    print(f"Columns: {', '.join(self.df.columns)}")
            except Exception as e:
                print(f"CSV loading error: {e}")
        else:
            print(f"CSV file not found or not specified: {self.data_file}")
                
        # Sonuç dosyasını yüklemeyi dene
        if self.results_file and os.path.exists(self.results_file):
            try:
                with open(self.results_file, 'r') as f:
                    self.results = json.load(f)
                print(f"Analysis results loaded: {self.results_file}")
            except Exception as e:
                print(f"Results file loading error: {e}")
                
        # Sonuç yoksa ama veri varsa, temel metrikleri oluştur
        if self.results is None and self.df is not None and not self.df.empty:
            print("Results file not found, basic metrics will be calculated")
            self._create_basic_metrics()
    
    def _create_basic_metrics(self):
        """Calculate basic metrics when CSV is loaded (if results file is missing)"""
        if self.df is None or self.df.empty:
            print("Data not found, basic metrics cannot be created")
            return
            
        print("Basic metrics are being created...")
            
        # Basit bir sonuç sözlüğü oluştur
        self.results = {
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "product_name": self.data_file.split('/')[-1].split('_Products_')[0] if self.data_file else "Bilinmiyor",
            "metrics": {},
            "visualizations": {}
        }
        
        # Temel metrikleri hesapla
        metrics = {}
        
        # Toplam ürün
        metrics["total_products"] = len(self.df)
        
        # Fiyat istatistikleri
        try:
            # Sayısal fiyat alanını oluştur - daha güçlü hale getirilmiş
            self.df['price_numeric'] = self.df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            self.df['price_numeric'] = pd.to_numeric(self.df['price_numeric'], errors='coerce')
            self.df['price_numeric'].fillna(0, inplace=True)
            
            metrics["average_price"] = float(self.df['price_numeric'].mean())
            metrics["min_price"] = float(self.df['price_numeric'].min())
            metrics["max_price"] = float(self.df['price_numeric'].max())
            print(f"Fiyat istatistikleri hesaplandı: Ort: ${metrics['average_price']:.2f}, Min: ${metrics['min_price']:.2f}, Max: ${metrics['max_price']:.2f}")
        except Exception as e:
            print(f"Fiyat hesaplama hatası: {e}")
            metrics["average_price"] = 0
            metrics["min_price"] = 0
            metrics["max_price"] = 0
            
        # Değerlendirme istatistikleri
        try:
            metrics["average_rating"] = float(self.df['productRating'].mean())
            metrics["total_reviews"] = int(self.df['productReviewCount'].sum())
            print(f"Review statistics calculated: Avg. Rating: {metrics['average_rating']:.2f}, Total: {metrics['total_reviews']:,}")
        except Exception as e:
            print(f"Review calculation error: {e}")
            metrics["average_rating"] = 0
            metrics["total_reviews"] = 0
            
        # Sözcük bulutu oluşturma
        try:
            wordcloud_base64 = self._get_wordcloud_image()
            if wordcloud_base64:
                self.results["visualizations"]["wordcloud_image"] = wordcloud_base64
                print("Wordcloud created")
        except Exception as e:
            print(f"Wordcloud creation error: {e}")
            
        self.results["metrics"] = metrics
        print("Basic metrics created successfully")
    
    def create_dashboard(self):
        """Create the dashboard layout and callbacks."""
        app = Dash(__name__, 
                 assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets'),
                 title="Amazon Product Analysis Dashboard")
        
        # Define dark theme colors
        dark_bg = "#121212"
        dark_card_bg = "#1E1E1E"
        dark_text = "#E0E0E0"
        dark_secondary_text = "#AAAAAA"
        dark_accent = "#BB86FC"  # Purple accent
        dark_secondary_accent = "#03DAC6"  # Teal accent
        
        # Define the app layout with dark theme
        app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Amazon Product Analysis Dashboard", className="dashboard-title"),
                html.Div([
                    html.Span("Analysis Time: ", className="header-label"),
                    html.Span(self.results.get("analysis_time", "Unknown") if self.results else "No Data", 
                             className="header-value")
                ], className="header-item"),
                html.Div([
                    html.Span("Product: ", className="header-label"),
                    html.Span(self.results.get("product_name", "Unknown") if self.results else "No Data", 
                             className="header-value")
                ], className="header-item")
            ], className="dashboard-header"),
            
            # Metrics Cards Row
            html.Div([
                html.Div([
                    html.H3("Total Products"),
                    html.Div(
                        str(self.results.get("metrics", {}).get("total_products", "N/A")) if self.results else "No Data",
                        className="metric-value"
                    )
                ], className="metric-card"),
                
                html.Div([
                    html.H3("Average Price"),
                    html.Div(
                        f"${self.results.get('metrics', {}).get('average_price', 'N/A'):.2f}" 
                        if self.results and self.results.get('metrics', {}).get('average_price') 
                        else "No Data",
                        className="metric-value"
                    )
                ], className="metric-card"),
                
                html.Div([
                    html.H3("Average Rating"),
                    html.Div([
                        html.Span(
                            f"{self.results.get('metrics', {}).get('average_rating', 'N/A'):.1f}" 
                            if self.results and self.results.get('metrics', {}).get('average_rating') is not None
                            else "No Data",
                            className="metric-value"
                        ),
                        html.Span(" / 5", className="metric-unit")
                    ], className="metric-value-container")
                ], className="metric-card"),
                
                html.Div([
                    html.H3("Total Reviews"),
                    html.Div(
                        f"{int(self.results.get('metrics', {}).get('total_reviews', 0)):,}" 
                        if self.results and self.results.get('metrics', {}).get('total_reviews') is not None
                        else "No Data",
                        className="metric-value"
                    )
                ], className="metric-card"),
            ], className="metrics-container"),
            
            # Tabs
            dcc.Tabs([
                # Overview Tab
                dcc.Tab(label="Overview", children=[
                    html.Div([
                        html.Div([
                            html.Div([
                                html.H2("Price and Rating Distribution"),
                                dcc.Graph(
                                    id="scatterplot",
                                    figure=self._create_scatter_plot(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card", style={'width': '50%'}),
                            
                            html.Div([
                                html.H2("Price Distribution"),
                                dcc.Graph(
                                    id="price-distribution",
                                    figure=self._create_price_distribution(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card", style={'width': '50%'}),
                        ], className="graph-row", style={'display': 'flex', 'flexDirection': 'row', 'gap': '20px'}),
                        
                        html.Div([
                            html.Div([
                                html.H2("Rating Distribution"),
                                dcc.Graph(
                                    id="rating-distribution",
                                    figure=self._create_rating_distribution(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card", style={'width': '50%'}),
                            
                            html.Div([
                                html.H2("Most Popular Products"),
                                dcc.Graph(
                                    id="top-products",
                                    figure=self._create_top_products_chart(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card", style={'width': '50%'}),
                        ], className="graph-row", style={'display': 'flex', 'flexDirection': 'row', 'gap': '20px'}),
                        
                        html.Div([
                            html.Div([
                                html.H2("Frequently Used Words in Product Titles"),
                                html.Img(
                                    id="wordcloud-img",
                                    src=self._get_wordcloud_image(),
                                    className="wordcloud-image"
                                ) if self.results and "wordcloud_image" in self.results.get("visualizations", {}) else
                                html.Div("Word cloud could not be created", className="no-data-message")
                            ], className="wordcloud-card", style={'width': '100%'}),
                        ], className="graph-row"),
                    ], className="tab-content", style={"backgroundColor": dark_bg}),
                ]),
                
                # Products Tab
                dcc.Tab(label="Products", children=[
                    html.Div([
                        html.H2("Product List"),
                        html.Div([
                            dcc.Input(
                                id="search-input",
                                type="text",
                                placeholder="Search products...",
                                className="search-input"
                            ),
                            html.Button("Search", id="search-button", className="search-button"),
                        ], className="search-container"),
                        
                        html.Div(id="product-list", children=self._create_product_list()),
                    ], className="tab-content")
                ], style={"backgroundColor": dark_bg}),
                
                # Price Analysis Tab
                dcc.Tab(label="Price Analysis", children=[
                    html.Div([
                        html.Div([
                            html.Div([
                                html.H2("Price Range Distribution"),
                                dcc.Graph(
                                    id="price-range-chart",
                                    figure=self._create_price_range_chart(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card-full", style={'width': '100%', 'marginBottom': '20px'}),
                            
                            html.Div([
                                html.H2("Price Box Plot"),
                                dcc.Graph(
                                    id="price-boxplot",
                                    figure=self._create_price_boxplot(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card-full", style={'width': '100%'}),
                        ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}),
                    ], className="tab-content")
                ], style={"backgroundColor": dark_bg}),
                
                # Rating Analysis Tab
                dcc.Tab(label="Rating Analysis", children=[
                    html.Div([
                        html.Div([
                            html.Div([
                                html.H2("Products by Rating Score"),
                                dcc.Graph(
                                    id="rating-chart",
                                    figure=self._create_rating_chart(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card-full", style={'width': '100%', 'marginBottom': '20px'}),
                            
                            html.Div([
                                html.H2("High Rated Products (4.0+)"),
                                dcc.Graph(
                                    id="high-rated-products",
                                    figure=self._create_high_rated_products_chart(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card-full", style={'width': '100%'}),
                        ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}),
                    ], className="tab-content")
                ], style={"backgroundColor": dark_bg}),
                
                # Correlations Tab
                dcc.Tab(label="Correlations", children=[
                    html.Div([
                        html.Div([
                            html.Div([
                                html.H2("Price and Rating Correlation"),
                                dcc.Graph(
                                    id="price-rating-correlation",
                                    figure=self._create_price_rating_correlation(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card-full", style={'width': '100%', 'marginBottom': '20px'}),
                            
                            html.Div([
                                html.H2("Price and Review Count Correlation"),
                                dcc.Graph(
                                    id="price-review-correlation",
                                    figure=self._create_price_review_correlation(),
                                    config={'displayModeBar': True, 'responsive': True}
                                )
                            ], className="graph-card-full", style={'width': '100%'}),
                        ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}),
                    ], className="tab-content")
                ], style={"backgroundColor": dark_bg}),
            ], className="tabs-container", colors={
                "border": dark_accent,
                "primary": dark_accent,
                "background": dark_bg
            }),
            
            # Footer
            html.Footer([
                html.P([
                    "Amazon Review Analyzer Dashboard | Report Generated: ",
                    html.Span(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ])
            ], className="dashboard-footer")
        ], className="dashboard-container", style={
            "backgroundColor": dark_bg,
            "color": dark_text
        })
        
        # Add callbacks
        @app.callback(
            Output("product-list", "children"),
            [Input("search-button", "n_clicks")],
            [State("search-input", "value")],
            prevent_initial_call=True
        )
        def search_products(n_clicks, search_term):
            if not n_clicks or not search_term or not self.df is not None:
                return self._create_product_list()
                
            filtered_df = self.df[self.df['title'].str.contains(search_term, case=False, na=False)]
            return self._create_product_list(filtered_df)
        
        self.app = app
    
    def _create_scatter_plot(self):
        """Create a scatter plot of price vs. rating."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="No data found", template="plotly_dark")
            
        # Clean and prepare data
        plot_df = self.df.copy()
        
        # Convert price to numeric - handle non-numeric prices better
        try:
            # Extract price value using regex and more robust handling
            plot_df['price_numeric'] = plot_df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            # Convert to float, handle missing values
            plot_df['price_numeric'] = pd.to_numeric(plot_df['price_numeric'], errors='coerce')
            # Replace NaN values with 0
            plot_df['price_numeric'].fillna(0, inplace=True)
        except Exception as e:
            print(f"Price conversion error: {e}")
            plot_df['price_numeric'] = 0
        
        try:
            # Create scatter plot
            fig = px.scatter(
                plot_df,
                x="price_numeric",
                y="productRating",
                size="productReviewCount",
                color="productRating",
                hover_name="title",
                size_max=40,
                color_continuous_scale=px.colors.sequential.Plasma,
                template="plotly_dark"
            )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Price and Rating Relationship",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                xaxis_title="Price ($)",
                yaxis_title="Rating Score",
                xaxis={'tickprefix': '$'},
                yaxis={'range': [0, 5.5]},
                coloraxis_colorbar=dict(
                    title="Rating"
                ),
                legend_title="Review Count",
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=500
            )
            
            return fig
        except Exception as e:
            print(f"Scatter plot creation error: {e}")
            return go.Figure().update_layout(
                title="Price and Rating Relationship - Error processing data",
                template="plotly_dark",
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=500
            )
    
    def _create_price_distribution(self):
        """Create a histogram of price distribution."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="No data found", template="plotly_dark")
            
        # Clean and prepare data
        plot_df = self.df.copy()
        
        # Convert price to numeric - handle non-numeric prices better
        try:
            # Extract price value using regex and more robust handling
            plot_df['price_numeric'] = plot_df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            # Convert to float, handle missing values
            plot_df['price_numeric'] = pd.to_numeric(plot_df['price_numeric'], errors='coerce')
            # Replace NaN values with 0
            plot_df['price_numeric'].fillna(0, inplace=True)
        except Exception as e:
            print(f"Price conversion error: {e}")
            plot_df['price_numeric'] = 0
        
        try:
            # Create histogram
            fig = px.histogram(
                plot_df,
                x="price_numeric",
                nbins=20,
                color_discrete_sequence=['#BB86FC'],
                template="plotly_dark"
            )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Price Distribution",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                xaxis_title="Price ($)",
                yaxis_title="Product Count",
                xaxis={'tickprefix': '$'},
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=400
            )
            
            # Add mean price line
            mean_price = plot_df['price_numeric'].mean()
            if pd.notna(mean_price):
                fig.add_vline(
                    x=mean_price, 
                    line_dash="dash", 
                    line_color="#03DAC6",
                    annotation_text=f"Avg: ${mean_price:.2f}",
                    annotation_position="top right",
                    annotation_font_color="#03DAC6"
                )
            
            return fig
        except Exception as e:
            print(f"Price distribution chart creation error: {e}")
            return go.Figure().update_layout(
                title="Price Distribution - Error processing data",
                template="plotly_dark",
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=400
            )
    
    def _create_rating_distribution(self):
        """Create a bar chart of rating distribution."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="No data found", template="plotly_dark")
            
        # Count ratings by score
        rating_counts = self.df.groupby('productRating').size().reset_index(name='count')
        
        # Create bar chart
        fig = px.bar(
            rating_counts,
            x="productRating",
            y="count",
            color="productRating",
            color_continuous_scale=px.colors.sequential.Plasma,
            template="plotly_dark"
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': "Rating Score Distribution",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 18}
            },
            xaxis_title="Rating Score",
            yaxis_title="Product Count",
            coloraxis_showscale=False,
            paper_bgcolor='rgba(30,30,30,0.8)',
            plot_bgcolor='rgba(30,30,30,0.8)',
            height=400
        )
        
        return fig
    
    def _create_top_products_chart(self):
        """Create a bar chart of top products by review count."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="Veri bulunamadı")
            
        # Get top 10 products by review count
        top_products = self.df.sort_values('productReviewCount', ascending=False).head(10)
        
        # Truncate long titles
        top_products['short_title'] = top_products['title'].apply(lambda x: x[:40] + '...' if len(x) > 40 else x)
        
        # Create bar chart
        fig = px.bar(
            top_products,
            x="productReviewCount",
            y="short_title",
            color="productRating",
            color_continuous_scale=px.colors.sequential.Viridis,
            orientation='h',
            template="plotly_white"
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': "En Çok Değerlendirilen 10 Ürün",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 18}
            },
            xaxis_title="Review Count",
            yaxis_title="Product Title",
            yaxis={'categoryorder': 'total ascending'},
            coloraxis_colorbar=dict(
                title="Rating"
            ),
            plot_bgcolor='rgba(240,240,240,0.2)',
            height=500
        )
        
        return fig
    
    def _get_wordcloud_image(self):
        """Get the base64 encoded wordcloud image."""
        if self.results and "visualizations" in self.results and "wordcloud_image" in self.results["visualizations"]:
            return self.results["visualizations"]["wordcloud_image"]
        
        # If no wordcloud in results but we have titles, generate one
        if self.df is not None and 'title' in self.df.columns and not self.df.empty:
            try:
                # Extract product titles for text analysis
                titles = self.df['title'].dropna()
                titles_text = ' '.join(titles.astype(str)).lower()
                
                # Set stopwords
                stopwords = set(STOPWORDS)
                stopwords.update(['br', 'href', 'www', 'http', 'com', 'amazon'])
                
                # Generate dark theme wordcloud
                wordcloud = WordCloud(
                    background_color='#121212',
                    max_words=100,
                    stopwords=stopwords,
                    max_font_size=50,
                    width=800,
                    height=400,
                    colormap='viridis',
                    prefer_horizontal=0.9,
                    relative_scaling=0.5,
                    min_font_size=10,
                    random_state=42
                ).generate(titles_text)
                
                # Convert to base64
                img = BytesIO()
                wordcloud.to_image().save(img, format='PNG')
                img.seek(0)
                
                print("Generated dark-themed word cloud")
                return 'data:image/png;base64,' + base64.b64encode(img.getvalue()).decode()
            except Exception as e:
                print(f"Error generating word cloud: {e}")
                return None
        
        return None
    
    def _create_product_list(self, df=None):
        """Create a list of product cards."""
        if df is None:
            df = self.df
            
        if df is None or df.empty:
            return html.Div("No product data found", className="no-data-message")
            
        # Create product cards
        product_cards = []
        for _, row in df.iterrows():
            product_cards.append(
                html.Div([
                    html.H3(row['title'], className="product-title"),
                    html.Div([
                        html.Div([
                            html.Span("ASIN: ", className="product-label"),
                            html.Span(row['productASIN'], className="product-value")
                        ]),
                        html.Div([
                            html.Span("Price: ", className="product-label"),
                            html.Span(row['productPrice'], className="product-value")
                        ]),
                        html.Div([
                            html.Span("Rating: ", className="product-label"),
                            html.Span(f"{row['productRating']:.1f}/5.0", className="product-value")
                        ]),
                        html.Div([
                            html.Span("Review Count: ", className="product-label"),
                            html.Span(f"{int(row['productReviewCount']):,}", className="product-value")
                        ]),
                    ], className="product-details"),
                    html.A("View on Amazon", href=row['url'], target="_blank", className="product-link")
                ], className="product-card")
            )
            
        return product_cards
    
    def _create_price_range_chart(self):
        """Create a bar chart of price ranges."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="No data found", template="plotly_dark")
            
        # Clean and prepare data
        plot_df = self.df.copy()
        
        # Convert price to numeric - handle non-numeric prices better
        try:
            # Extract price value using regex and more robust handling
            plot_df['price_numeric'] = plot_df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            # Convert to float, handle missing values
            plot_df['price_numeric'] = pd.to_numeric(plot_df['price_numeric'], errors='coerce')
            # Replace NaN values with 0
            plot_df['price_numeric'].fillna(0, inplace=True)
        except Exception as e:
            print(f"Price conversion error: {e}")
            plot_df['price_numeric'] = 0
        
        # Create price bins with proper error handling
        max_price = plot_df['price_numeric'].max()
        if pd.isna(max_price) or max_price <= 0:
            max_price = 1000  # Default max if data issues
        
        # Make sure bins are monotonically increasing
        price_bins = [0, 50, 100, 200, 500, 1000]
        # Only add the max_price+1 bin if it's larger than the last bin
        if max_price > price_bins[-1]:
            price_bins.append(max_price + 1)
            price_labels = ['0-50', '51-100', '101-200', '201-500', '501-1000', '1000+']
        else:
            price_labels = ['0-50', '51-100', '101-200', '201-500', '501-1000']
        
        try:
            plot_df['price_range'] = pd.cut(plot_df['price_numeric'], bins=price_bins, labels=price_labels)
            price_range_counts = plot_df.groupby('price_range').size().reset_index(name='count')
            
            # Create bar chart
            fig = px.bar(
                price_range_counts,
                x="price_range",
                y="count",
                color="price_range",
                color_discrete_sequence=px.colors.sequential.Plasma,
                template="plotly_dark"
            )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Price Range Distribution",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                xaxis_title="Price Range ($)",
                yaxis_title="Product Count",
                coloraxis_showscale=False,
                showlegend=False,
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=450
            )
            
            return fig
        except Exception as e:
            print(f"Price range chart creation error: {e}")
            # Return empty figure if binning fails
            return go.Figure().update_layout(
                title="Price Range Distribution - Error processing data",
                template="plotly_dark",
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=450
            )
    
    def _create_price_boxplot(self):
        """Create a box plot of prices."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="No data found", template="plotly_dark")
            
        # Clean and prepare data
        plot_df = self.df.copy()
        
        # Convert price to numeric - handle non-numeric prices better
        try:
            # Extract price value using regex and more robust handling
            plot_df['price_numeric'] = plot_df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            # Convert to float, handle missing values
            plot_df['price_numeric'] = pd.to_numeric(plot_df['price_numeric'], errors='coerce')
            # Replace NaN values with 0
            plot_df['price_numeric'].fillna(0, inplace=True)
        except Exception as e:
            print(f"Price conversion error: {e}")
            plot_df['price_numeric'] = 0
        
        try:
            # Create box plot
            fig = go.Figure()
            fig.add_trace(go.Box(
                y=plot_df['price_numeric'],
                name="Price",
                boxmean=True,
                marker_color='#BB86FC',
                line=dict(color='#9979DB')
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Price Distribution (Box Plot)",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                yaxis_title="Price ($)",
                yaxis={'tickprefix': '$'},
                showlegend=False,
                template="plotly_dark",
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=450
            )
            
            return fig
        except Exception as e:
            print(f"Price box plot creation error: {e}")
            return go.Figure().update_layout(
                title="Price Distribution (Box Plot) - Error processing data",
                template="plotly_dark",
                paper_bgcolor='rgba(30,30,30,0.8)',
                plot_bgcolor='rgba(30,30,30,0.8)',
                height=450
            )
    
    def _create_rating_chart(self):
        """Create a pie chart of ratings."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="Data not found")
            
        # Count ratings by score
        rating_counts = self.df.groupby('productRating').size().reset_index(name='count')
        
        try:
            # Create pie chart
            fig = px.pie(
                rating_counts,
                values="count",
                names="productRating",
                color="productRating",
                color_discrete_sequence=px.colors.sequential.Viridis,
                hole=0.4,
                template="plotly_white"
            )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Product Distribution by Rating",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                legend_title="Rating",
                plot_bgcolor='rgba(240,240,240,0.2)',
                height=450
            )
            
            # Update traces
            fig.update_traces(textinfo='percent+label')
            
            return fig
        except Exception as e:
            print(f"Rating chart creation error: {e}")
            return go.Figure().update_layout(
                title="Product Distribution by Rating - Error processing data",
                height=450
            )
    
    def _create_high_rated_products_chart(self):
        """Create a bar chart of high rated products."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="Data not found")
            
        # Get high rated products (4.0+)
        high_rated = self.df[self.df['productRating'] >= 4.0].sort_values('productReviewCount', ascending=False).head(10)
        
        # If no high-rated products exist
        if high_rated.empty:
            return go.Figure().update_layout(title="4.0+ değerlendirmeli ürün bulunamadı")
        
        try:
            # Truncate long titles
            high_rated['short_title'] = high_rated['title'].apply(lambda x: x[:40] + '...' if len(x) > 40 else x)
            
            # Create bar chart
            fig = px.bar(
                high_rated,
                x="short_title",
                y="productRating",
                color="productReviewCount",
                color_discrete_sequence=px.colors.sequential.Viridis,
                template="plotly_white"
            )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Yüksek Değerlendirmeli Ürünler (4.0+)",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                xaxis_title="",
                yaxis_title="Değerlendirme Puanı",
                yaxis={'range': [3.9, 5.1]},
                coloraxis_colorbar=dict(
                    title="Değ. Sayısı"
                ),
                plot_bgcolor='rgba(240,240,240,0.2)',
                height=450,
                xaxis={'tickangle': 45}
            )
            
            return fig
        except Exception as e:
            print(f"High rated products chart creation error: {e}")
            return go.Figure().update_layout(
                title="High Rated Products - Error processing data",
                height=450
            )
    
    def _create_price_rating_correlation(self):
        """Create a scatter plot of price vs rating with trend line."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="Data not found")
            
        # Clean and prepare data
        plot_df = self.df.copy()
        
        # Convert price to numeric - handle non-numeric prices better
        try:
            # Extract price value using regex and more robust handling
            plot_df['price_numeric'] = plot_df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            # Convert to float, handle missing values
            plot_df['price_numeric'] = pd.to_numeric(plot_df['price_numeric'], errors='coerce')
            # Replace NaN values with 0
            plot_df['price_numeric'].fillna(0, inplace=True)
        except Exception as e:
            print(f"Price conversion error: {e}")
            plot_df['price_numeric'] = 0
        
        try:
            # Create scatter plot with trend line
            try:
                fig = px.scatter(
                    plot_df,
                    x="price_numeric",
                    y="productRating",
                    hover_name="title",
                    trendline="ols",
                    trendline_color_override="red",
                    template="plotly_white"
                )
            except Exception as e:
                print(f"Trend line creation error: {e}")
                # Fallback without trendline
                fig = px.scatter(
                    plot_df,
                    x="price_numeric",
                    y="productRating",
                    hover_name="title",
                    template="plotly_white"
                )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Price and Rating Correlation",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                xaxis_title="Price ($)",
                yaxis_title="Rating",
                xaxis={'tickprefix': '$'},
                yaxis={'range': [0, 5.5]},
                plot_bgcolor='rgba(240,240,240,0.2)',
                height=450
            )
            
            return fig
        except Exception as e:
            print(f"Price-rating correlation chart creation error: {e}")
            return go.Figure().update_layout(
                title="Price and Rating Correlation - Error processing data",
                height=450
            )
    
    def _create_price_review_correlation(self):
        """Create a scatter plot of price vs review count with trend line."""
        if self.df is None or self.df.empty:
            return go.Figure().update_layout(title="Data not found")
            
        # Clean and prepare data
        plot_df = self.df.copy()
        
        # Convert price to numeric - handle non-numeric prices better
        try:
            # Extract price value using regex and more robust handling
            plot_df['price_numeric'] = plot_df['productPrice'].astype(str).str.extract(r'(\d+\.?\d*)')[0]
            # Convert to float, handle missing values
            plot_df['price_numeric'] = pd.to_numeric(plot_df['price_numeric'], errors='coerce')
            # Replace NaN values with 0
            plot_df['price_numeric'].fillna(0, inplace=True)
        except Exception as e:
            print(f"Price conversion error: {e}")
            plot_df['price_numeric'] = 0
        
        try:
            # Log scale for review count
            plot_df['log_review_count'] = np.log10(plot_df['productReviewCount'].astype(float) + 1)
            
            # Create scatter plot with trend line
            try:
                fig = px.scatter(
                    plot_df,
                    x="price_numeric",
                    y="productReviewCount",
                    hover_name="title",
                    trendline="ols",
                    trendline_color_override="red",
                    log_y=True,
                    template="plotly_white"
                )
            except Exception as e:
                print(f"Trend line creation error: {e}")
                # Fallback without trendline
                fig = px.scatter(
                    plot_df,
                    x="price_numeric",
                    y="productReviewCount",
                    hover_name="title",
                    log_y=True,
                    template="plotly_white"
                )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Price and Review Count Correlation",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 18}
                },
                xaxis_title="Price ($)",
                yaxis_title="Review Count (log scale)",
                xaxis={'tickprefix': '$'},
                plot_bgcolor='rgba(240,240,240,0.2)',
                height=450
            )
            
            return fig
        except Exception as e:
            print(f"Price-review count correlation chart creation error: {e}")
            return go.Figure().update_layout(
                title="Price and Review Count Correlation - Error processing data",
                height=450
            )
    
    def run_dashboard(self, debug=False, open_browser=True):
        """Create and run the dashboard."""
        if self.app is None:
            self.create_dashboard()
        
        # Create a new thread to open browser after a delay
        if open_browser:
            threading.Thread(target=self._open_browser_delayed).start()

        print(f"Dashboard started: http://127.0.0.1:{self.port}/")
        self.app.run(debug=debug, port=self.port)
        
    def _open_browser_delayed(self, delay=1.5):
        """Open browser after a short delay to allow server to start."""
        time.sleep(delay)
        webbrowser.open(f'http://127.0.0.1:{self.port}/')

def main():
    """Main function to run the dashboard."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon Dashboard')
    parser.add_argument('--data', type=str, help='Path to the product data CSV file')
    parser.add_argument('--results', type=str, help='Path to the analysis results JSON file')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the dashboard on')
    args = parser.parse_args()
    
    # Initialize dashboard
    dashboard = AmazonDashboard(args.data, args.results, args.port)
    
    # Run dashboard
    dashboard.run_dashboard()

if __name__ == "__main__":
    main() 