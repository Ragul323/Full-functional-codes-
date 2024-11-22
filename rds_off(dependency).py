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
# Main handler function for checking dependencies and stopping RDS instances
def lambda_handler(event, context):
    names = event.get('names', [])  # List of names triggering the Lambda
    action = "stop"  # Action to perform
    if not names:
        return {
            'statusCode': 400,
            'body': "Invalid request. Provide 'names'."
        }
    # Get the name-to-db mapping
    name_to_db_mapping = get_name_to_db_mapping()
    results = {}
    # Dependency logic for stopping B, C, D
    for name in names:
        db_instance_ids = name_to_db_mapping.get(name, [])
        if name == 'Navin':  # If Navin is requested to stop
            # Stop Navin's DB immediately
            results[name] = invoke_start_stop_rds(db_instance_ids, action)
            # Check the status of Swashi and Shubha
            c_status = get_db_status(name_to_db_mapping['Swashi'][0])  # C - Swashi
            d_status = get_db_status(name_to_db_mapping['Shubha'][0])  # D - Shubha
            # If both Swashi and Shubha are OFF, stop Ragul's DBs
            if c_status != 'available' and d_status != 'available':
                results['Ragul'] = invoke_start_stop_rds(name_to_db_mapping['Ragul'], action)
            else:
                # If either Swashi or Shubha is still ON, keep Ragul's DBs running
                results['Ragul'] = {'message': "Ragul's DBs remain ON because either Swashi or Shubha is still running."}
        elif name in ['Swashi', 'Shubha']:  # If Swashi or Shubha is requested to stop
            # Stop the requested DB
            results[name] = invoke_start_stop_rds(db_instance_ids, action)
            # Check the status of the other two DBs (Navin, Swashi/Shubha)
            other_status = get_db_status(name_to_db_mapping['Navin'][0])  # B - Navin
            if name == 'Swashi':
                d_status = get_db_status(name_to_db_mapping['Shubha'][0])  # D - Shubha
            else:
                d_status = get_db_status(name_to_db_mapping['Swashi'][0])  # C - Swashi
            # If both the other two DBs are OFF, stop Ragul's DBs
            if other_status != 'available' and d_status != 'available':
                results['Ragul'] = invoke_start_stop_rds(name_to_db_mapping['Ragul'], action)
            else:
                results['Ragul'] = {'message': "Ragul's DBs remain ON because either Navin or Swashi/Shubha is still running."}
        else:
            # Directly stop Ragul's DBs (A)
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
