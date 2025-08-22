import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import cloudinary
import cloudinary.uploader
from typing import List, Optional
import tempfile
import shutil
import random

# Configure Cloudinary credentials
cloudinary.config(
    cloud_name='dqd7ywrxm',
    api_key=483271414334463,      # Leave None if using unsigned upload preset
    api_secret='HxsPC3cCy4ESf9nnL4mB4v4-fj8',   # Leave None if using unsigned upload preset
    secure=True
)

UPLOAD_PRESET = 'my_neighbourlink_upload'

class ImageScraper:
    def __init__(self):
        self.temp_dir = None
        
    def setup_driver(self):
        """Setup Chrome driver with stealth options"""
        options = webdriver.ChromeOptions()
        # Make it less detectable
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def google_images_search(self, driver, query: str, scrolls: int = 3) -> str:
        """Search Google Images and return page HTML with better detection avoidance"""
        try:
            search_url = f"https://www.google.com/search?tbm=isch&q={query.replace(' ', '+')}"
            print(f"Searching URL: {search_url}")
            
            driver.get(search_url)
            time.sleep(random.uniform(3, 5))  # Random delay
            
            # Check if we got blocked
            if "unusual traffic" in driver.page_source.lower():
                print("⚠️ Google detected unusual traffic. Try again later.")
                return ""
            
            # Scroll to load more images with random delays
            for i in range(scrolls):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 4))
                print(f"Scroll {i+1}/{scrolls} completed")
                
            # Try to click "Show more results" if available
            try:
                show_more = driver.find_element(By.XPATH, "//input[@value='Show more results']")
                if show_more:
                    show_more.click()
                    time.sleep(3)
            except:
                pass
                
            html = driver.page_source
            print(f"Page HTML length: {len(html)}")
            return html
            
        except Exception as e:
            print(f"Error during Google search: {str(e)}")
            return ""

    def extract_image_urls(self, html: str, max_images: int = 20) -> List[str]:
        """Extract image URLs from HTML with multiple strategies"""
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        urls = set()  # Use set to avoid duplicates
        
        # Strategy 1: Look for img tags with src
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src')
            if src and self._is_valid_image_url(src):
                urls.add(src)
        
        # Strategy 2: Look for data-src attributes
        for img in img_tags:
            data_src = img.get('data-src')
            if data_src and self._is_valid_image_url(data_src):
                urls.add(data_src)
        
        # Strategy 3: Look for Google's specific image containers
        # Google Images often uses specific div structures
        img_divs = soup.find_all('div', {'class': lambda x: x and 'rg_i' in str(x)})
        for div in img_divs:
            img = div.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src and self._is_valid_image_url(src):
                    urls.add(src)
        
        urls_list = list(urls)[:max_images]
        print(f"Extracted {len(urls_list)} unique image URLs")
        return urls_list

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL"""
        if not url or not url.startswith('http'):
            return False
        if 'base64' in url:
            return False
        if len(url) < 20:  # Too short URLs are usually not real images
            return False
        # Check for common image extensions or image-related patterns
        image_indicators = ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'imgurl', 'image']
        return any(indicator in url.lower() for indicator in image_indicators)

    def download_image(self, url: str, filename: str) -> Optional[str]:
        """Download image from URL to temp directory with better error handling"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print(f"Downloading: {url[:100]}...")
            response = requests.get(url, timeout=15, headers=headers, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type.lower():
                print(f"Not an image: {content_type}")
                return None
            
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
            # Validate downloaded file
            if os.path.getsize(filepath) < 1024:  # Less than 1KB
                print(f"Downloaded file too small: {os.path.getsize(filepath)} bytes")
                os.remove(filepath)
                return None
                
            print(f"✓ Downloaded: {filename} ({os.path.getsize(filepath)} bytes)")
            return filepath
            
        except Exception as e:
            print(f"✗ Failed to download {url[:50]}...: {str(e)}")
            return None

    def upload_image_to_cloudinary(self, filepath: str, folder: str = "pandel_images") -> Optional[str]:
        """Upload image to Cloudinary and return public_id"""
        try:
            print(f"Uploading to Cloudinary: {os.path.basename(filepath)}")
            result = cloudinary.uploader.upload(
                filepath, 
                upload_preset=UPLOAD_PRESET,
                folder=folder,
                resource_type="image"
            )
            public_id = result.get('public_id')
            print(f"✓ Cloudinary upload successful: {public_id}")
            return public_id
        except Exception as e:
            print(f"✗ Cloudinary upload failed for {filepath}: {str(e)}")
            return None

    def scrape_and_upload_images(self, pandel_name: str, max_images: int = 5) -> List[str]:
        """Main function to scrape and upload images for a pandel"""
        print(f"\n🔍 Starting image scraping for: {pandel_name}")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        print(f"Temp directory: {self.temp_dir}")
        
        try:
            # Try multiple search variations
            search_queries = [
                f"{pandel_name} Durga Puja pandal Kolkata",
                f"{pandel_name} Durga Puja Kolkata",
                f"{pandel_name} pandal",
                f"Durga Puja {pandel_name}"
            ]
            
            all_urls = []
            driver = None
            
            for query in search_queries:
                if len(all_urls) >= max_images * 3:  # Get extra URLs as backup
                    break
                    
                try:
                    print(f"\n🔎 Trying search query: {query}")
                    driver = self.setup_driver()
                    html = self.google_images_search(driver, query, scrolls=2)
                    
                    if html:
                        new_urls = self.extract_image_urls(html, max_images)
                        all_urls.extend(new_urls)
                        print(f"Found {len(new_urls)} URLs from this query")
                    else:
                        print("No HTML content received")
                        
                except Exception as e:
                    print(f"Error with query '{query}': {str(e)}")
                finally:
                    if driver:
                        driver.quit()
                        time.sleep(2)  # Brief pause between searches

            # Remove duplicates while preserving order
            unique_urls = list(dict.fromkeys(all_urls))
            print(f"\n📊 Total unique URLs found: {len(unique_urls)}")

            if not unique_urls:
                print("❌ No image URLs found. Google might be blocking requests.")
                return []

            uploaded_public_ids = []
            successful_downloads = 0
            
            for idx, url in enumerate(unique_urls):
                if successful_downloads >= max_images:
                    break
                    
                print(f"\n📸 Processing image {idx + 1}/{len(unique_urls)}")
                filename = f"{pandel_name.replace(' ', '_').replace('/', '_')}_{idx}.jpg"
                filepath = self.download_image(url, filename)
                
                if filepath and os.path.exists(filepath):
                    public_id = self.upload_image_to_cloudinary(filepath)
                    if public_id:
                        uploaded_public_ids.append(public_id)
                        successful_downloads += 1
                        print(f"✅ Success! ({successful_downloads}/{max_images})")
                    
                    # Remove local file after processing
                    try:
                        os.remove(filepath)
                    except:
                        pass

            print(f"\n🎉 Scraping complete! Successfully uploaded {len(uploaded_public_ids)} images")
            return uploaded_public_ids
            
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return []
            
        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    print(f"🧹 Cleaned up temp directory")
                except:
                    pass

    def cleanup(self):
        """Clean up resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass
