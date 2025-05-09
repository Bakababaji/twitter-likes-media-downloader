import re
import os
import time
import json
import requests
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
X_USERNAME = "USERNAME"
X_PASSWORD = "PASSWORD"
PROFILE_URL = f"https://x.com/{X_USERNAME}"
LIKES_TAB_SELECTOR = "a[href='/USERNAME/likes']"
TWEET_CONTAINER_SELECTOR = "article[data-testid='tweet']"
# More comprehensive selectors to capture all possible media
IMAGE_SELECTOR = "img[src*='pbs.twimg.com/media/'], img[src*='pbs.twimg.com/ext_tw_video_thumb/']"
BACKGROUND_IMAGE_DIV_SELECTOR = "div[style*='background-image: url']"
VIDEO_SELECTOR = "video[src*='video.twimg.com'], div[data-testid='videoPlayer']"
TWEET_MEDIA_CONTAINER = "div[data-testid='tweetPhoto'], div[data-testid='videoPlayer']"
DOWNLOAD_FOLDER = "D:/python/x liked"
CHECKPOINT_FILE = os.path.join(DOWNLOAD_FOLDER, "checkpoint.json")

# --- New Configuration Options ---
# Target number of media items to collect (increase this to your desired limit)
TARGET_MEDIA_COUNT = 3000
# Batch size for processing and saving progress
BATCH_SIZE = 100
# Longer pause time for better loading of media content
SCROLL_PAUSE_TIME = 5
# Maximum number of scrolls (safety limit)
MAX_SCROLLS = 3000
# Progress report frequency (every N scrolls)
PROGRESS_REPORT_FREQ = 10

def is_profile_image(url):
    """Check if the URL is a profile image (we want to skip these)"""
    if not url:
        return True
    return ('profile_images' in url or 
            '_bigger.' in url or 
            '_normal.' in url or 
            '_mini.' in url or
            'twimg.com/emoji/' in url or  # Skip emoji images
            '/semantic_core_img/' in url)  # Skip UI elements

def extract_media_from_page(driver):
    """
    A comprehensive function to extract all media from the currently loaded page.
    """
    media_urls = set()
    
    # First look for all possible media element types
    print("Scanning page for media content...")

    # 1. Check for images in media containers
    media_images = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tweetPhoto'] img")
    for img in media_images:
        src = img.get_attribute('src')
        if src and not is_profile_image(src):
            # Convert to highest quality version
            if '/media/' in src:
                if 'format=' in src:
                    src = re.sub(r'format=\w+', 'format=jpg', src)
                if 'name=' in src:
                    src = re.sub(r'name=\w+', 'name=orig', src)
                else:
                    src += '&name=orig'
                media_urls.add(src)
    
    # 2. Check for videos and their previews
    video_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='videoPlayer'] video")
    for video in video_elements:
        src = video.get_attribute('src')
        if src:
            media_urls.add(src)
        
        # Also get the poster image as backup
        poster = video.get_attribute('poster')
        if poster:
            media_urls.add(poster)
    
    # 3. Check for video thumbnails
    video_thumbs = driver.find_elements(By.CSS_SELECTOR, "img[src*='ext_tw_video_thumb']")
    for thumb in video_thumbs:
        src = thumb.get_attribute('src')
        if src:
            media_urls.add(src)
    
    # 4. Check for general media images with more generic selector
    all_images = driver.find_elements(By.CSS_SELECTOR, "img[src*='pbs.twimg.com/media/']")
    for img in all_images:
        src = img.get_attribute('src')
        if src and not is_profile_image(src):
            width = img.get_attribute('width')
            # Skip tiny icons
            if width and int(width) < 50:
                continue
                
            if '/media/' in src:
                if 'format=' in src:
                    src = re.sub(r'format=\w+', 'format=jpg', src)
                if 'name=' in src:
                    src = re.sub(r'name=\w+', 'name=orig', src)
                else:
                    src += '&name=orig'
                media_urls.add(src)
    
    # 5. Background images in divs (sometimes contains media)
    bg_elements = driver.find_elements(By.CSS_SELECTOR, "div[style*='background-image: url']")
    for div in bg_elements:
        style = div.get_attribute('style')
        match = re.search(r'url\("?(.*?)"?\)', style)
        if match:
            src = match.group(1)
            if src and not is_profile_image(src) and '/media/' in src:
                if 'format=' in src:
                    src = re.sub(r'format=\w+', 'format=jpg', src)
                if 'name=' in src:
                    src = re.sub(r'name=\w+', 'name=orig', src)
                else:
                    src += '&name=orig'
                media_urls.add(src)
    
    # 6. Check for Twitter card images (sometimes used for shared links with images)
    card_images = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='card.layoutSmall.media'] img, div[data-testid='card.layoutLarge.media'] img")
    for img in card_images:
        src = img.get_attribute('src')
        if src and not is_profile_image(src):
            if '/media/' in src:
                if 'format=' in src:
                    src = re.sub(r'format=\w+', 'format=jpg', src)
                if 'name=' in src:
                    src = re.sub(r'name=\w+', 'name=orig', src)
                else:
                    src += '&name=orig'
                media_urls.add(src)
    
    return list(media_urls)

