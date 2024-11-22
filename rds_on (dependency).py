import boto3
import json
lambda_client = boto3.client('lambda')
rds_client = boto3.client('rds')
# Helper function to get the status of an RDS instance
def get_db_status(db_instance_id):
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        return response['DBInstances'][0]['DBInstanceStatus']
    except Exception as e:
        return str(e)
# Helper function to invoke start_stop_rds Lambda
def invoke_start_stop_rds(db_instance_ids, action):
    results = {}
    for db_instance_id in db_instance_ids:
        payload = {
            "instance_id": db_instance_id,
            "action": action
        }
        # Invoke the start_stop_rds Lambda
        response = lambda_client.invoke(
            FunctionName='arn:aws:lambda:ap-south-1:183631326320:function:start_stop_rds',  # Replace with your actual Lambda function name
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        # Collect the result for each DB
        results[db_instance_id] = json.loads(response['Payload'].read())
    return results
# Main handler function for checking dependencies and starting RDS instances
def lambda_handler(event, context):
    names = event.get('names', [])  # List of names triggering the Lambda
    action = "start"  # Action to perform
    if not names:
        return {
            'statusCode': 400,
            'body': "Invalid request. Provide 'names'."
        }
    # Get the name-to-db mapping
    name_to_db_mapping = get_name_to_db_mapping()
    results = {}
    # Dependency logic for Ragul, Navin, Swashi, Shubha
    for name in names:
        db_instance_ids = name_to_db_mapping.get(name, [])
        # Check dependencies only for Ragul
        if name in ['Navin', 'Swashi', 'Shubha']:
            # Check Ragul's DB status (A)
            if get_db_status(name_to_db_mapping['Ragul'][0]) != 'available':
                # If Ragul's DBs are not available, start Ragul's DBs first
                invoke_start_stop_rds(name_to_db_mapping['Ragul'], action)
            # Start the requested DB after Ragul's DBs are confirmed to be started
            results[name] = invoke_start_stop_rds(db_instance_ids, action)
        else:
            # Directly start Ragul's DBs
            results[name] = invoke_start_stop_rds(db_instance_ids, action)
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
# Helper function to get name-to-db mapping from the rds_names Lambda
def get_name_to_db_mapping():
    response = lambda_client.invoke(
        FunctionName='arn:aws:lambda:ap-south-1:183631326320:function:rds_names_dependency',  # Replace with the actual Lambda function name
        InvocationType='RequestResponse'
    )
    response_payload = json.loads(response['Payload'].read())
    return json.loads(response_payload['body'])
