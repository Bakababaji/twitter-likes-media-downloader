# Twitter/X Likes Media Downloader

A powerful Python script to automatically download media (images and videos) from your liked tweets on Twitter/X.

## Features

- **Comprehensive Media Scraping**: Downloads images and videos from your liked tweets
- **Smart Checkpoint System**: Saves progress and allows resuming at any point
- **Media Quality Optimization**: Automatically fetches highest quality versions of media
- **Batch Organization**: Organizes downloads into manageable batches
- **Robust Error Handling**: Retries failed downloads and provides detailed logs

## Requirements

- Python 3.6+
- Chrome browser
- Required Python packages (see Installation)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/twitter-likes-media-downloader.git
   cd twitter-likes-media-downloader
   ```

2. Install required packages:
   ```
   pip install selenium requests webdriver-manager
   ```

3. Configure your settings:
   Open `twitter_media_downloader.py` and update the following variables:
   - `X_USERNAME`: Your Twitter/X username
   - `X_PASSWORD`: Your Twitter/X password
   - `DOWNLOAD_FOLDER`: Where you want to save downloaded media
   - `TARGET_MEDIA_COUNT`: How many media items you want to download

## Usage

1. Run the script:
   ```
   python twitter_media_downloader.py
   ```

2. The script will:
   - Log into your Twitter/X account (may require manual verification)
   - Navigate to your likes page
   - Scroll through your liked tweets collecting media URLs
   - Download all found media to your specified folder

3. If the script is interrupted, you can resume by running it again - it will use the saved checkpoint.

## Customization

You can modify these variables at the top of the script:

- `TARGET_MEDIA_COUNT`: Maximum number of media items to collect (default: 3000)
- `BATCH_SIZE`: Number of items per batch (default: 100)
- `SCROLL_PAUSE_TIME`: Time to wait between scrolls (default: 5 seconds)
- `MAX_SCROLLS`: Maximum number of scrolls to perform (default: 3000)

## How It Works

1. **Authentication**: The script logs into your Twitter/X account
2. **Navigation**: It navigates to your likes page
3. **Media Collection**: Using Selenium, it scrolls through your likes, collecting media URLs
4. **Downloading**: It downloads all media items, optimizing for quality
5. **Checkpointing**: Progress is saved to resume later if needed

## Notes

- The script requires Chrome browser and will use ChromeDriver (automatically downloaded)
- Twitter/X may require phone verification during login - the script allows time for manual intervention
- Media is saved in the specified download folder, organized by batches of 1000 items
- User credentials are stored in plain text in the script - consider using environment variables or a config file for better security

## Disclaimer

This tool is for personal use only. Please respect Twitter's terms of service and copyright laws. Don't distribute downloaded content without permission.

## License

[MIT License](LICENSE)
