from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException
import csv
import time
import os
import re
import sys
import random
import json
from datetime import datetime
import argparse
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

def setup_driver():
    """Set up and return a Chrome WebDriver."""
    chrome_options = Options()
    # Add options for headless browser if needed
    # chrome_options.add_argument("--headless")  # Headless modu kapat, interaktif moda al
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Initialize Chrome WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Mask automation
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Add a delay to make it look more human
    time.sleep(2)
    
    return driver

def scroll_to_element(driver, element):
    """Scroll element into view using JavaScript."""
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
    time.sleep(1.5)  # Small delay to allow scrolling to complete

def safe_click(driver, element, wait_time=3, attempts=3):
    """Safely click an element with retries and different strategies."""
    for attempt in range(attempts):
        try:
            # First scroll the element into view
            scroll_to_element(driver, element)
            
            # Try direct click
            element.click()
            time.sleep(wait_time)
            return True
        except (ElementClickInterceptedException, ElementNotInteractableException) as e:
            print(f"Click intercepted on attempt {attempt+1}, trying alternative methods...")
            
            try:
                # Try JavaScript click as alternative
                driver.execute_script("arguments[0].click();", element)
                time.sleep(wait_time)
                return True
            except Exception:
                # Try using ActionChains if JavaScript click fails
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(driver)
                    actions.move_to_element(element).click().perform()
                    time.sleep(wait_time)
                    return True
                except Exception:
                    # If we're on the last attempt, try to get past any overlays
                    if attempt == attempts - 1:
                        try:
                            # Try to click any potential "close" buttons on overlays
                            close_buttons = driver.find_elements(By.CSS_SELECTOR, 
                                "[aria-label='Close'], .close-button, .dismiss-button, button:contains('Continue'), button:contains('No thanks')")
                            for btn in close_buttons:
                                try:
                                    btn.click()
                                    time.sleep(1.5)
                                except:
                                    pass
                            
                            # Try one more direct click
                            element.click()
                            time.sleep(wait_time)
                            return True
                        except:
                            pass
        except Exception as e:
            print(f"Error clicking element: {e}")
        
        # Wait before retrying
        time.sleep(2)
    
    return False

def search_amazon(search_term, num_pages=1):
    """Search Amazon for products and scrape results."""
    print(f"Searching Amazon for: {search_term}")
    
    try:
        driver = setup_driver()
        
        # Create folder if it doesn't exist
        if not os.path.exists("amazon_products"):
            os.makedirs("amazon_products")
        
        # Prepare product data storage
        all_products = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Go to Amazon homepage
            driver.get("https://www.amazon.com")
            print("Loading: Amazon homepage ")
            time.sleep(5)  # Daha uzun bir bekleme süresi
            
            # Accept cookies if the dialog appears
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "sp-cc-accept"))
                )
                cookie_button.click()
                print("Cookies accepted")
                time.sleep(2)
            except:
                print("Cookie notice not found or already accepted")
            
            # Search for the term
            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
                )
                search_box.clear()
                search_box.send_keys(search_term)
                search_box.submit()
                print(f"Search performed: {search_term}")
                time.sleep(3)  # Daha uzun bir bekleme süresi
            except Exception as e:
                print(f"Search box not found: {e}")
                
            # Process each page of results
            for page in range(1, num_pages + 1):
                print(f"\nProcessing page {page}/{num_pages}...")
                
                # Wait for products to load with explicit wait
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']"))
                    )
                    time.sleep(5)  # Sayfanın tamamen yüklenmesi için ekstra bekleme
                except Exception as e:
                    print(f"Products not loaded: {e}")
                    # Refresh the page and try again
                    driver.refresh()
                    time.sleep(7)
                    
                # Random scrolling to simulate human behavior and load dynamic content
                scroll_page_randomly(driver)
                
                # Find all product elements
                try:
                    product_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']"))
                    )
                    print(f"{len(product_elements)} products found")
                    
                    # Alternative selector if the first one doesn't work
                    if not product_elements:
                        product_elements = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
                        print(f"Alternative selector found {len(product_elements)} products")
                        
                    # Process each product
                    for product_element in product_elements:
                        try:
                            product_data = extract_product_data(product_element)
                            if product_data:
                                all_products.append(product_data)
                                print(f"Product added: {product_data.get('title', 'Unknown product')[:40]}...")
                        except Exception as e:
                            print(f"Error extracting product data: {e}")
                            
                except Exception as e:
                    print(f"Products not found: {e}")
                
                # Go to next page if not on the last page
                if page < num_pages:
                    try:
                        next_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".s-pagination-next"))
                        )
                        
                        # Scroll to the next button and click
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(2)
                        next_button.click()
                        
                        print("Moving to next page...")
                        time.sleep(5)  # Daha uzun bir bekleme süresi
                    except Exception as e:
                        print(f"Failed to move to next page: {e}")
                        break
        
        except Exception as e:
            print(f"Error during search: {e}")
        
        # Save data to CSV
        if all_products:
            # Format the search term for filename
            search_term_formatted = search_term.replace(" ", "_")
            
            # Create filename with timestamp
            csv_filename = f"amazon_products/{search_term_formatted}_Products_{timestamp}.csv"
            
            # Convert to DataFrame and save
            products_df = pd.DataFrame(all_products)
            products_df.to_csv(csv_filename, index=False)
            
            print(f"\nProduct data saved successfully: {csv_filename}")
            print(f"Total {len(all_products)} products saved")
            
            return csv_filename
        else:
            print("\nNo product data to save")
            return None
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    
    finally:
        try:
            # Close the browser
            driver.quit()
            print("Browser closed")
        except:
            print("Error closing browser")

