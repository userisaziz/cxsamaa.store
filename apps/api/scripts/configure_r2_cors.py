#!/usr/bin/env python3
"""Configure CORS on Cloudflare R2 bucket to allow browser-based uploads.

This script sets up CORS rules to allow:
- PUT requests for pre-signed URL uploads
- GET requests for downloading audio files
- Required headers for browser security

Usage:
    python configure_r2_cors.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.config import Config
from src.config import settings

def configure_r2_cors():
    """Apply CORS configuration to R2 bucket."""
    
    print("🔧 Configuring R2 CORS for direct uploads...")
    print(f"   Account ID: {settings.r2_account_id}")
    print(f"   Bucket: {settings.r2_bucket}")
    print()
    
    # Initialize R2 client
    client = boto3.client(
        's3',
        endpoint_url=f'https://{settings.r2_account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name='auto',
        config=Config(signature_version='s3v4')
    )
    
    # CORS configuration for direct browser uploads
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'HEAD'],
                'AllowedOrigins': [
                    'http://localhost:3000',      # Local development
                    'http://localhost:3001',      # Local development
                    'http://92.4.87.24',          # Production IP
                    'http://92.4.87.24:3000',     # Production IP with port
                    'https://dashboard.cxsamaa.store',  # Production dashboard
                    'https://app.cxsamaa.store',        # Production web app
                    'https://cxsamaa.store',            # Production domain (apex)
                    'https://www.cxsamaa.store',        # Production domain (www)
                    'https://api.cxsamaa.store',        # Production API domain
                ],
                'ExposeHeaders': ['ETag', 'x-amz-request-id', 'x-amz-id-2'],
                'MaxAgeSeconds': 86400  # 24 hours for better caching
            }
        ]
    }
    
    try:
        client.put_bucket_cors(
            Bucket=settings.r2_bucket,
            CORSConfiguration=cors_configuration
        )
        print("✅ CORS configuration applied successfully!")
        print()
        print("📋 CORS Rules:")
        print("   - Allowed Origins: localhost, 92.4.87.24, dashboard.cxsamaa.store, + others")
        print("   - Allowed Methods: GET, PUT, HEAD")
        print("   - Allowed Headers: * (all)")
        print("   - Max Age: 3600 seconds (1 hour)")
        print()
        print("🎯 What this enables:")
        print("   ✓ Browser-based pre-signed URL uploads (PUT)")
        print("   ✓ Audio file downloads (GET)")
        print("   ✓ Proper CORS headers for XMLHttpRequest")
        print()
        
        # Verify the configuration
        response = client.get_bucket_cors(Bucket=settings.r2_bucket)
        print("✅ Verified: CORS is now active on the bucket")
        print(f"   Rules: {len(response.get('CORSRules', []))} rule(s)")
        
    except Exception as e:
        print(f"❌ Failed to configure CORS: {e}")
        print()
        print("💡 Manual Configuration Steps:")
        print("   1. Go to Cloudflare Dashboard → R2")
        print("   2. Select bucket: cxsamaa-prod")
        print("   3. Go to 'Settings' → 'CORS'")
        print("   4. Add a new CORS rule with:")
        print("      - Allowed Origins: http://localhost:3000, http://92.4.87.24")
        print("      - Allowed Methods: GET, PUT, HEAD")
        print("      - Allowed Headers: *")
        print("      - Max Age: 3600")
        raise

if __name__ == "__main__":
    configure_r2_cors()
