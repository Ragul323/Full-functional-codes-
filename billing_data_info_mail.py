import boto3
import datetime
import csv
import io
def lambda_handler(event, context):
    # Initialize clients
    ce_client = boto3.client('ce')  # AWS Cost Explorer client
    s3_client = boto3.client('s3')
    ses_client = boto3.client('ses')
    # Define parameters
    start_date = event.get("start_date", (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d'))
    end_date = event.get("end_date", datetime.date.today().replace(day=1).strftime('%Y-%m-%d'))
    bucket_name = event.get("bucket_name", "billinginfo-lambda")  # Replace with your S3 bucket name
    recipient_email = event.get("recipient_email", "raguldevops03@gmail.com")  # Replace with your email address
    # Request cost and usage data by service
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=['BlendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    # Prepare data for CSV and email summary
    billing_data = []
    total_cost = 0.0
    # HTML Table for email body
    summary_html = """
    <html>
        <body>
            <h2>AWS Billing Report by Service</h2>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="text-align: left;">Service</th>
                        <th style="text-align: right;">Cost (USD)</th>
                    </tr>
                </thead>
                <tbody>
    """
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            service = group['Keys'][0]
            amount = float(group['Metrics']['BlendedCost']['Amount'])
            total_cost += amount
            billing_data.append([service, f"${amount:.2f}"])
            # Add rows to HTML table
            summary_html += f"""
                <tr>
                    <td>{service}</td>
                    <td style="text-align: right;">${amount:.2f}</td>
                </tr>
            """
    # Add total cost row to HTML table
    summary_html += f"""
                <tr style="font-weight: bold;">
                    <td>Total Cost</td>
                    <td style="text-align: right;">${total_cost:.2f}</td>
                </tr>
                </tbody>
            </table>
            <p>The full report is also available as a CSV file in your S3 bucket: {bucket_name}/billing_report_{start_date}_to_{end_date}.csv.</p>
        </body>
    </html>
    """
    # Create CSV content in memory
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["Service", "Cost (USD)"])  # CSV header
    csv_writer.writerows(billing_data)  # Write each service and cost
    csv_writer.writerow(["Total Cost", f"${total_cost:.2f}"])  # Add total cost as the last row
    # Save CSV to S3
    csv_key = f'billing_report_{start_date}_to_{end_date}.csv'
    s3_client.put_object(
        Bucket=bucket_name,
        Key=csv_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )
    # Prepare and send the email with HTML summary
    email_subject = "AWS Billing Report by Service"
    ses_client.send_email(
        Source="ragulmurthy3@gmail.com",  # Replace with your verified SES email
        Destination={'ToAddresses': [recipient_email]},
        Message={
            'Subject': {'Data': email_subject},
            'Body': {
                'Html': {'Data': summary_html}
            }
        }
    )
    return {
        'statusCode': 200,
        'body': f'Successfully sent billing report to {recipient_email} and saved as {csv_key} in {bucket_name}'
    }




----------------------------------------------------------
{
  "start_date": "2024-10-01",
  "end_date": "2024-10-31",
  "bucket_name": "billinginfo-lambda",
  "recipient_email": "raguldevops03@gmail.com"
}
