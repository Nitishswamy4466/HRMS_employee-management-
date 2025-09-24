import boto3
import os
from config import *

def check_aws_credentials():
    print("🔍 Checking AWS Credentials...")
    print("=" * 50)
    
    # Check environment variables
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region_env = os.getenv('AWS_DEFAULT_REGION')
    
    print("Environment Variables:")
    print(f"AWS_ACCESS_KEY_ID: {'✅ Set' if access_key else '❌ Not set'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'✅ Set' if secret_key else '❌ Not set'}")
    print(f"AWS_DEFAULT_REGION: {region_env if region_env else '❌ Not set'}")
    print()
    
    try:
        # Test credentials
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print("✅ AWS Credentials Valid!")
        print(f"Account: {identity['Account']}")
        print(f"User ID: {identity['UserId']}")
        print(f"ARN: {identity['Arn']}")
        print()
        
        # Test S3 access
        s3 = boto3.client('s3', region_name=region)
        try:
            s3.head_bucket(Bucket=bucket)
            print(f"✅ S3 Bucket '{bucket}' is accessible!")
        except Exception as e:
            print(f"❌ S3 Bucket error: {e}")
            
    except Exception as e:
        print(f"❌ AWS Credentials Invalid: {e}")
        print("\n💡 Run: aws configure")
        print("💡 Or set environment variables")

if __name__ == "__main__":
    check_aws_credentials()