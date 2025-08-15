import requests
import os
from datetime import datetime

# API base URL
BASE_URL = "https://img-store.onrender.com"

def download_all_images():
    """Download all images from the API"""
    
    # Create downloads directory
    downloads_dir = "downloaded_images"
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
    
    # Get all images
    print("📋 Getting list of all images...")
    response = requests.get(f"{BASE_URL}/images")
    
    if response.status_code != 200:
        print(f"❌ Failed to get images: {response.text}")
        return
    
    data = response.json()
    images = data.get('data', [])
    
    if not images:
        print("📭 No images found!")
        return
    
    print(f"📥 Found {len(images)} images to download...")
    
    # Download each image
    for i, image in enumerate(images, 1):
        image_id = image['id']
        original_name = image['name']
        
        # Clean filename (remove special characters)
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-")
        
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{i}_{safe_name}"
        filepath = os.path.join(downloads_dir, filename)
        
        print(f"📥 Downloading {i}/{len(images)}: {original_name}...")
        
        # Download the image
        img_response = requests.get(f"{BASE_URL}/images/{image_id}")
        
        if img_response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            print(f"✅ Saved as: {filename}")
        else:
            print(f"❌ Failed to download {original_name}")
    
    print(f"\n🎉 Download complete! All images saved in '{downloads_dir}' folder.")

if __name__ == "__main__":
    download_all_images() 