import requests
import json
import os
import logging
import base64
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

class PerfectCorpProcessor:
    """
    Class to handle virtual try-on using the Perfect Corp API.
    """
    def __init__(self, access_token=None, mock_mode=False):
        self.access_token = access_token or settings.PERFECT_CORP_ACCESS_TOKEN
        self.base_url = "https://api-us.perfectcorp.com/s2s/v1.0"
        self.mock_mode = mock_mode
        
    def get_access_token(self, api_key, api_secret):
        """
        Get an access token from the Perfect Corp API.
        
        Args:
            api_key: Your API key
            api_secret: Your API secret
            
        Returns:
            Access token if successful, None otherwise
        """
        # If in mock mode, return a fake token
        if self.mock_mode:
            logger.info("Mock mode: Generating fake access token")
            mock_token = f"mock_token_{uuid.uuid4().hex[:10]}"
            self.access_token = mock_token
            return mock_token
            
        try:
            # Prepare the API endpoint
            endpoint = f"{self.base_url}/auth/access-token"
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Prepare the request payload
            payload = {
                "api_key": api_key,
                "api_secret": api_secret
            }
            
            # Make the API request
            response = requests.post(endpoint, headers=headers, json=payload)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the access token
                if "access_token" in result:
                    self.access_token = result["access_token"]
                    return self.access_token
                else:
                    logger.error(f"Perfect Corp API response missing access token: {result}")
                    return None
            else:
                logger.error(f"Perfect Corp API request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Perfect Corp access token: {str(e)}")
            return None
    
    def upload_hairstyle(self, image_path, content_type=None):
        """
        Upload a hairstyle image to the Perfect Corp API.
        
        Args:
            image_path: Path to the hairstyle image
            content_type: Content type of the image (auto-detected if None)
            
        Returns:
            Hairstyle ID if successful, None otherwise
        """
        # If in mock mode, return a fake hairstyle ID
        if self.mock_mode:
            logger.info(f"Mock mode: Generating fake hairstyle ID for {image_path}")
            return f"mock_hairstyle_{uuid.uuid4().hex[:10]}"
            
        try:
            if not self.access_token:
                logger.error("No access token available. Call get_access_token first.")
                return None
                
            # Determine content type if not provided
            if content_type is None:
                if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
                    content_type = "image/jpeg"
                elif image_path.lower().endswith('.png'):
                    content_type = "image/png"
                else:
                    logger.error(f"Unsupported file type for {image_path}")
                    return None
            
            # Prepare the API endpoint
            endpoint = f"{self.base_url}/file/hair-style"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Read the image file as binary data
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                
            # Encode the image data as base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            # Get the file name from the path
            file_name = os.path.basename(image_path)
            
            # Prepare the request payload
            payload = {
                "files": [
                    {
                        "content_type": content_type,
                        "file_name": file_name,
                        "content": encoded_image
                    }
                ]
            }
            
            # Make the API request
            response = requests.post(endpoint, headers=headers, json=payload)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the hairstyle ID
                if "files" in result and len(result["files"]) > 0 and "id" in result["files"][0]:
                    return result["files"][0]["id"]
                else:
                    logger.error(f"Perfect Corp API response missing hairstyle ID: {result}")
                    return None
            else:
                logger.error(f"Perfect Corp API request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading hairstyle to Perfect Corp: {str(e)}")
            return None
    
    def process_tryon(self, user_image_path, hairstyle_id, output_path):
        """
        Process the virtual try-on using the Perfect Corp API.
        
        Args:
            user_image_path: Path to the user's image
            hairstyle_id: ID of the hairstyle in Perfect Corp's system
            output_path: Path to save the result
            
        Returns:
            Path to the processed image if successful, None otherwise
        """
        # If in mock mode, create a simple mock result
        if self.mock_mode:
            logger.info(f"Mock mode: Creating mock try-on result for {user_image_path} with hairstyle {hairstyle_id}")
            try:
                # Just copy the user image to the output path as a mock result
                import shutil
                shutil.copy(user_image_path, output_path)
                logger.info(f"Mock mode: Created mock result at {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Mock mode: Error creating mock result: {str(e)}")
                return None
                
        try:
            if not self.access_token:
                logger.error("No access token available. Call get_access_token first.")
                return None
                
            # Determine content type
            if user_image_path.lower().endswith('.jpg') or user_image_path.lower().endswith('.jpeg'):
                content_type = "image/jpeg"
            elif user_image_path.lower().endswith('.png'):
                content_type = "image/png"
            else:
                logger.error(f"Unsupported file type for {user_image_path}")
                return None
            
            # Prepare the API endpoint
            endpoint = f"{self.base_url}/effect/hair-style"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Read the image file as binary data
            with open(user_image_path, "rb") as image_file:
                image_data = image_file.read()
                
            # Encode the image data as base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            # Get the file name from the path
            file_name = os.path.basename(user_image_path)
            
            # Prepare the request payload
            payload = {
                "source_image": {
                    "content_type": content_type,
                    "file_name": file_name,
                    "content": encoded_image
                },
                "hair_style_id": hairstyle_id,
                "return_type": "base64"
            }
            
            # Make the API request
            response = requests.post(endpoint, headers=headers, json=payload)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the processed image
                if "result_image" in result and "content" in result["result_image"]:
                    # Decode the base64 image
                    processed_image_data = base64.b64decode(result["result_image"]["content"])
                    
                    # Save the image to the output path
                    with open(output_path, "wb") as output_file:
                        output_file.write(processed_image_data)
                    
                    logger.info(f"Perfect Corp virtual try-on completed successfully. Result saved to {output_path}")
                    return output_path
                else:
                    logger.error(f"Perfect Corp API response missing result image: {result}")
                    return None
            else:
                logger.error(f"Perfect Corp API request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing Perfect Corp virtual try-on: {str(e)}")
            return None