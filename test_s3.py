import boto3

s3 = boto3.client('s3')  # connect to S3
buckets = s3.list_buckets()  # list your buckets
print("Buckets:", [b['Name'] for b in buckets])
