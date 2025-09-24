import boto3
import json
from config import *

def fix_s3_permissions():
    try:
        # Create S3 client
        s3 = boto3.client('s3', region_name=region)
        
        print(f"🔧 Fixing permissions for bucket: {bucket}")
        
        # 1. First, try to check bucket existence
        try:
            s3.head_bucket(Bucket=bucket)
            print("✅ Bucket exists")
        except Exception as e:
            print(f"❌ Bucket access error: {e}")
            return False
        
        # 2. Set bucket policy for public read
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket}/*"
                },
                {
                    "Sid": "AllowUploads",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket}/*"
                }
            ]
        }
        
        # Convert policy to JSON string
        policy_json = json.dumps(bucket_policy)
        
        try:
            s3.put_bucket_policy(Bucket=bucket, Policy=policy_json)
            print("✅ Bucket policy updated successfully!")
        except Exception as e:
            print(f"❌ Error setting bucket policy: {e}")
            # Try alternative approach - enable public access
            try:
                s3.put_public_access_block(
                    Bucket=bucket,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': False,
                        'IgnorePublicAcls': False,
                        'BlockPublicPolicy': False,
                        'RestrictPublicBuckets': False
                    }
                )
                print("✅ Public access enabled")
            except Exception as e2:
                print(f"❌ Error enabling public access: {e2}")
                return False
        
        # 3. Enable CORS configuration
        cors_configuration = {
            'CORSRules': [{
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': [],
                'MaxAgeSeconds': 3000
            }]
        }
        
        try:
            s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_configuration)
            print("✅ CORS configuration set")
        except Exception as e:
            print(f"⚠️  CORS configuration failed: {e}")
        
        print("✅ S3 bucket permissions fixed!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing permissions: {e}")
        return False

if __name__ == "__main__":
    fix_s3_permissions()