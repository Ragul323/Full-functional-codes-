import boto3
import csv
import os
from io import StringIO
def lambda_handler(event, context):
    iam_client = boto3.client('iam')
    s3_client = boto3.client('s3')
    # Get all IAM users
    response = iam_client.list_users()
    users = response['Users']
    # CSV file to store user details
    csv_file = StringIO()
    csv_writer = csv.writer(csv_file)
    # CSV headers
    csv_writer.writerow(['Username', 'UserId', 'ARN', 'CreateDate', 'LastActivity', 'AccessKeyId', 'AccessKeyLastUsed'])
    for user in users:
        username = user['UserName']
        user_id = user['UserId']
        arn = user['Arn']
        create_date = user['CreateDate']
        # Get last activity details
        last_activity = "No activity found"
        try:
            activity_response = iam_client.get_user(UserName=username)
            if 'PasswordLastUsed' in activity_response['User']:
                last_activity = activity_response['User']['PasswordLastUsed']
        except Exception as e:
            last_activity = f"Error: {str(e)}"
        # Get access key details
        access_key_id = ""
        access_key_last_used = ""
        try:
            access_keys = iam_client.list_access_keys(UserName=username)
            if access_keys['AccessKeyMetadata']:
                access_key_id = access_keys['AccessKeyMetadata'][0]['AccessKeyId']
                last_used_response = iam_client.get_access_key_last_used(AccessKeyId=access_key_id)
                access_key_last_used = last_used_response.get('AccessKeyLastUsed', {}).get('LastUsedDate', 'Never Used')
        except Exception as e:
            access_key_last_used = f"Error: {str(e)}"
        # Write to CSV
        csv_writer.writerow([username, user_id, arn, create_date, last_activity, access_key_id, access_key_last_used])
    # Upload CSV to S3
    s3_bucket = os.environ.get('S3_BUCKET') 
    s3_client.put_object(
        Bucket=s3_bucket,
        Key='iam_user_data.csv',
        Body=csv_file.getvalue()
    )
    return {
        'statusCode': 200,
        'body': f"CSV file created and uploaded to S3 bucket {s3_bucket}"
    }
