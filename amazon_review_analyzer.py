import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from textblob import TextBlob
from wordcloud import WordCloud, STOPWORDS
from collections import Counter
import re
from datetime import datetime
import json
import sys
import warnings

# Dashboard entegrasyonu için eklenen import
try:
    from amazon_dashboard import AmazonDashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    print("Warning: Dashboard components not found, interactive dashboard will not be available.")

warnings.filterwarnings('ignore')

class AmazonReviewAnalyzer:
    def __init__(self, watch_folder="amazon_products", output_folder="analysis_results"):
        """Initialize the analyzer with folders to watch and save results."""
        self.watch_folder = watch_folder
        self.output_folder = output_folder
        self.processed_files = set()
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
    
    def monitor_folder(self, interval=5):
        """Monitor the folder for new CSV files and process them."""
        print(f"Monitoring folder: {self.watch_folder} for new Amazon product CSV files...")
        
        while True:
            try:
                # Get all CSV files in the watch folder
                csv_files = [f for f in os.listdir(self.watch_folder) 
                           if f.endswith('.csv') and 'Products' in f]
                
                # Process new files
                for csv_file in csv_files:
                    file_path = os.path.join(self.watch_folder, csv_file)
                    
                    # Skip already processed files
                    if file_path in self.processed_files:
                        continue
                    
                    # Check if file is not being written to (file size stable)
                    if self.is_file_ready(file_path):
                        print(f"\n{'='*50}")
                        print(f"New file detected: {csv_file}")
                        print(f"Starting analysis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Process the file
                        self.process_file(file_path)
                        
                        # Mark as processed
                        self.processed_files.add(file_path)
                        print(f"{'='*50}\n")
            
            except Exception as e:
                print(f"Error monitoring folder: {e}")
            
            # Wait before checking again
            time.sleep(interval)
    
    def is_file_ready(self, file_path, checks=3, interval=1):
        """Check if file is complete and not being written to."""
        size1 = os.path.getsize(file_path)
        for _ in range(checks):
            time.sleep(interval)
            size2 = os.path.getsize(file_path)
            if size1 != size2:  # File still being written
                return False
            size1 = size2
        return True
    
    def process_file(self, file_path):
        """Process a single CSV file of Amazon products."""
        try:
            # Extract product name from filename
            file_name = os.path.basename(file_path)
            product_name = file_name.split('_Products_')[0].replace('_', ' ')
            
            # Load the data
            print(f"Loading data from {file_path}...")
            df = pd.read_csv(file_path)
            print(f"Loaded {len(df)} product entries")
            
            # Prepare data for analysis
            self.prepare_data(df)
            
            # Generate analysis and visualizations
            analysis_results = self.analyze_products(df, product_name)
            
            # Save results
            self.save_results(df, analysis_results, product_name)
            
            print(f"Analysis completed for {file_name}")
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
    
    def prepare_data(self, df):
        """Clean and prepare the data for analysis."""
        # Convert date to datetime if exists
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            except:
                # Try a different approach if standard conversion fails
                df['date'] = df['date'].astype(str)
                date_pattern = r'(\w+ \d+, \d{4})'
                df['date'] = df['date'].str.extract(date_pattern)
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convert rating to numeric if exists
        if 'rating' in df.columns:
            df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        
        # Convert product rating to numeric
        if 'productRating' in df.columns:
            df['productRating'] = pd.to_numeric(df['productRating'], errors='coerce')
        
        # Convert product review count to numeric
        if 'productReviewCount' in df.columns:
            df['productReviewCount'] = pd.to_numeric(df['productReviewCount'], errors='coerce')
        
        # Convert helpful votes to numeric
        if 'helpful' in df.columns:
            df['helpful_votes'] = pd.to_numeric(df['helpful'], errors='coerce')
        
        # Convert verified purchase to boolean
        if 'verifiedPurchase' in df.columns:
            if df['verifiedPurchase'].dtype == bool:
                pass  # Already boolean
            else:
                df['verifiedPurchase'] = df['verifiedPurchase'].map({'true': True, 'false': False, True: True, False: False})
        
        # Clean up product price
        if 'productPrice' in df.columns:
            df['productPrice'] = df['productPrice'].astype(str)
            # Extract price value
            df['price_numeric'] = df['productPrice'].str.extract(r'(\d+\.?\d*)').astype(float)
        
        # Add sentiment analysis for product title
        if 'title' in df.columns:
            df['title_sentiment'] = df['title'].astype(str).apply(self.get_sentiment)
        
        # Add sentiment analysis for review text
        if 'review' in df.columns:
            df['review_length'] = df['review'].astype(str).apply(len)
            df['sentiment_score'] = df['review'].astype(str).apply(self.get_sentiment)
            df['sentiment_category'] = pd.cut(
                df['sentiment_score'], 
                bins=[-1, -0.3, 0.3, 1], 
                labels=['Negative', 'Neutral', 'Positive']
            )

    def get_sentiment(self, text):
        """Calculate sentiment score for a text."""
        try:
            return TextBlob(str(text)).sentiment.polarity
        except:
            return 0
    
    def analyze_products(self, df, product_name):
        """Analyze product data and generate visualizations."""
        results = {
            "product_name": product_name,
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {},
            "visualizations": {}
        }
        
        # 1. Basic metrics
        results["metrics"]["total_products"] = len(df)
        
        # NaN değerlerini null olarak değiştir
        avg_rating = df['productRating'].mean() if 'productRating' in df.columns and not df['productRating'].empty else None
        results["metrics"]["average_rating"] = None if pd.isna(avg_rating) else avg_rating
        
        avg_review = df['productReviewCount'].mean() if 'productReviewCount' in df.columns and not df['productReviewCount'].empty else None 
        results["metrics"]["average_review_count"] = None if pd.isna(avg_review) else avg_review
        
        # Calculate price metrics if price data available
        if 'price_numeric' in df.columns:
            price_data = df['price_numeric'].dropna()
            if not price_data.empty:
                results["metrics"]["average_price"] = price_data.mean()
                results["metrics"]["min_price"] = price_data.min()
                results["metrics"]["max_price"] = price_data.max()
        
        # 2. Create visualizations
        figure_paths = []
        
        # 2.1. Rating distribution
        if 'productRating' in df.columns:
            plt.figure(figsize=(10, 6))
            sns.histplot(df['productRating'].dropna(), bins=5, kde=True)
            plt.title(f'Product Rating Distribution for {product_name}', fontsize=14)
            plt.xlabel('Rating (Stars)')
            plt.ylabel('Number of Products')
            
            rating_dist_path = os.path.join(self.output_folder, f"{product_name}_rating_dist.png".replace(' ', '_'))
            plt.tight_layout()
            plt.savefig(rating_dist_path)
            plt.close()
            figure_paths.append(rating_dist_path)
        
        # 2.2. Price distribution
        if 'price_numeric' in df.columns and df['price_numeric'].notna().any():
            plt.figure(figsize=(10, 6))
            sns.histplot(df['price_numeric'].dropna(), kde=True)
            plt.title(f'Price Distribution for {product_name}', fontsize=14)
            plt.xlabel('Price ($)')
            plt.ylabel('Number of Products')
            
            price_dist_path = os.path.join(self.output_folder, f"{product_name}_price_dist.png".replace(' ', '_'))
            plt.tight_layout()
            plt.savefig(price_dist_path)
            plt.close()
            figure_paths.append(price_dist_path)
            
            # 2.2.1 Price vs Rating
            plt.figure(figsize=(10, 6))
            sns.scatterplot(data=df.dropna(subset=['price_numeric', 'productRating']), 
                           x='price_numeric', y='productRating', 
                           size='productReviewCount', sizes=(20, 200),
                           alpha=0.7)
            plt.title(f'Price vs. Rating for {product_name}', fontsize=14)
            plt.xlabel('Price ($)')
            plt.ylabel('Rating (Stars)')
            
            price_rating_path = os.path.join(self.output_folder, f"{product_name}_price_vs_rating.png".replace(' ', '_'))
            plt.tight_layout()
            plt.savefig(price_rating_path)
            plt.close()
            figure_paths.append(price_rating_path)
        
        # 2.3. Review count distribution
        if 'productReviewCount' in df.columns and df['productReviewCount'].notna().any():
            plt.figure(figsize=(10, 6))
            # Use log scale for better visualization if there's high variance
            has_reviews = df['productReviewCount'] > 0
            if has_reviews.any():
                sns.histplot(df.loc[has_reviews, 'productReviewCount'], log_scale=True)
                plt.title(f'Review Count Distribution for {product_name} (Log Scale)', fontsize=14)
                plt.xlabel('Number of Reviews (Log Scale)')
                plt.ylabel('Number of Products')
                
                review_count_path = os.path.join(self.output_folder, f"{product_name}_review_count.png".replace(' ', '_'))
                plt.tight_layout()
                plt.savefig(review_count_path)
                plt.close()
                figure_paths.append(review_count_path)
        
        # 2.4. Word cloud of product titles
        if 'title' in df.columns:
            titles_text = " ".join(df['title'].astype(str))
            stopwords = set(STOPWORDS)
            stopwords.update(['br', 'href', 'www', 'http', 'com', 'amazon'])
            
            wordcloud_image = None
            if titles_text and len(titles_text.strip()) > 0:
                try:
                    # Create a WordCloud of product titles
                    print("Generating word cloud from product titles...")
                    wordcloud = WordCloud(
                        background_color='white',
                        max_words=100,
                        stopwords=stopwords,
                        max_font_size=50,
                        width=800,
                        height=400
                    ).generate(titles_text)
                    
                    plt.figure(figsize=(10, 8))
                    plt.imshow(wordcloud, interpolation='bilinear')
                    plt.axis('off')
                    plt.title(f'Most Common Words in {product_name} Titles', fontsize=14)
                    
                    wordcloud_path = os.path.join(self.output_folder, f"{product_name}_title_wordcloud.png".replace(' ', '_'))
                    plt.tight_layout()
                    plt.savefig(wordcloud_path)
                    plt.close()
                    figure_paths.append(wordcloud_path)
                except ValueError as e:
                    print(f"Warning: Could not generate wordcloud - {str(e)}")
                    print("Continuing analysis without wordcloud...")
            else:
                print("Warning: Not enough text data for wordcloud generation. Skipping.")
                wordcloud_image = None
        
        # 3. Collect key insights
        results["insights"] = self.generate_product_insights(df, product_name)
        
        # 4. Add visualization paths
        results["visualizations"] = figure_paths
        
        return results
    
    def generate_product_insights(self, df, product_name):
        """Generate key insights from the product data."""
        insights = []
        
        # Basic metrics
        insights.append(f"Total products analyzed: {len(df)}")
        
        # Rating insights
        if 'productRating' in df.columns and df['productRating'].notna().any():
            avg_rating = df['productRating'].mean()
            insights.append(f"Average product rating: {avg_rating:.2f} out of 5.0 stars")
            
            # Highest rated products
            if len(df) > 1:
                top_rated = df.nlargest(3, 'productRating')
                insights.append("Top rated products:")
                for idx, row in top_rated.iterrows():
                    insights.append(f"- {row['title'][:50]}... ({row['productRating']} stars)")
        
        # Price insights
        if 'price_numeric' in df.columns and df['price_numeric'].notna().any():
            price_data = df['price_numeric'].dropna()
            if not price_data.empty:
                avg_price = price_data.mean()
                min_price = price_data.min()
                max_price = price_data.max()
                
                insights.append(f"Price range: ${min_price:.2f} - ${max_price:.2f}")
                insights.append(f"Average price: ${avg_price:.2f}")
                
                # Best value (highest rating for price)
                if 'productRating' in df.columns and df['productRating'].notna().any():
                    df['value_score'] = df['productRating'] / df['price_numeric']
                    best_value = df.dropna(subset=['value_score']).nlargest(1, 'value_score')
                    if not best_value.empty:
                        best_val_row = best_value.iloc[0]
                        insights.append(f"Best value: {best_val_row['title'][:50]}... " +
                                      f"(${best_val_row['price_numeric']:.2f}, {best_val_row['productRating']} stars)")
        
        # Review count insights
        if 'productReviewCount' in df.columns and df['productReviewCount'].notna().any():
            review_counts = df['productReviewCount'].dropna()
            if not review_counts.empty:
                total_reviews = review_counts.sum()
                most_reviewed = df.nlargest(1, 'productReviewCount')
                if not most_reviewed.empty:
                    most_rev_row = most_reviewed.iloc[0]
                    insights.append(f"Most reviewed: {most_rev_row['title'][:50]}... " +
                                  f"({int(most_rev_row['productReviewCount'])} reviews)")
                insights.append(f"Total reviews across all products: {int(total_reviews)}")
        
        return insights
    
    def save_results(self, df, analysis_results, product_name):
        """Save the analysis results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = product_name.replace(' ', '_')
        
        # 1. Save comprehensive analysis report (HTML)
        report_path = os.path.join(self.output_folder, f"{base_name}_report_{timestamp}.html")
        self.generate_html_report(df, analysis_results, report_path)
        
        # 2. Save summary in JSON format
        summary_path = os.path.join(self.output_folder, f"{base_name}_summary_{timestamp}.json")
        with open(summary_path, 'w') as f:
            json.dump(analysis_results, f, indent=4)
        
        # 3. Save key metrics to CSV
        metrics_path = os.path.join(self.output_folder, f"{base_name}_metrics_{timestamp}.csv")
        metrics_df = pd.DataFrame([analysis_results["metrics"]])
        metrics_df.to_csv(metrics_path, index=False)
        
        print(f"Analysis results saved to:\n- {report_path}\n- {summary_path}\n- {metrics_path}")
        
        # 4. Return the paths for potential dashboard launch
        return {
            'report': report_path,
            'summary': summary_path,
            'metrics': metrics_path,
            'data': df
        }
    
    def generate_html_report(self, df, analysis_results, output_path):
        """Generate a comprehensive HTML report."""
        product_name = analysis_results["product_name"]
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Amazon Product Analysis: {product_name}</title>
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
            <style>
                :root {{
                    --primary-color: #232F3E;
                    --secondary-color: #FF9900;
                    --text-color: #333;
                    --bg-color: #f9f9f9;
                    --card-bg: #fff;
                    --border-color: #ddd;
                    --accent-color: #37475A;
                    --success-color: #188038;
                    --info-color: #1967D2;
                    --warning-color: #E37400;
                    --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Roboto', sans-serif;
                    line-height: 1.6;
                    color: var(--text-color);
                    background-color: var(--bg-color);
                    padding: 0;
                    margin: 0;
                }}
                
                .dashboard {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0;
                }}
                
                header {{
                    background-color: var(--primary-color);
                    color: white;
                    padding: 20px 40px;
                    border-bottom: 4px solid var(--secondary-color);
                }}
                
                .header-content {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .logo {{
                    display: flex;
                    align-items: center;
                }}
                
                .logo i {{
                    font-size: 24px;
                    margin-right: 10px;
                    color: var(--secondary-color);
                }}
                
                .header-title {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: 700;
                }}
                
                .header-subtitle {{
                    font-size: 14px;
                    opacity: 0.8;
                    margin-top: 4px;
                }}
                
                .container {{
                    padding: 30px;
                }}
                
                .section-title {{
                    font-size: 22px;
                    color: var(--primary-color);
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid var(--secondary-color);
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                }}
                
                .section-title i {{
                    margin-right: 10px;
                    color: var(--secondary-color);
                }}
                
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                
                .metric-card {{
                    background-color: var(--card-bg);
                    border-radius: 8px;
                    box-shadow: var(--shadow);
                    padding: 20px;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    border-top: 4px solid var(--secondary-color);
                }}
                
                .metric-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
                }}
                
                .metric-icon {{
                    font-size: 18px;
                    background-color: var(--secondary-color);
                    color: white;
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 15px;
                }}
                
                .metric-value {{
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--primary-color);
                    margin: 10px 0;
                }}
                
                .metric-label {{
                    font-size: 14px;
                    color: #666;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .insights-card {{
                    background-color: var(--card-bg);
                    border-radius: 8px;
                    box-shadow: var(--shadow);
                    padding: 25px;
                    margin-bottom: 40px;
                }}
                
                .insight-item {{
                    display: flex;
                    align-items: flex-start;
                    margin-bottom: 15px;
                    padding-bottom: 15px;
                    border-bottom: 1px solid var(--border-color);
                }}
                
                .insight-item:last-child {{
                    margin-bottom: 0;
                    padding-bottom: 0;
                    border-bottom: none;
                }}
                
                .insight-icon {{
                    margin-right: 15px;
                    font-size: 16px;
                    color: var(--secondary-color);
                }}
                
                .insight-text {{
                    flex: 1;
                }}
                
                .visualizations-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
                    gap: 30px;
                    margin-bottom: 40px;
                }}
                
                @media (max-width: 650px) {{
                    .visualizations-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
                
                .viz-card {{
                    background-color: var(--card-bg);
                    border-radius: 8px;
                    box-shadow: var(--shadow);
                    overflow: hidden;
                }}
                
                .viz-header {{
                    padding: 15px 20px;
                    background-color: var(--accent-color);
                    color: white;
                }}
                
                .viz-title {{
                    margin: 0;
                    font-size: 16px;
                    font-weight: 500;
                }}
                
                .viz-body {{
                    padding: 20px;
                    text-align: center;
                }}
                
                .viz-body img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 4px;
                }}
                
                .product-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 40px;
                    background-color: var(--card-bg);
                    box-shadow: var(--shadow);
                    border-radius: 8px;
                    overflow: hidden;
                }}
                
                .product-table th {{
                    background-color: var(--accent-color);
                    color: white;
                    padding: 15px;
                    text-align: left;
                    font-weight: 500;
                }}
                
                .product-table td {{
                    padding: 12px 15px;
                    border-bottom: 1px solid var(--border-color);
                }}
                
                .product-table tr:last-child td {{
                    border-bottom: none;
                }}
                
                .product-table tr:nth-child(even) {{
                    background-color: #f2f7ff;
                }}
                
                .rating-pill {{
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 12px;
                    font-weight: 500;
                    font-size: 12px;
                    color: white;
                }}
                
                .price-tag {{
                    font-weight: 500;
                    color: var(--secondary-color);
                }}
                
                .reviews-tag {{
                    background-color: #f2f2f2;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 12px;
                    color: #666;
                }}
                
                footer {{
                    background-color: var(--primary-color);
                    color: white;
                    text-align: center;
                    padding: 20px;
                    margin-top: 40px;
                    font-size: 14px;
                }}
                
                .highlight {{
                    color: var(--secondary-color);
                    font-weight: 500;
                }}
            </style>
        </head>
        <body>
            <div class="dashboard">
                <header>
                    <div class="header-content">
                        <div class="logo">
                            <i class="fab fa-amazon"></i>
                            <div>
                                <h1 class="header-title">Amazon Product Analysis: {product_name}</h1>
                                <p class="header-subtitle">Analysis generated on {analysis_results["analysis_time"]}</p>
                            </div>
                        </div>
                    </div>
                </header>
                
                <div class="container">
                    <h2 class="section-title"><i class="fas fa-chart-line"></i> Key Metrics</h2>
                    <div class="metrics-grid">
        """
        
        # Add metrics cards with icons
        icons = {
            "total_products": "fas fa-box",
            "average_rating": "fas fa-star",
            "min_price": "fas fa-tag",
            "max_price": "fas fa-tags",
            "average_price": "fas fa-dollar-sign",
            "average_review_count": "fas fa-comments",
        }
        
        colors = {
            "total_products": "#FF9900",  # Amazon Orange
            "average_rating": "#FFC107",  # Yellow
            "min_price": "#4CAF50",       # Green
            "max_price": "#F44336",       # Red
            "average_price": "#2196F3",   # Blue
            "average_review_count": "#9C27B0",  # Purple
        }
        
        for k, v in analysis_results["metrics"].items():
            if v is not None:
                icon = icons.get(k, "fas fa-chart-bar")
                color = colors.get(k, "#FF9900")
                
                # Format the value properly
                if k.startswith("price") or k == "average_price":
                    formatted_value = f"${v:.2f}"
                elif isinstance(v, float):
                    formatted_value = f"{v:.2f}"
                else:
                    formatted_value = f"{v}"
                
                label = k.replace("_", " ").title()
                
                html += f"""
                    <div class="metric-card">
                        <div class="metric-icon" style="background-color: {color}">
                            <i class="{icon}"></i>
                        </div>
                        <div class="metric-value">{formatted_value}</div>
                        <div class="metric-label">{label}</div>
                    </div>
                """
        
        html += """
                    </div>
                    
                    <h2 class="section-title"><i class="fas fa-lightbulb"></i> Key Insights</h2>
                    <div class="insights-card">
        """
        
        # Add insights with icons
        insight_icons = [
            "fas fa-chart-pie",
            "fas fa-star",
            "fas fa-tags",
            "fas fa-trophy",
            "fas fa-dollar-sign",
            "fas fa-comment-dots",
            "fas fa-percentage"
        ]
        
        for i, insight in enumerate(analysis_results["insights"]):
            icon = insight_icons[i % len(insight_icons)]
            html += f"""
                <div class="insight-item">
                    <div class="insight-icon">
                        <i class="{icon}"></i>
                    </div>
                    <div class="insight-text">{insight}</div>
                </div>
            """
        
        html += """
                    </div>
                    
                    <h2 class="section-title"><i class="fas fa-chart-bar"></i> Visualizations</h2>
                    <div class="visualizations-grid">
        """
        
        # Add visualization cards
        for viz_path in analysis_results["visualizations"]:
            viz_name = os.path.basename(viz_path)
            viz_title = viz_name.replace('_', ' ').replace('.png', '').title()
            
            # Get relative path for HTML
            rel_path = os.path.relpath(viz_path, os.path.dirname(output_path))
            
            html += f"""
                <div class="viz-card">
                    <div class="viz-header">
                        <h3 class="viz-title">{viz_title}</h3>
                    </div>
                    <div class="viz-body">
                        <img src="{rel_path}" alt="{viz_title}">
                    </div>
                </div>
            """
        
        html += """
                    </div>
                    
                    <h2 class="section-title"><i class="fas fa-list"></i> Sample Products</h2>
                    <table class="product-table">
                        <thead>
                            <tr>
                                <th>Title</th>
                                <th>ASIN</th>
                                <th>Rating</th>
                                <th>Reviews</th>
                                <th>Price</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Get a sample of products (make sure we have varied ratings if possible)
        sample_size = min(10, len(df))
        
        # Try to get a diverse sample with different ratings
        if 'productRating' in df.columns and df['productRating'].nunique() > 1:
            # Group by rating
            rating_groups = df.groupby('productRating')
            
            # Sample from each rating group
            sample_df = pd.DataFrame()
            for _, group in rating_groups:
                group_sample = group.sample(min(2, len(group)))
                sample_df = pd.concat([sample_df, group_sample])
            
            # If we need more samples, take random ones
            if len(sample_df) < sample_size:
                remaining = sample_size - len(sample_df)
                extra_samples = df.drop(sample_df.index).sample(min(remaining, len(df) - len(sample_df)))
                sample_df = pd.concat([sample_df, extra_samples])
            
            # If we have too many, take a random subset
            if len(sample_df) > sample_size:
                sample_df = sample_df.sample(sample_size)
        else:
            # Just take a random sample
            sample_df = df.sample(sample_size)
        
        for _, row in sample_df.iterrows():
            title = row.get('title', '-')
            if len(str(title)) > 40:
                title = str(title)[:40] + '...'
                
            # Generate a color for the rating pill based on rating value
            rating = row.get('productRating', 0)
            if isinstance(rating, (int, float)):
                if rating >= 4.5:
                    rating_color = "#4CAF50"  # Green
                elif rating >= 4.0:
                    rating_color = "#8BC34A"  # Light Green
                elif rating >= 3.0:
                    rating_color = "#FFC107"  # Amber
                elif rating >= 2.0:
                    rating_color = "#FF9800"  # Orange
                else:
                    rating_color = "#F44336"  # Red
            else:
                rating_color = "#9E9E9E"  # Grey
                
            html += f"""
                <tr>
                    <td>{title}</td>
                    <td>{row.get('productASIN', '-')}</td>
                    <td><span class="rating-pill" style="background-color: {rating_color}">{row.get('productRating', '-')}</span></td>
                    <td><span class="reviews-tag">{row.get('productReviewCount', '-')}</span></td>
                    <td><span class="price-tag">{row.get('productPrice', '-')}</span></td>
                </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
                
                <footer>
                    <p>Report generated by <span class="highlight">Amazon Product Analyzer</span> | Data from Amazon.com</p>
                </footer>
            </div>
        </body>
        </html>
        """
        
        # Save HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

def main():
    print("Starting Amazon Product Analyzer...")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Amazon Product Analyzer")
    parser.add_argument('file_path', nargs='?', help='Path to CSV file to analyze')
    parser.add_argument('--dashboard', action='store_true', help='Launch interactive dashboard after analysis')
    args = parser.parse_args()
    
    # Check if a file was passed as an argument
    if args.file_path:
        # If a specific file is provided, analyze it directly
        file_path = args.file_path
        if os.path.exists(file_path) and file_path.endswith('.csv'):
            print(f"Analyzing specific file: {file_path}")
            analyzer = AmazonReviewAnalyzer()
            df = pd.read_csv(file_path)
            
            # Extract product name from filename
            file_name = os.path.basename(file_path)
            product_name = file_name.split('_Products_')[0].replace('_', ' ')
            
            # Prepare data for analysis
            analyzer.prepare_data(df)
            
            # Generate analysis and visualizations
            analysis_results = analyzer.analyze_products(df, product_name)
            
            # Save results and get paths
            result_paths = analyzer.save_results(df, analysis_results, product_name)
            
            print("Analysis completed!")
            
            # Launch dashboard if requested
            if args.dashboard and DASHBOARD_AVAILABLE:
                print("\nLaunching interactive dashboard...")
                try:
                    dashboard = AmazonDashboard(
                        data_path=file_path,
                        analysis_results=result_paths['summary'],
                        port=8050
                    )
                    dashboard.run_dashboard(debug=False)
                except Exception as e:
                    print(f"Error launching dashboard: {e}")
        else:
            print(f"Error: {file_path} is not a valid CSV file")
    else:
        # If no specific file, monitor the folder
        print("No specific file provided. Starting folder monitoring...")
        watch_folder = "amazon_products"  # Default folder
        
        # Create watch folder if it doesn't exist
        if not os.path.exists(watch_folder):
            os.makedirs(watch_folder)
            
        analyzer = AmazonReviewAnalyzer(watch_folder=watch_folder)
        analyzer.monitor_folder()

# Automatically trigger analyzer after scraper finishes
def run_after_scraper_completes():
    """Run the analyzer automatically after scraper completes"""
    import subprocess
    import os
    import time
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Analyzer after Scraper")
    parser.add_argument('--dashboard', action='store_true', help='Launch interactive dashboard after analysis')
    args = parser.parse_args()
    
    # Check if the scraper is already running
    try:
        # Run the scraper
        print("Starting Amazon Review Scraper...")
        scraper_process = subprocess.Popen(["python", "amazon_review_scraper.py"], 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE, 
                                          text=True)
        
        # Wait for scraper to complete
        stdout, stderr = scraper_process.communicate()
        
        if scraper_process.returncode == 0:
            print("Scraper completed successfully!")
            print("Starting analyzer automatically...")
            
            # Find the most recent CSV file in the amazon_products folder
            products_folder = "amazon_products"
            if not os.path.exists(products_folder):
                print(f"Warning: {products_folder} folder not found")
                return
                
            csv_files = [f for f in os.listdir(products_folder) if f.endswith('.csv')]
            if not csv_files:
                print("No CSV files found to analyze")
                return
                
            # Sort by creation time, newest first
            csv_files.sort(key=lambda x: os.path.getctime(os.path.join(products_folder, x)), reverse=True)
            latest_csv = os.path.join(products_folder, csv_files[0])
            
            # Run the analyzer on the most recent file
            print(f"Analyzing most recent file: {latest_csv}")
            
            # Build command with dashboard flag if requested
            cmd = ["python", "amazon_review_analyzer.py", latest_csv]
            if args.dashboard:
                cmd.append("--dashboard")
                
            subprocess.call(cmd)
            
        else:
            print("Scraper encountered an error:")
            print(stderr)
    
    except Exception as e:
        print(f"Error running automation: {e}")

if __name__ == "__main__":
    # Add support for argparse
    import argparse
    
    # Check if we should run the auto-sequence
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        run_after_scraper_completes()
    else:
        main()
