import pymysql
from config import *

print("🔍 Testing RDS Connection...")
print("=" * 50)

try:
    print(f"Host: {host}")
    print(f"User: {user}")
    print(f"Database: {db}")
    print(f"Region: {region}")
    print("=" * 50)
    
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db,
        port=3306,
        connect_timeout=10
    )
    
    print("✅ RDS Connection: SUCCESS!")
    
    # Test basic query
    cursor = connection.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"✅ MySQL Version: {version[0]}")
    
    # Check if employees table exists
    cursor.execute("SHOW TABLES LIKE 'employees'")
    table_exists = cursor.fetchone()
    if table_exists:
        print("✅ Employees table: EXISTS")
    else:
        print("⚠️ Employees table: NOT FOUND")
    
    cursor.close()
    connection.close()
    
except pymysql.MySQLError as e:
    print(f"❌ MySQL Error: {e}")
    print("\n💡 Common Solutions:")
    print("1. Check RDS endpoint for typos")
    print("2. Verify database name is 'employee'")
    print("3. Check if RDS instance is running")
    print("4. Verify security group allows your IP")
    
except Exception as e:
    print(f"❌ Connection Error: {e}")

print("=" * 50)