def login_to_x(driver, username, password):
    """Log into X/Twitter account"""
    print("Logging into X/Twitter...")
    driver.get("https://x.com/login")
    wait = WebDriverWait(driver, 20)
    
    try:
        # Try the modern login flow first
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        username_field.send_keys(username)
        username_field.send_keys(Keys.RETURN)
        time.sleep(2)
        
        # Handle potential phone verification step
        try:
            # Check if there's a "phone" input (means verification needed)
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, "phone")))
            print("Phone verification required. Please complete verification manually...")
            # Wait longer for manual intervention
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, "password")))
        except:
            # Phone verification not needed, continue
            pass
            
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        
        # Wait for navigation to complete (look for main nav element)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav")))
        print("Login successful!")
        
    except Exception as e:
        print(f"Login error: {e}")
        print("Please check your credentials or try logging in manually...")
        # Wait for manual login (give user 60 seconds to intervene)
        time.sleep(60)

def navigate_to_likes(driver, profile_url, likes_tab_selector):
    """Navigate to the likes tab of the profile"""
    print(f"Navigating to likes page at {profile_url}...")
    driver.get(profile_url)
    wait = WebDriverWait(driver, 20)
    
    try:
        likes_tab = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, likes_tab_selector)))
        likes_tab.click()
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, TWEET_CONTAINER_SELECTOR)))
        print("Successfully navigated to likes page")
    except Exception as e:
        print(f"Navigation error: {e}")
        print("Please check your profile URL and likes tab selector")
        # Try direct navigation as fallback
        likes_url = f"{profile_url}/likes"
        print(f"Attempting direct navigation to {likes_url}")
        driver.get(likes_url)
        time.sleep(5)

def save_checkpoint(media_urls, downloaded_count, scroll_count):
    """Save progress to checkpoint file"""
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)
        
    checkpoint_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'media_urls': list(media_urls),
        'downloaded_count': downloaded_count,
        'scroll_count': scroll_count,
        'total_found': len(media_urls)
    }
    
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint_data, f)
    
    print(f"Progress saved: {len(media_urls)} media URLs found, {downloaded_count} downloaded")

