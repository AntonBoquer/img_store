import requests
import os

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health Check: {response.status_code}")
    print(response.json())
    print()

def test_upload():
    """Test image upload"""
    # Create a test image (1x1 pixel PNG)
    test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178\xea\x00\x00\x00\x00IEND\xaeB`\x82'
    
    files = {"file": ("test.png", test_image_data, "image/png")}
    response = requests.post(f"{BASE_URL}/upload", files=files)
    
    print(f"Upload Test: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Uploaded Image ID: {result['data']['id']}")
        return result['data']['id']
    else:
        print(f"Upload failed: {response.text}")
        return None
    print()

def test_get_images():
    """Test getting all images"""
    response = requests.get(f"{BASE_URL}/images")
    print(f"Get Images: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Found {len(result['data'])} images")
        for img in result['data']:
            print(f"  - {img['name']} ({img['size']} bytes)")
    else:
        print(f"Failed to get images: {response.text}")
    print()

def test_get_image(image_id):
    """Test getting specific image"""
    response = requests.get(f"{BASE_URL}/images/{image_id}")
    print(f"Get Image {image_id}: {response.status_code}")
    if response.status_code == 200:
        print(f"Image retrieved: {len(response.content)} bytes")
        # Save the image
        with open("test_downloaded.png", "wb") as f:
            f.write(response.content)
        print("Image saved as test_downloaded.png")
    else:
        print(f"Failed to get image: {response.text}")
    print()

def test_delete_image(image_id):
    """Test deleting image"""
    response = requests.delete(f"{BASE_URL}/images/{image_id}")
    print(f"Delete Image {image_id}: {response.status_code}")
    if response.status_code == 200:
        print("Image deleted successfully")
    else:
        print(f"Failed to delete image: {response.text}")
    print()

if __name__ == "__main__":
    print("🧪 Testing Image Store API")
    print("=" * 40)
    
    # Test health
    test_health()
    
    # Test upload
    image_id = test_upload()
    
    if image_id:
        # Test get all images
        test_get_images()
        
        # Test get specific image
        test_get_image(image_id)
        
        # Test delete image
        test_delete_image(image_id)
        
        # Verify deletion
        test_get_images()
    
    print("✅ Testing complete!") 