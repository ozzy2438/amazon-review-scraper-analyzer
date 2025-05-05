#!/usr/bin/env python3
"""
Amazon Product Scraper and Analyzer
-----------------------------------
This script runs the Amazon product scraper and then automatically starts the analyzer.
"""

import os
import sys
import time
import subprocess
from datetime import datetime
import argparse
import webbrowser
import threading
# from amazon_review_scraper import search_amazon
from amazon_review_analyzer import AmazonReviewAnalyzer

def print_header(message):
    """Print a formatted header message"""
    print(f"\n{'='*60}")
    print(f" {message}")
    print(f"{'='*60}\n")

def run_scraper(search_term=None, num_pages=1):
    """Run the Amazon product scraper"""
    print_header("1) Amazon Product Scraper Starting")
    
    cmd = ["python", "amazon_review_scraper.py"]
    
    # Add arguments if provided
    if search_term:
        cmd.extend(["--search", search_term])
    if num_pages:
        cmd.extend(["--pages", str(num_pages)])
    
    # Run the scraper
    print(f"Command running: {' '.join(cmd)}")
    
    # Real-time output
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Real-time output
    for line in process.stdout:
        print(line, end='')
    
    # İşlemin tamamlanmasını bekle
    process.wait()
    
    if process.returncode == 0:
        print("Scraper completed successfully!")
        return True
    else:
        print(f"Scraper failed!")
        return False

def get_latest_csv_file():
    """Get the path to the most recently created CSV file in amazon_products folder"""
    products_folder = "amazon_products"
    if not os.path.exists(products_folder):
        print(f"Warning: {products_folder} folder not found")
        return None
        
    csv_files = [f for f in os.listdir(products_folder) if f.endswith('.csv')]
    if not csv_files:
        print("CSV file not found")
        return None
        
    # Sort by creation time, newest first
    csv_files.sort(key=lambda x: os.path.getctime(os.path.join(products_folder, x)), reverse=True)
    latest_csv = os.path.join(products_folder, csv_files[0])
    
    print(f"Latest created CSV: {latest_csv}")
    return latest_csv

def run_analyzer(csv_file):
    """Run the Amazon review analyzer on a specific CSV file"""
    print_header("2) Amazon Analiz Programı Başlatılıyor")
    
    if not csv_file:
        print("CSV file not found to analyze")
        return False
    
    # Run the analyzer
    cmd = ["python", "amazon_review_analyzer.py", csv_file]
    print(f"Command running: {' '.join(cmd)}")
    
    # Real-time output
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Real-time output
    for line in process.stdout:
        print(line, end='')
    
    # Wait for the process to complete
    process.wait()
    
    if process.returncode == 0:
        print("Analysis completed successfully!")
        return True
    else:
        print(f"Analysis failed!")
        return False

def get_latest_results():
    """Get the paths to the most recently created HTML report and JSON results"""
    results_folder = "analysis_results"
    if not os.path.exists(results_folder):
        print(f"Warning: {results_folder} folder not found")
        return None, None
    
    # Find the most recent HTML report
    html_files = [f for f in os.listdir(results_folder) if f.endswith('.html')]
    latest_html = None
    if html_files:
        html_files.sort(key=lambda x: os.path.getctime(os.path.join(results_folder, x)), reverse=True)
        latest_html = os.path.join(results_folder, html_files[0])
    
    # Find the most recent JSON summary
    json_files = [f for f in os.listdir(results_folder) if f.endswith('.json')]
    latest_json = None
    if json_files:
        json_files.sort(key=lambda x: os.path.getctime(os.path.join(results_folder, x)), reverse=True)
        latest_json = os.path.join(results_folder, json_files[0])
    
    return latest_html, latest_json

def open_dashboard(csv_file, json_file=None, port=8050):
    """Open the interactive dashboard"""
    print_header("3) Interactive Dashboard Starting")
    
    if not csv_file:
        print("CSV file not found for dashboard")
        return False
    
    try:
        # Run the dashboard directly
        from amazon_dashboard import AmazonDashboard
        print(f"CSV file: {csv_file}")
        print(f"JSON file: {json_file}")
        print(f"Port: {port}")
        
        dashboard = AmazonDashboard(csv_file, json_file, port=port)
        dashboard.run_dashboard(open_browser=True)
        return True
    except Exception as e:
        print(f"Error opening dashboard: {e}")
        return False

def open_html_report(html_file):
    """Open HTML report in the default browser"""
    print_header("3) Analysis Report Opening")
    
    if not html_file:
        print("HTML report file not found")
        return False
    
    try:
        print(f"Report file opening: {html_file}")
        # Convert to absolute path if needed
        abs_path = os.path.abspath(html_file)
        webbrowser.open(f'file://{abs_path}')
        print("Report opened in browser!")
        return True
    except Exception as e:
        print(f"Error opening report: {e}")
        return False

def run_analysis(args):
    """Run the analysis pipeline."""
    # Start time
    start_time = datetime.now()
    print(f"Analysis started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Scrape products
    if args.csv:
        print(f"Using existing CSV file: {args.csv}")
        product_file = args.csv
    else:
        print(f"Scraping products for '{args.search}' ({args.pages} pages)...")
        # Scrape the products using run_scraper, not search_amazon
        success = run_scraper(args.search, args.pages)
        if not success:
            print("Error: Scraping failed")
            return None
        # Get the latest CSV file
        product_file = get_latest_csv_file()
    
    if not product_file or not os.path.exists(product_file):
        print("Error: No product data available for analysis")
        return
    
    # Step 2: Analyze data if needed (sadece dashboard isteniyorsa atlayalım)
    latest_html = None
    latest_json = None
    
    if not args.dashboard_only:
        print("\nAnalyzing product data...")
        success = run_analyzer(product_file)
        if not success:
            print("Error: Analysis failed")
        
        # Get the latest results
        latest_html, latest_json = get_latest_results()
    
    # Step 3: Run dashboard if requested
    if args.dashboard or args.dashboard_only:
        print("\nStarting dashboard...")
        try:
            # Önerilen port
            dashboard_port = args.port if args.port else 8050
            
            # Dashboard'u doğrudan başlat
            dashboard_success = open_dashboard(product_file, latest_json, dashboard_port)
            if not dashboard_success:
                print("Dashboard başlatılamadı, HTML raporu açılıyor...")
                if latest_html:
                    open_html_report(latest_html)
        except Exception as e:
            print(f"Error starting dashboard: {e}")
            if latest_html:
                open_html_report(latest_html)
    elif latest_html:
        # HTML raporu tarayıcıda aç
        open_html_report(latest_html)
    
    # End time
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\nAnalysis completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total duration: {duration.total_seconds():.2f} seconds")
    
    return latest_json

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Amazon Product Analysis Workflow")
    parser.add_argument("--search", type=str, help="Product to search for on Amazon")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--dashboard", action="store_true", help="Use in    teractive dashboard")
    parser.add_argument("--dashboard_only", action="store_true", help="Run only dashboard, skip analysis")
    parser.add_argument("--csv", type=str, help="CSV file to use")
    parser.add_argument("--port", type=int, help="Port to use for dashboard")
    args = parser.parse_args()
    
    # Print welcome message
    print("\n" + "="*60)
    print(" Amazon Product Analysis System".center(60))
    print(" " + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(58))
    print("="*60 + "\n")
    
    # Run the analysis
    run_analysis(args)
    
    print("\nAmazon Product Analysis Workflow completed!")

if __name__ == "__main__":
    main() 