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

def setup_driver():
    """Set up and return the Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Start maximized
    chrome_options.add_argument("--disable-notifications")  # Disable notifications
    
    # Add user agent to appear more like a real user
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
    
    # Disable automation flags to avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execution of CDP commands to hide automation
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """
    })
    
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

def search_amazon(driver, product_term):
    """Navigate to Amazon and search for the product term."""
    print(f"Navigating to Amazon.com to search for '{product_term}'...")
    
    # Try up to 3 times to navigate to Amazon and search
    for attempt in range(3):
        try:
            # Clear cookies and refresh
            driver.delete_all_cookies()
            
            # Navigate to Amazon
            driver.get("https://www.amazon.com")
            time.sleep(5)  # Wait for page to load fully
            
            # Take a screenshot for debugging
            driver.save_screenshot("amazon_home.png")
            print(f"Saved Amazon homepage screenshot (attempt {attempt+1})")
            
            # Check for any popups or dialogs and try to close them
            try:
                popup_selectors = [
                    ".a-popover-header-close", 
                    "#nav-main-close", 
                    ".a-button-close",
                    ".a-closebutton",
                    ".a-close-button"
                ]
                
                for selector in popup_selectors:
                    close_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in close_buttons:
                        if button.is_displayed():
                            button.click()
                            time.sleep(1)
            except:
                pass
            
            # Try multiple selectors for the search box
            search_box_selectors = [
                "#twotabsearchtextbox", 
                "input[name='field-keywords']",
                "input[type='search']",
                "input.nav-input",
                "#nav-search-keywords"
            ]
            
            search_box = None
            for selector in search_box_selectors:
                try:
                    search_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if search_box and search_box.is_displayed():
                        print(f"Found search box using selector: {selector}")
                        break
                except:
                    continue
            
            if not search_box:
                print(f"Could not find search box on attempt {attempt+1}. Retrying...")
                continue
                
            # Clear the search box and enter search term
            search_box.clear()
            time.sleep(1)
            search_box.send_keys(product_term)
            time.sleep(1)
            
            # Try different methods to submit the search
            try:
                # Method 1: Press ENTER
                search_box.send_keys(Keys.RETURN)
                print("Submitted search using ENTER key")
            except:
                try:
                    # Method 2: Click search button
                    search_button_selectors = [
                        "input[type='submit']",
                        ".nav-search-submit",
                        "#nav-search-submit-button"
                    ]
                    
                    for selector in search_button_selectors:
                        try:
                            search_button = driver.find_element(By.CSS_SELECTOR, selector)
                            if search_button.is_displayed():
                                search_button.click()
                                print(f"Clicked search button using selector: {selector}")
                                break
                        except:
                            continue
                except:
                    print("Failed to submit search using button click")
        
            # Wait for search results to load
            print("Waiting for search results to load...")
            search_result_selectors = [
                ".s-result-item",
                "div[data-component-type='s-search-result']",
                ".sg-col-inner"
            ]
            
            results_found = False
            for selector in search_result_selectors:
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    results_found = True
                    print(f"Search results loaded with selector: {selector}")
                    break
                except:
                    continue
                    
            if not results_found:
                print(f"Search results did not load on attempt {attempt+1}")
                # Take a screenshot to debug
                driver.save_screenshot(f"search_failed_{attempt+1}.png")
                continue
                
            # Take a screenshot of search results
            driver.save_screenshot("search_results.png")
            print("Saved search results screenshot")
            
            # Allow additional time for all content to load
            time.sleep(5)
                
            return True
                
        except Exception as e:
            print(f"Error during search attempt {attempt+1}: {e}")
            # Take screenshot for debugging
            driver.save_screenshot(f"search_error_{attempt+1}.png")
            
            if attempt < 2:  # If not the last attempt
                print("Retrying search...")
                time.sleep(5)  # Wait before retrying
            else:
                print("All search attempts failed.")
                return False
                
    return False

