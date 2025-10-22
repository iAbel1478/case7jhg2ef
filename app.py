from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, PublicAccess, ContentSettings
from datetime import datetime
import os
import logging

# Get environment variables
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = 'lanternfly-images'

# Initialize Flask app
app = Flask(__name__)

# Create Blob Service Client
bsc = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
cc = bsc.get_container_client(CONTAINER_NAME)

# Ensure container exists and is public
try:
    cc.create_container()
    cc.set_container_access_policy(public_access=PublicAccess.Container)
    print(f"✅ Container '{CONTAINER_NAME}' ready")
except Exception as e:
    print(f"ℹ️ Container may already exist: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/v1/upload', methods=['POST'])
def upload():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify(ok=False, error="No file provided"), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify(ok=False, error="No file selected"), 400
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            return jsonify(ok=False, error="Only image files allowed"), 400
        
        # Check file size (10MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify(ok=False, error="File too large (max 10MB)"), 400
        
        # Generate timestamped filename
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        safe_filename = f"{timestamp}-{file.filename}"
        
        # Upload to blob storage
        blob_client = bsc.get_blob_client(CONTAINER_NAME, safe_filename)
        blob_client.upload_blob(
            file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type)
        )
        
        # Return success response
        return jsonify(ok=True, url=blob_client.url)
        
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/v1/gallery', methods=['GET'])
def gallery():
    try:
        # List all blobs in container
        blob_list = cc.list_blobs()
        gallery_urls = []
        
        for blob in blob_list:
            blob_url = f"{cc.url}/{blob.name}"
            gallery_urls.append(blob_url)
        
        return jsonify(ok=True, gallery=gallery_urls)
        
    except Exception as e:
        app.logger.error(f"Gallery error: {str(e)}")
        return jsonify(ok=False, error=str(e)), 500

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
