import boto3
from config import *
import pymysql

print("🔍 Running Diagnostic Check...")
print("=" * 50)

# Check RDS Connection
print("1. Testing RDS Database Connection...")
try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db,
        port=3306
    )
    print("✅ RDS Connection: SUCCESS")
    connection.close()
except Exception as e:
    print(f"❌ RDS Connection: FAILED - {e}")

# Check S3 Connection
print("\n2. Testing S3 Connection...")
try:
    s3 = boto3.client('s3', region_name=region)
    response = s3.list_buckets()
    print("✅ S3 Client: SUCCESS")
    
    # Check specific bucket
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"✅ S3 Bucket '{bucket}': ACCESSIBLE")
    except Exception as e:
        print(f"❌ S3 Bucket '{bucket}': NOT ACCESSIBLE - {e}")
        
except Exception as e:
    print(f"❌ S3 Client: FAILED - {e}")

print("=" * 50)