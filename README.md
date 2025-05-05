# 📊 Amazon Product Scraper and Analyzer

A comprehensive system for collecting, analyzing, and visualizing Amazon product data through a modern interactive dashboard.

![Dashboard](https://raw.githubusercontent.com/ozzy2438/amazon-review-scraper-analyzer/main/assets/dashboard_screenshot.png)

## 🚀 Features

- **Automated Data Collection**: Efficiently scrape product data from Amazon search results
- **Comprehensive Data Analysis**: Advanced analytics for price, rating, and review metrics
- **Interactive Dashboard**: Dynamic visualizations built with Plotly and Dash for intuitive data exploration
- **Visual Reports**: Automatically generated and professionally styled HTML reports
- **Single Command Workflow**: Streamlined process from data collection to visualization

## 📋 Requirements

- Python 3.8+
- Required libraries (listed in requirements.txt)
- Web browser (Chrome recommended)

## 🔧 Installation

1. Clone or download the project:
   ```
   git clone https://github.com/ozzy2438/amazon-review-scraper-analyzer.git
   cd amazon-review-scraper-analyzer
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Ensure Chrome WebDriver is installed (will be downloaded automatically if not present).

## 💻 Usage

### Complete Workflow

To collect data, perform analysis, and visualize results with a single command:

```bash
python run_amazon_analysis.py --search "smartphone" --pages 3 --dashboard
```

Parameters:
- `--search`: Product to search on Amazon (e.g., "smartphone")
- `--pages`: Number of pages to scrape (default: 1)
- `--dashboard`: Launch interactive dashboard after analysis
- `--port`: Specify custom port for dashboard (default: 8050)
- `--csv`: Use existing CSV file instead of scraping new data

### Running Individual Components

#### 1. Data Collection Only

```bash
python amazon_review_scraper.py --search "smartphone" --pages 3
```

#### 2. Analysis Only

```bash
python amazon_review_analyzer.py path/to/data_file.csv
```

#### 3. Dashboard Only

```bash
python amazon_dashboard.py --data path/to/data_file.csv --results path/to/results_file.json
```

## 📊 Dashboard Features

The interactive dashboard provides the following analytics and visualizations:

- **Key Metrics**: Product count, average rating, price range, and total reviews
- **Rating Distribution**: Visualization of product rating distribution
- **Price Analysis**: Price range distribution and statistics
- **Review Count Analysis**: Distribution of products by review volume
- **Price-Rating Correlation**: Analysis of relationship between price and ratings
- **Featured Products**: Highlighted products based on specific criteria
- **Word Cloud**: Common terms found in product titles

## 📂 Project Structure

```
amazon-review-scraper-analyzer/
├── amazon_review_scraper.py    # Data collection module
├── amazon_review_analyzer.py   # Data analysis and reporting module
├── amazon_dashboard.py         # Interactive dashboard module
├── run_amazon_analysis.py      # Automated workflow script
├── requirements.txt            # Dependencies list
├── amazon_products/            # Storage for collected data
├── analysis_results/           # Storage for analysis results
└── assets/                     # Dashboard style files and assets
```

## 📝 Notes

- Amazon may limit automated data collection. Avoid excessive usage.
- Large datasets may require increased memory allocation.
- The interactive dashboard will automatically open in your default web browser.
- For production use, consider implementing additional error handling and rate limiting.

## 🔄 Version History

- **v1.0.0**: Initial release
- **v1.1.0**: Added interactive dashboard
- **v1.2.0**: Improved data processing and visualization capabilities

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📁 Repository

GitHub Repository: [https://github.com/ozzy2438/amazon-review-scraper-analyzer.git](https://github.com/ozzy2438/amazon-review-scraper-analyzer.git) 