def scroll_page_randomly(driver):
    """Scroll the page randomly to simulate human behavior and load dynamic content."""
    print("Simulating human behavior by randomly scrolling the page...")
    
    # Get page height
    page_height = driver.execute_script("return document.body.scrollHeight")
    
    # Random number of scroll actions (3-7)
    num_scrolls = random.randint(3, 7)
    
    for i in range(num_scrolls):
        # Random scroll position
        scroll_to = random.randint(100, page_height)
        driver.execute_script(f"window.scrollTo(0, {scroll_to});")
        
        # Random pause between scrolls (0.5-2.5 seconds)
        time.sleep(random.uniform(0.5, 2.5))
        
    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

def extract_product_data(product_element):
    """Extract product data from product element."""
    try:
        print("Extracting product data...")
        
        # Get the HTML structure for debugging
        html = product_element.get_attribute('outerHTML')
        print(f"Element HTML structure (first 100 characters): {html[:100]}...")
        
        # Initialize variables with default values to avoid UnboundLocalError
        title = "Unknown Product"
        asin = f"unknown_{int(time.time())}"
        url = "https://www.amazon.com"
        price = "N/A"
        rating = 0.0
        review_count = 0
        date = datetime.now().strftime("%B %d, %Y")  # Default to today's date
        
        # Find title - try multiple selectors
        title_selectors = [
            "h2 a span",
            ".a-size-medium.a-color-base.a-text-normal",
            ".a-size-base-plus.a-color-base.a-text-normal",
            ".a-link-normal .a-text-normal",
            ".a-link-normal.s-underline-text.s-underline-link-text"
        ]
        
        for selector in title_selectors:
            try:
                title_element = product_element.find_element(By.CSS_SELECTOR, selector)
                title = title_element.text.strip()
                if title:  # Found a valid title, break the loop
                    print(f"Title found: {title[:40]}...")
                    break
            except:
                continue
        
        # If title is still empty, try more aggressively
        if not title:
            try:
                # Just find any text in the card that might be a title
                candidates = product_element.find_elements(By.CSS_SELECTOR, ".a-text-normal")
                for c in candidates:
                    if c.text and len(c.text) > 10:  # Reasonable title length
                        title = c.text
                        print(f"Alternative title found: {title[:40]}...")
                        break
            except:
                pass
        
        # Find ASIN (Amazon Standard Identification Number)
        try:
            # Extract ASIN from element data-asin attribute
            asin = product_element.get_attribute('data-asin')
            if not asin:
                # Try to extract from another attribute
                asin = product_element.get_attribute('data-cel-widget').split('_')[1]
            print(f"ASIN found: {asin}")
        except:
            asin = f"unknown_{int(time.time())}"
            print(f"ASIN not found, default value created: {asin}")
        
        # Find URL
        try:
            url_element = product_element.find_element(By.CSS_SELECTOR, "h2 a, .a-link-normal")
            url = url_element.get_attribute('href')
            print(f"URL found: {url[:50]}...")
        except:
            # Attempt to construct URL from ASIN
            if asin and asin.startswith('B0'):
                url = f"https://www.amazon.com/dp/{asin}"
                print(f"URL created: {url}")
        
        # Find price
        price_selectors = [
            ".a-price .a-offscreen",
            ".a-price-whole",
            ".a-color-base.a-text-normal",
            ".a-price",
            ".a-price .a-price-symbol"
        ]
        
        for selector in price_selectors:
            try:
                price_element = product_element.find_element(By.CSS_SELECTOR, selector)
                price = price_element.text.strip() or price_element.get_attribute("textContent").strip()
                if price and ('$' in price or ',' in price or '.' in price):
                    print(f"Price found: {price}")
                    break
            except:
                continue
        
        # Find rating
        try:
            rating_element = product_element.find_element(By.CSS_SELECTOR, ".a-icon-alt")
            rating_text = rating_element.get_attribute('textContent') or rating_element.text
            if 'out of' in rating_text.lower() or '5' in rating_text:
                # Extract numeric rating value
                rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
                    print(f"Rating found: {rating}")
            
            # Try alternative selectors if above didn't work
            if not rating or rating == 0:
                rating_element = product_element.find_element(By.CSS_SELECTOR, ".a-icon-star .a-icon-alt")
                rating_text = rating_element.get_attribute('textContent')
                rating = float(rating_text.split(' ')[0])
                print(f"Alternative rating found: {rating}")
        except:
            print("Rating not found")
        
        # Find review count
        try:
            review_element = product_element.find_element(By.CSS_SELECTOR, ".a-size-base.s-underline-text")
            review_text = review_element.text.strip() or review_element.get_attribute("textContent").strip()
            if review_text:
                # Extract numeric value
                review_match = re.search(r'(\d+[,\d+]*)', review_text)
                if review_match:
                    review_count_str = review_match.group(1).replace(',', '')
                    review_count = int(review_count_str)
                    print(f"Review count found: {review_count}")
        except:
            try:
                # Alternative selector for review count
                review_element = product_element.find_element(By.CSS_SELECTOR, "a[href*='customerReviews']")
                review_text = review_element.text.strip() or review_element.get_attribute("textContent").strip()
                if review_text:
                    review_match = re.search(r'(\d+[,\d+]*)', review_text)
                    if review_match:
                        review_count_str = review_match.group(1).replace(',', '')
                        review_count = int(review_count_str)
                        print(f"Alternative review count found: {review_count}")
            except:
                print("Review count not found")
        
        # Create product data dictionary
        product_data = {
            "title": title,
            "productASIN": asin,
            "productPrice": price,
            "productRating": rating,
            "productReviewCount": review_count,
            "url": url,
            "date": date  # Add current date
        }
        
        print(f"Product data extracted: {product_data}")
        return product_data
        
    except Exception as e:
        print(f"Error extracting product data: {e}")
        # Return a minimal product data with the error
        return {
            "title": f"Error: {str(e)[:50]}",
            "productASIN": f"error_{int(time.time())}",
            "productPrice": "N/A",
            "productRating": 0,
            "productReviewCount": 0,
            "url": "https://www.amazon.com",
            "date": datetime.now().strftime("%B %d, %Y")
        }

def main():
    """Main function to run the scraper."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon Product Scraper')
    parser.add_argument('--search', type=str, help='Search term for Amazon products')
    parser.add_argument('--pages', type=int, default=1, help='Number of pages to scrape (default: 1)')
    parser.add_argument('--output', type=str, default='amazon_products', help='Output folder (default: amazon_products)')
    args = parser.parse_args()
    
    # Print welcome message
    print("="*60)
    print("Amazon Product Scraper".center(60))
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
    print("="*60)
    
    # Get search term from command line or user input
    search_term = args.search
    if not search_term:
        search_term = input("\nEnter Amazon search term: ")
    
    # Get number of pages from command line or user input
    num_pages = args.pages
    if num_pages <= 0:
        num_pages_input = input("\nEnter number of pages to scrape (default: 1): ")
        num_pages = int(num_pages_input) if num_pages_input.strip() else 1
    
    print(f"\nStarting Amazon product scrape for: '{search_term}' - {num_pages} page(s)")
    
    # Run the scraper
    output_file = search_amazon(search_term, num_pages)
    
    print("\n" + "="*60)
    print("Scraping Complete!".center(60))
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
    print("="*60)
    
    return output_file

if __name__ == "__main__":
    main()