def extract_product_info(driver, product_element):
    """Extract basic product information from a search result item."""
    try:
        # Extract product ID (ASIN)
        asin = product_element.get_attribute('data-asin')
        if not asin:
            # Try alternative method to find ASIN
            try:
                asin_element = product_element.find_element(By.CSS_SELECTOR, "[data-asin]")
                asin = asin_element.get_attribute('data-asin')
            except:
                # If we still can't find ASIN, check if it's in the URL
                try:
                    link_element = product_element.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
                    href = link_element.get_attribute("href")
                    asin_match = re.search(r"/dp/([A-Z0-9]{10})", href)
                    if asin_match:
                        asin = asin_match.group(1)
                except:
                    pass
        
        if not asin:
            print("Could not extract ASIN for product")
            return None
            
        # Extract product title using multiple possible selectors
        title = None
        title_selectors = [
            "h2 a span", 
            "h2 span", 
            ".a-text-normal", 
            ".a-link-normal .a-text-normal",
            ".a-size-medium",
            ".a-size-base-plus",
            "h2 a"
        ]
        
        for selector in title_selectors:
            try:
                title_element = product_element.find_element(By.CSS_SELECTOR, selector)
                title = title_element.text
                if title and len(title) > 3:  # Make sure we got a meaningful title
                    break
            except:
                continue
        
        # If we still can't find title with CSS selectors, try XPath
        if not title:
            try:
                title_element = product_element.find_element(By.XPATH, ".//h2//a")
                title = title_element.text
            except:
                # Last resort: try to get any text from the product
                try:
                    title = product_element.text.split('\n')[0]
                except:
                    title = f"Product {asin}"  # Fallback
        
        # Extract rating if available - multiple possible selectors
        rating = None
        rating_selectors = [
            "i.a-icon-star-small", 
            ".a-icon-star", 
            "[class*='a-star']", 
            ".a-icon-alt"
        ]
        
        for selector in rating_selectors:
            try:
                rating_element = product_element.find_element(By.CSS_SELECTOR, selector)
                rating_text = rating_element.get_attribute("class") or rating_element.get_attribute("aria-label") or rating_element.text
                
                # Try to extract a number from the text
                rating_match = re.search(r"(\d+\.?\d*)", rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
                    break
            except:
                continue
        
        # Extract number of reviews if available - multiple possible selectors
        num_reviews = 0
        review_count_selectors = [
            "span[aria-label*='review']", 
            "a[href*='customerReviews'] span", 
            ".a-size-base[href*='customerReviews']",
            ".a-link-normal[href*='customerReviews']"
        ]
        
        for selector in review_count_selectors:
            try:
                reviews_element = product_element.find_element(By.CSS_SELECTOR, selector)
                reviews_text = reviews_element.get_attribute("aria-label") or reviews_element.text
                
                # Extract numbers from text
                review_count_match = re.search(r"(\d+(?:,\d+)*)", reviews_text)
                if review_count_match:
                    num_reviews = int(review_count_match.group(1).replace(',', ''))
                    break
            except:
                continue
        
        # Get product URL - multiple possible approaches
        product_url = None
        try:
            link_element = product_element.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
            product_url = link_element.get_attribute("href")
            # Clean up the URL
            if '?' in product_url:
                product_url = product_url.split('?')[0]
        except:
            # If we couldn't find direct link but have ASIN, construct URL
            if asin:
                product_url = f"https://www.amazon.com/dp/{asin}"
        
        # Create the reviews URL directly from the ASIN
        reviews_url = f"https://www.amazon.com/product-reviews/{asin}"
        
        product_info = {
            "asin": asin,
            "title": title,
            "rating": rating,
            "num_reviews": num_reviews,
            "product_url": product_url,
            "reviews_url": reviews_url
        }
        
        print(f"Successfully extracted product info: {asin} - {title}")
        return product_info
    except Exception as e:
        print(f"Error extracting product info: {e}")
        return None

def extract_review_data_from_list(review_element):
    """Extract review data from a review element in the reviews list."""
    try:
        # Take a screenshot of the review element for debugging
        try:
            driver = review_element.parent
            driver.execute_script("arguments[0].style.border='2px solid red'", review_element)
        except:
            pass
            
        review_data = {}
        
        # Extract review ID if available
        try:
            review_id = review_element.get_attribute('id')
            if not review_id:
                # Try looking for a data-hook attribute
                review_id = review_element.get_attribute('data-hook')
                
            if not review_id:
                # Try looking for a data-review-id attribute
                review_id = review_element.get_attribute('data-review-id')
                
            if not review_id:
                # Generate a random ID as last resort
                review_id = f"review_{int(time.time())}_{random.randint(1000, 9999)}"
                
            review_data["reviewID"] = review_id
        except:
            review_data["reviewID"] = f"review_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Extract reviewer name - multiple possible selectors
        reviewer_name_selectors = [
            ".a-profile-name", 
            "[data-hook='review-author']",
            ".a-profile a",
            ".a-profile",
            "[data-hook='genome-widget'] .a-profile-name"
        ]
        
        for selector in reviewer_name_selectors:
            try:
                name_element = review_element.find_element(By.CSS_SELECTOR, selector)
                name = name_element.text.strip()
                if name:
                    review_data["name"] = name
                    break
            except:
                continue
                
        if "name" not in review_data:
            review_data["name"] = "Anonymous"
            
        # Extract review date - multiple possible selectors
        date_selectors = [
            "[data-hook='review-date']",
            ".review-date",
            ".review-timestamp"
        ]
        
        for selector in date_selectors:
            try:
                date_element = review_element.find_element(By.CSS_SELECTOR, selector)
                date_text = date_element.text.strip()
                if date_text:
                    # Try to extract just the date part
                    date_match = re.search(r'on\s+(.+)', date_text)
                    if date_match:
                        date_text = date_match.group(1)
                    else:
                        # Try different format
                        date_match = re.search(r'(\w+\s+\d+,\s+\d{4})', date_text)
                        if date_match:
                            date_text = date_match.group(1)
                            
                    review_data["date"] = date_text
                    break
            except:
                continue
                
        if "date" not in review_data:
            # Use current date as fallback
            now = datetime.now()
            review_data["date"] = now.strftime("%B %d, %Y")
            
        # Check if verified purchase - multiple possible selectors
        verified_selectors = [
            "[data-hook='avp-badge']",
            ".a-color-success",
            "span:contains('Verified Purchase')"
        ]
        
        review_data["verifiedPurchase"] = False  # Default
        
        for selector in verified_selectors:
            try:
                review_element.find_element(By.CSS_SELECTOR, selector)
                if "Verified Purchase" in review_element.text:
                    review_data["verifiedPurchase"] = True
                    break
            except:
                continue
                
        # Alternative verification check
        if not review_data["verifiedPurchase"] and "Verified Purchase" in review_element.text:
            review_data["verifiedPurchase"] = True
            
        # Extract rating - multiple possible selectors
        rating_selectors = [
            "[data-hook='review-star-rating'] .a-icon-alt",
            "[data-hook='cmps-review-star-rating'] .a-icon-alt",
            ".review-rating",
            ".a-icon-star"
        ]
        
        for selector in rating_selectors:
            try:
                rating_element = review_element.find_element(By.CSS_SELECTOR, selector)
                rating_text = rating_element.get_attribute("textContent") or rating_element.text
                
                # Extract the numeric rating
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
                    review_data["rating"] = rating
                    break
            except:
                continue
                
        if "rating" not in review_data:
            # Try extracting from classes
            try:
                star_element = review_element.find_element(By.CSS_SELECTOR, "[class*='a-star']")
                class_attr = star_element.get_attribute("class")
                rating_match = re.search(r'a-star-(\d+)', class_attr)
                if rating_match:
                    rating = int(rating_match.group(1))
                    review_data["rating"] = rating
            except:
                review_data["rating"] = 0  # Fallback
                
        # Extract helpfulness votes - multiple possible selectors
        helpful_selectors = [
            "[data-hook='helpful-vote-statement']",
            ".cr-vote-text",
            ".review-votes"
        ]
        
        review_data["helpful"] = 0  # Default
        
        for selector in helpful_selectors:
            try:
                helpful_element = review_element.find_element(By.CSS_SELECTOR, selector)
                helpful_text = helpful_element.text.strip()
                
                # Extract numbers from text
                helpful_match = re.search(r'(\d+(?:,\d+)*)', helpful_text)
                if helpful_match:
                    helpful_count = int(helpful_match.group(1).replace(',', ''))
                    review_data["helpful"] = helpful_count
                    break
            except:
                continue
                
        # Extract review title - multiple possible selectors
        title_selectors = [
            "[data-hook='review-title']",
            ".review-title",
            ".review-heading"
        ]
        
        for selector in title_selectors:
            try:
                title_element = review_element.find_element(By.CSS_SELECTOR, selector)
                title_text = title_element.text.strip()
                
                # Remove any "stars" text from the beginning
                title_text = re.sub(r'^(\d+\.?\d*)\s*out of\s*\d+\s*stars\.?\s*', '', title_text)
                title_text = title_text.strip()
                
                if title_text:
                    review_data["title"] = title_text
                    break
            except:
                continue
                
        if "title" not in review_data or not review_data["title"]:
            review_data["title"] = "No Title"
            
        # Extract review text - multiple possible selectors
        review_text_selectors = [
            "[data-hook='review-body']",
            ".review-text",
            ".review-text-content",
            ".a-expander-partial-collapse-content"
        ]
        
        for selector in review_text_selectors:
            try:
                text_element = review_element.find_element(By.CSS_SELECTOR, selector)
                
                # Check if there's a "Read more" or expand button
                try:
                    expand_button = text_element.find_element(By.CSS_SELECTOR, ".a-expander-prompt")
                    if expand_button.is_displayed() and expand_button.is_enabled():
                        try:
                            expand_button.click()
                            time.sleep(1)  # Wait for expansion
                        except:
                            pass
                except:
                    pass
                    
                review_text = text_element.text.strip()
                if review_text:
                    review_data["review"] = review_text
                    break
            except:
                continue
                
        if "review" not in review_data or not review_data["review"]:
            # Fallback to just taking all text from the review element
            all_text = review_element.text
            # Try to extract just the review part
            title = review_data.get("title", "")
            
            if title and title in all_text:
                # Get text after title
                review_text = all_text.split(title, 1)[1].strip()
                # Remove known elements like "Verified Purchase"
                review_text = re.sub(r'Verified Purchase', '', review_text)
                review_data["review"] = review_text
            else:
                review_data["review"] = "No review text available"
                
        # Get reviewer profile URL if available
        try:
            profile_element = review_element.find_element(By.CSS_SELECTOR, ".a-profile")
            profile_url = profile_element.get_attribute("href")
            if profile_url:
                review_data["profile"] = profile_url
            else:
                review_data["profile"] = ""
        except:
            review_data["profile"] = ""
            
        # Country is usually part of the review date text
        review_data["country"] = "US"  # Default
        if "date" in review_data:
            country_match = re.search(r'in\s+the\s+(.+)$', review_data["date"])
            if country_match:
                review_data["country"] = country_match.group(1)
                
        # Generate review link based on the product ASIN and review ID
        review_data["reviewLink"] = ""  # Default empty
        
        # Check for review images
        try:
            image_elements = review_element.find_elements(By.CSS_SELECTOR, "img.review-image")
            if image_elements:
                image_urls = []
                for img in image_elements:
                    src = img.get_attribute("src")
                    if src:
                        image_urls.append(src)
                
                review_data["reviewImage"] = ", ".join(image_urls)
            else:
                review_data["reviewImage"] = ""
        except:
            review_data["reviewImage"] = ""
            
        return review_data
    except Exception as e:
        print(f"Error extracting review data: {e}")
        return None

def scrape_search_results(driver, num_reviews_to_scrape):
    """Scrape products from search results without clicking into product pages."""
    products_scraped = 0
    products_data = []
    page_num = 1
    
    while products_scraped < num_reviews_to_scrape:
        print(f"\nArama sonuçları sayfası {page_num} işleniyor...")
        
        # Sayfanın tam yüklenmesi için ek bekleme
        time.sleep(5)
        
        # Hata ayıklama için ekran görüntüsü
        debug_screenshot = f"search_page_{page_num}.png"
        driver.save_screenshot(debug_screenshot)
        print(f"Arama sayfası ekran görüntüsü kaydedildi: {debug_screenshot}")
        
        # Tüm içeriğin yüklenmesi için yavaşça aşağı kaydırma
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(5):  # 5 adımda kaydırma
            scroll_height = (i + 1) * (last_height / 5)
            driver.execute_script(f"window.scrollTo(0, {scroll_height});")
            time.sleep(2)  # Her kaydırmadan sonra içeriğin yüklenmesi için bekleme
            
        # Sayfa başına dön
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # Ürünler için birden fazla CSS seçici dene
        product_selectors = [
            "div[data-component-type='s-search-result']", 
            ".s-result-item[data-asin]",
            ".sg-col-inner .a-section.a-spacing-base",
            ".s-main-slot > div",
            "div.rush-component"
        ]
        
        # Stale element hatalarını önlemek için önce ürün linklerini ve ASIN'leri al
        product_info_list = []
        
        for selector in product_selectors:
            try:
                product_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_elements and len(product_elements) > 0:
                    print(f"{selector} seçicisi kullanılarak {len(product_elements)} ürün bulundu")
                    
                    # Stale referansları önlemek için gerekli bilgileri hemen çıkar
                    for product in product_elements:
                        try:
                            asin = product.get_attribute('data-asin')
                            if not asin:
                                # ASIN bulmak için alternatif yöntemler
                                try:
                                    asin_element = product.find_element(By.CSS_SELECTOR, "[data-asin]")
                                    asin = asin_element.get_attribute('data-asin')
                                except:
                                    try:
                                        link_element = product.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
                                        href = link_element.get_attribute("href")
                                        asin_match = re.search(r"/dp/([A-Z0-9]{10})", href)
                                        if asin_match:
                                            asin = asin_match.group(1)
                                    except:
                                        pass
                                        
                            if not asin:
                                continue
                                
                            # Başlığı almaya çalış
                            title = None
                            for title_selector in ["h2 a span", "h2 span", ".a-text-normal", "h2 a"]:
                                try:
                                    title_element = product.find_element(By.CSS_SELECTOR, title_selector)
                                    title_text = title_element.text
                                    if title_text and len(title_text) > 3:
                                        title = title_text
                                        break
                                except:
                                    continue
                                    
                            if not title:
                                title = f"Ürün {asin}"
                                
                            # Değerlendirme ve yorum sayısını almaya çalış
                            rating = None
                            try:
                                rating_element = product.find_element(By.CSS_SELECTOR, "i.a-icon-star-small, .a-icon-star")
                                rating_text = rating_element.get_attribute("class") or rating_element.get_attribute("aria-label") or rating_element.text
                                rating_match = re.search(r"(\d+\.?\d*)", rating_text)
                                if rating_match:
                                    rating = float(rating_match.group(1))
                            except:
                                pass
                                
                            # Yorum sayısını bul
                            num_reviews = 0
                            try:
                                reviews_element = product.find_element(By.CSS_SELECTOR, "span[aria-label*='review'], a[href*='customerReviews']")
                                reviews_text = reviews_element.get_attribute("aria-label") or reviews_element.text
                                review_count_match = re.search(r"(\d+(?:,\d+)*)", reviews_text)
                                if review_count_match:
                                    num_reviews = int(review_count_match.group(1).replace(',', ''))
                            except:
                                pass
                                
                            # Ürün fiyatını almaya çalış    
                            price = None
                            try:
                                price_element = product.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen")
                                price = price_element.get_attribute("textContent")
                            except:
                                try:
                                    price_element = product.find_element(By.CSS_SELECTOR, ".a-price, .a-color-price")
                                    price = price_element.text
                                except:
                                    pass
                                
                            # Ürün URL'sini al
                            product_url = None
                            try:
                                link_element = product.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
                                product_url = link_element.get_attribute("href")
                                if '?' in product_url:
                                    product_url = product_url.split('?')[0]
                            except:
                                if asin:
                                    product_url = f"https://www.amazon.com/dp/{asin}"
                            
                            # Ürün resim URL'sini almaya çalış
                            image_url = None
                            try:
                                img_element = product.find_element(By.CSS_SELECTOR, "img.s-image")
                                image_url = img_element.get_attribute("src")
                            except:
                                pass
                                
                            # CSV örnekteki her alana bir değer ata
                            product_data = {
                                "reviewID": f"product_{asin}_{int(time.time())}",
                                "name": "Amazon Customer",  # Varsayılan değer
                                "date": datetime.now().strftime("%B %d, %Y"),  # Bugünün tarihi
                                "verifiedPurchase": False,  # Varsayılan değer
                                "rating": rating if rating else 0,
                                "helpful": num_reviews,  # Yorum sayısını helpful olarak kullan
                                "title": title,
                                "review": f"Product listing from Amazon search. Price: {price if price else 'Not available'}",
                                "profile": product_url,
                                "country": "US",
                                "reviewLink": product_url,
                                "reviewImage": image_url if image_url else "",
                                "productTitle": title,
                                "productASIN": asin,
                                "productURL": product_url,
                                "productPrice": price if price else "Not available",
                                "productRating": rating if rating else 0,
                                "productReviewCount": num_reviews
                            }
                            
                            product_info_list.append(product_data)
                            products_scraped += 1
                            print(f"Ürün bilgisi çıkarıldı: {asin} - {title[:30]}... ({products_scraped}/{num_reviews_to_scrape})")
                            
                            if products_scraped >= num_reviews_to_scrape:
                                break
                                
                        except Exception as e:
                            print(f"Ürün bilgisi çıkarılırken hata: {e}")
                            
                    if product_info_list:
                        print(f"{len(product_info_list)} ürün için başarıyla bilgiler çıkarıldı")
                        # Hepsini products_data listesine ekle
                        products_data.extend(product_info_list)
                        if products_scraped >= num_reviews_to_scrape:
                            break
                        else:
                            break  # Bir sonraki seçiciye geçme, mevcut seçici çalıştı
            except Exception as e:
                print(f"{selector} seçicisi ile ürün aranırken hata: {e}")
                
        # Yeterli ürün bulunamadıysa sonraki sayfaya git
        if products_scraped < num_reviews_to_scrape:
            next_search_page_found = navigate_to_next_search_page(driver)
            if next_search_page_found:
                page_num += 1
            else:
                print("Daha fazla arama sonucu sayfası yok veya sonraki sayfaya tıklanamadı.")
                break
        else:
            break
    
    return products_data

def navigate_to_next_search_page(driver):
    """Navigate to the next page of search results."""
    next_search_page_found = False
    search_next_selectors = [
        "a.s-pagination-next",
        "a.a-last",
        "a[aria-label='Go to next page']",
        ".a-pagination .a-last a"
    ]
    
    for selector in search_next_selectors:
        try:
            next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for next_button in next_buttons:
                # Check if this is really the "Next" button for search results
                if (next_button.is_displayed() and 
                    (next_button.text.lower() == "next" or 
                     "next" in (next_button.get_attribute("aria-label") or "").lower())):
                    
                    # Check if disabled
                    if "a-disabled" in (next_button.get_attribute("class") or ""):
                        print("Reached the last page of search results.")
                        return False
                    
                    # Try to click
                    print("Navigating to next page of search results...")
                    if safe_click(driver, next_button, wait_time=5):
                        next_search_page_found = True
                        time.sleep(5)
                        return True
        except Exception as e:
            print(f"Error finding next search page button: {e}")
            continue
    
    # Alternative method: manually construct URL for next page
    try:
        current_url = driver.current_url
        if "page=" in current_url:
            # Extract current page number and increment
            page_match = re.search(r"page=(\d+)", current_url)
            if page_match:
                current_page = int(page_match.group(1))
                next_page = current_page + 1
                next_url = re.sub(r"page=\d+", f"page={next_page}", current_url)
                print(f"Navigating to next page using URL: {next_url}")
                driver.get(next_url)
                time.sleep(5)
                return True
        else:
            # Add page=2 parameter
            if "?" in current_url:
                next_url = current_url + "&page=2"
            else:
                next_url = current_url + "?page=2"
            print(f"Navigating to page 2 using URL: {next_url}")
            driver.get(next_url)
            time.sleep(5)
            return True
    except Exception as e:
        print(f"Error navigating to next page via URL: {e}")
    
    return False

def navigate_to_next_review_page(driver):
    """Navigate to the next page of reviews."""
    next_page_found = False
    next_page_selectors = [
        "li.a-last a",
        "a[href*='pageNumber=']",
        ".a-pagination .a-last a",
        "[data-hook='pagination-next']"
    ]
    
    for selector in next_page_selectors:
        try:
            next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for next_button in next_buttons:
                # Check if this might be the "Next" button
                if next_button.is_displayed() and next_button.is_enabled():
                    # Check if the button is disabled
                    if "a-disabled" in (next_button.get_attribute("class") or "") or "Disabled" in (next_button.get_attribute("aria-label") or ""):
                        print("  Reached the last page of reviews for this product.")
                        return False
                    
                    # Try to click using our safe click method
                    if safe_click(driver, next_button, wait_time=5):
                        # Wait for the new page to load
                        time.sleep(4)
                        return True
            
        except Exception as e:
            print(f"  Error finding next review page: {e}")
            continue
    
    return False

def save_to_csv(reviews_data, product_term, output_folder="scraped_data"):
    """Save the scraped reviews to a CSV file."""
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Create a filename based on the product term and current time
    filename = os.path.join(output_folder, f"{product_term.replace(' ', '_')}_reviews_{int(time.time())}.csv")
    
    # Define the CSV header based on the sample CSV
    fieldnames = [
        "reviewID", "name", "date", "verifiedPurchase", "rating", 
        "helpful", "title", "review", "profile", "country", 
        "reviewLink", "reviewImage"
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for review in reviews_data:
                # Only include fields that are in the fieldnames
                filtered_review = {k: v for k, v in review.items() if k in fieldnames}
                writer.writerow(filtered_review)
        
        print(f"Successfully saved {len(reviews_data)} reviews to {filename}")
        return True
    except Exception as e:
        print(f"Error saving reviews to CSV: {e}")
        return False

def main():
    """Amazon Review Scraper ana fonksiyonu."""
    global product_term  # product_term değişkenini diğer fonksiyonlarda kullanabilmek için global yap
    
    print("Amazon Review Scraper Başlatılıyor...")
    try:
        # Kullanıcı girdisi al
        product_term = input("Amazon'da aranacak ürünü girin: ")
        num_reviews = input("Kaç ürün çekilecek (varsayılan: 100): ")
        num_reviews = int(num_reviews) if num_reviews.strip() else 100
        
        # Tarayıcıyı kur
        driver = setup_driver()
        
        try:
            # Amazon'da ürün ara
            search_amazon(driver, product_term)
            
            # Arama sonuçlarından ürünleri çek
            products = scrape_search_results(driver, num_reviews)
            
            if products:
                # Çıktı dizini yoksa oluştur
                output_dir = "amazon_products"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # Ürünleri CSV dosyasına kaydet
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = os.path.join(output_dir, f"Amazon_Products_{timestamp}.csv")
                
                with open(csv_filename, "w", newline="", encoding="utf-8") as csv_file:
                    # Tüm alanlarla CSV yazıcı oluştur
                    fieldnames = ["reviewID", "name", "date", "verifiedPurchase", "rating", 
                                  "helpful", "title", "review", "profile", "country", 
                                  "reviewLink", "reviewImage", "productTitle", "productASIN",
                                  "productURL", "productPrice", "productRating", "productReviewCount"]
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # Her ürünü CSV'ye yaz
                    for product in products:
                        writer.writerow(product)
                
                print(f"\nBaşarıyla {len(products)} ürün çekildi ve {csv_filename} dosyasına kaydedildi")
            else:
                print("Hiç ürün çekilemedi.")
        except Exception as e:
            print(f"Çekme işlemi sırasında bir hata oluştu: {e}")
            # Hata ayıklama için sayfanın kaynağını kaydet
            with open("error_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Hata sayfası kaynağı error_page.html dosyasına kaydedildi")
            
            # Ekran görüntüsü al
            driver.save_screenshot("error_screenshot.png")
            print("Hata ekran görüntüsü error_screenshot.png dosyasına kaydedildi")
        finally:
            # Tarayıcıyı kapat
            print("Tarayıcı kapatılıyor...")
            driver.quit()
        
    except Exception as e:
        print(f"Kurulum sırasında bir hata oluştu: {e}")
        
    print("Amazon Review Scraper tamamlandı")

if __name__ == "__main__":
    main()