def load_checkpoint():
    """Load progress from checkpoint file if it exists"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint_data = json.load(f)
            
            # Convert back to set for easy deduplication
            media_urls = set(checkpoint_data.get('media_urls', []))
            downloaded_count = checkpoint_data.get('downloaded_count', 0)
            scroll_count = checkpoint_data.get('scroll_count', 0)
            
            print(f"Checkpoint loaded: {len(media_urls)} media URLs found, {downloaded_count} downloaded")
            return media_urls, downloaded_count, scroll_count
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
    
    # Return defaults if no checkpoint or error
    return set(), 0, 0

def optimized_scroll_for_media(driver, target_count=TARGET_MEDIA_COUNT):
    """
    Optimized scrolling function to find large amounts of media
    with progress tracking and checkpoint saving
    """
    print(f"Starting optimized scrolling to collect {target_count} media items...")
    
    # Load checkpoint if available
    all_media_urls, downloaded_count, start_scroll_count = load_checkpoint()
    
    # Track progress
    scroll_count = start_scroll_count
    last_height = driver.execute_script("return document.body.scrollHeight")
    unchanged_height_count = 0
    last_media_count = len(all_media_urls)
    last_save_time = time.time()
    
    # Scroll until we have enough media or reach the end
    while len(all_media_urls) < target_count and scroll_count < MAX_SCROLLS:
        # Extract media from current viewport
        current_media = extract_media_from_page(driver)
        new_media_count = 0
        
        # Add to our collection, track how many new items we found
        for media_url in current_media:
            if media_url not in all_media_urls and not is_profile_image(media_url):
                all_media_urls.add(media_url)
                new_media_count += 1
        
        # Report progress on regular intervals
        if scroll_count % PROGRESS_REPORT_FREQ == 0 or new_media_count > 0:
            print(f"Scroll #{scroll_count}: Found {new_media_count} new media items")
            print(f"Total collected: {len(all_media_urls)}/{target_count} ({len(all_media_urls)/target_count*100:.1f}%)")
        
        # Scroll down with overlap to ensure we don't miss anything
        viewport_height = driver.execute_script("return window.innerHeight")
        # Use smaller scroll increment for more reliable content loading
        driver.execute_script(f"window.scrollBy(0, {int(viewport_height * 0.6)});")
        
        scroll_count += 1
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Every 10 scrolls, do a more comprehensive scan
        if scroll_count % 20 == 0:
            print(f"Performing comprehensive scan at scroll #{scroll_count}...")
            
            # First scroll back up a bit to ensure new content is fully loaded
            driver.execute_script(f"window.scrollBy(0, {int(-viewport_height * 0.3)});")
            time.sleep(SCROLL_PAUSE_TIME)
            
            # Now do a thorough scan
            full_page_media = extract_media_from_page(driver)
            new_count = 0
            for media_url in full_page_media:
                if media_url not in all_media_urls and not is_profile_image(media_url):
                    all_media_urls.add(media_url)
                    new_count += 1
            
            print(f"Comprehensive scan found {new_count} additional media items")
            print(f"Total: {len(all_media_urls)}/{target_count} ({len(all_media_urls)/target_count*100:.1f}%)")
        
        # Save checkpoint periodically (every 50 scrolls or when we find a significant number of new media)
        if scroll_count % 50 == 0 or (new_media_count > 10 and time.time() - last_save_time > 60):
            save_checkpoint(all_media_urls, downloaded_count, scroll_count)
            last_save_time = time.time()
        
        # Check if we've reached the end
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            unchanged_height_count += 1
            print(f"Page height unchanged for {unchanged_height_count} consecutive scrolls")
            
            # If height unchanged for several scrolls AND we haven't found new media
            if unchanged_height_count >= 5 and len(all_media_urls) == last_media_count:
                print("No new content detected after multiple scrolls.")
                
                # Try forcing a full height update
                driver.execute_script("window.scrollTo(0, 0);")  # Scroll to top
                time.sleep(SCROLL_PAUSE_TIME)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll to bottom
                time.sleep(SCROLL_PAUSE_TIME * 2)
                
                final_height = driver.execute_script("return document.body.scrollHeight")
                if final_height == new_height:
                    print(f"Reached end of available content after {scroll_count} scrolls")
                    break
                else:
                    # Reset if height changed
                    print("Content height changed after reset, continuing...")
                    unchanged_height_count = 0
                    last_height = final_height
        else:
            # Height changed, reset counter
            unchanged_height_count = 0
            last_height = new_height
        
        # Keep track of media count to detect when we stop finding new media
        last_media_count = len(all_media_urls)
        
        # Check if we've reached our target
        if len(all_media_urls) >= target_count:
            print(f"Target reached! Found {len(all_media_urls)} media items.")
            break
    
    print(f"Scrolling complete - processed {scroll_count} scrolls")
    print(f"Found {len(all_media_urls)} total media URLs to download")
    
    # Save final checkpoint
    save_checkpoint(all_media_urls, downloaded_count, scroll_count)
    
    return list(all_media_urls)

def download_media(media_urls, download_folder, start_index=0):
    """
    Download media with improved error handling and resumption
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    
    # Load checkpoint to get download progress
    _, downloaded_count, _ = load_checkpoint()
    start_index = max(start_index, downloaded_count)
    
    # Create subdirectories by batch for better organization
    batch_folder = os.path.join(download_folder, f"batch_{start_index//1000+1}")
    if not os.path.exists(batch_folder):
        os.makedirs(batch_folder)
    
    # Statistics tracking
    successful_downloads = 0
    skipped_urls = 0
    failed_downloads = 0
    
    # Filter out known non-media URLs first
    filtered_urls = []
    for url in media_urls:
        # Skip URLs that don't contain media or are profile images
        if is_profile_image(url):
            skipped_urls += 1
            continue
            
        # Check for valid media types
        if not any(pattern in url for pattern in ['/media/', 'video.twimg', 'ext_tw_video_thumb', 'amplify_video']):
            skipped_urls += 1
            continue
            
        filtered_urls.append(url)
    
    print(f"Filtered {skipped_urls} non-media URLs. Proceeding to download {len(filtered_urls)} media files.")
    
    # Process actual downloads with retries
    for i, url in enumerate(filtered_urls[start_index:], start=start_index):
        # Determine which batch folder to use
        current_batch = i // 1000 + 1
        batch_folder = os.path.join(download_folder, f"batch_{current_batch}")
        if not os.path.exists(batch_folder):
            os.makedirs(batch_folder)
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"Downloading {i+1}/{len(filtered_urls)}: {url}")
                
                # Custom headers can help with downloading
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://twitter.com/'
                }
                
                response = requests.get(url, stream=True, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                
                # Extract filename from URL
                parsed_url = urllib.parse.urlparse(url)
                path = parsed_url.path
                
                # Get base filename from URL path
                base_filename = os.path.basename(path).split('?')[0]
                
                # Determine file extension based on content type or default to jpg/mp4
                if 'video' in content_type or 'video' in url:
                    extension = 'mp4'
                elif 'image' in content_type:
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        extension = 'jpg'
                    elif 'png' in content_type:
                        extension = 'png'
                    elif 'gif' in content_type:
                        extension = 'gif'
                    else:
                        extension = 'jpg'  # Default for images
                else:
                    # Default based on URL patterns
                    if 'video' in url:
                        extension = 'mp4'
                    else:
                        extension = 'jpg'
                
                # Ensure we have a file extension
                if '.' not in base_filename or base_filename.split('.')[-1] not in ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm', 'mov']:
                    filename = f"{base_filename}.{extension}"
                else:
                    filename = base_filename
                
                # Make sure filename is valid
                filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                
                # Add media ID and index for uniqueness
                media_id = ''
                if '/media/' in url:
                    media_id_match = re.search(r'/media/([A-Za-z0-9_-]+)', url)
                    if media_id_match:
                        media_id = f"{media_id_match.group(1)}_"
                
                # Use index and media_id for uniqueness
                full_path = os.path.join(batch_folder, f"{i+1}_{media_id}{filename}")
                
                # Download the file
                with open(full_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = os.path.getsize(full_path)
                if file_size < 1000:  # Less than 1KB is likely an error
                    print(f"Warning: Downloaded file is very small ({file_size} bytes), may be an error")
                    # If it's an error page, just continue
                    if file_size < 200:  # Very small file, likely an error
                        os.remove(full_path)
                        raise Exception("Downloaded file too small, likely an error")
                
                print(f"✓ Downloaded {full_path} ({file_size/1024:.1f} KB)")
                successful_downloads += 1
                
                # Update checkpoint after successful download
                downloaded_count = i + 1
                save_checkpoint(media_urls, downloaded_count, 0)  # 0 for scroll_count since we're just tracking downloads
                
                break  # Success, exit retry loop
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                print(f"Download attempt {retry_count} failed: {e}")
                if retry_count < max_retries:
                    print(f"Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"Failed to download after {max_retries} attempts.")
                    failed_downloads += 1
                    break
            except Exception as e:
                print(f"Failed to download {url}: {e}")
                failed_downloads += 1
                break
    
    print(f"\nDownload Summary:")
    print(f"- Successfully downloaded: {successful_downloads} files")
    print(f"- Failed downloads: {failed_downloads} files")
    print(f"- Skipped non-media URLs: {skipped_urls} URLs")
    print(f"- Total processed: {len(media_urls)} URLs")

def main():
    # Create session log file
    log_file = os.path.join(DOWNLOAD_FOLDER, f"scraper_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)
    
    # Set up Chrome options for better media loading
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")  # Start maximized
    chrome_options.add_argument("--disable-notifications")  # Disable notifications
    
    # Optional arguments to help with media loading
    chrome_options.add_argument("--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    
    # Anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Create download folder if it doesn't exist
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)
        print(f"Created download folder: {DOWNLOAD_FOLDER}")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        print("=" * 50)
        print(f"Twitter Media Scraper v2.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        print(f"Username: {X_USERNAME}")
        print(f"Target: {TARGET_MEDIA_COUNT} media items")
        print(f"Download folder: {DOWNLOAD_FOLDER}")
        print("=" * 50)
        
        # Check for existing checkpoint
        if os.path.exists(CHECKPOINT_FILE):
            print("Found existing checkpoint. Resuming previous session...")
            loaded_urls, downloaded_count, _ = load_checkpoint()
            
            # Ask if user wants to continue downloading from checkpoint
            if downloaded_count > 0 and len(loaded_urls) > downloaded_count:
                choice = input(f"Continue downloading remaining {len(loaded_urls) - downloaded_count} items? (y/n): ")
                
                if choice.lower() == 'y':
                    print("Continuing download from checkpoint...")
                    # Skip login and scrolling, just download remaining items
                    download_media(list(loaded_urls), DOWNLOAD_FOLDER, downloaded_count)
                    print("Checkpoint download complete! Run the script again to collect more items.")
                    return
        
        # Login and navigate to likes page
        login_to_x(driver, X_USERNAME, X_PASSWORD)
        navigate_to_likes(driver, PROFILE_URL, LIKES_TAB_SELECTOR)
        
        # Perform optimized scrolling to collect media URLs
        all_media_urls = optimized_scroll_for_media(driver, TARGET_MEDIA_COUNT)
        
        if all_media_urls:
            print(f"Starting download of {len(all_media_urls)} media files...")
            download_media(all_media_urls, DOWNLOAD_FOLDER)
        else:
            print("No media found to download.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to save progress before exit
        if 'all_media_urls' in locals() and all_media_urls:
            print("Saving progress before exit...")
            save_checkpoint(all_media_urls, downloaded_count if 'downloaded_count' in locals() else 0, 
                           scroll_count if 'scroll_count' in locals() else 0)
    finally:
        print("Closing browser...")
        driver.quit()
        print("Script execution complete.")

if __name__ == "__main__":
    main()