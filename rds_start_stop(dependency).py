import boto3
import json
lambda_client = boto3.client('lambda')
rds_client = boto3.client('rds')
def lambda_handler(event, context):
    # Check if the event body is stringified
    if 'body' in event:
        # Parse the JSON string from the API Gateway
        event = json.loads(event['body'])
    # Name to RDS instance mappings
    name_to_db_mapping = get_name_to_db_mapping()  # Fetches name-to-db mappings
    # Ensure name_to_db_mapping is a dictionary
    if not isinstance(name_to_db_mapping, dict):
        return {
            'statusCode': 500,
            'body': json.dumps("Error: name_to_db_mapping is not a dictionary.")
        }
    # Fetch the action (start/stop) and names (can be single or multiple names)
    action = event.get('action', 'start')
    names = event.get('names')  # Expecting this to be a list or a single name string
    # Debugging information to check the structure of inputs
    print(f"Event received: {event}")
    print(f"Action: {action}")
    print(f"Names: {names}")
    # Ensure 'names' is a list (if a single name is passed, wrap it in a list)
    if isinstance(names, str):
        names = [names]  # Convert single name string to list
    elif names is None:
        return {
            'statusCode': 400,
            'body': json.dumps("Invalid request. Provide 'names' (as a list or string) and 'action'.")
        }
    # Collect all DB names for the provided names
    db_names = []
    for name in names:
        if name in name_to_db_mapping:
            db_names.extend(name_to_db_mapping[name])
        else:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Invalid name '{name}'. No databases found.")
            }
    # Add the combined DB names to the event payload
    event['db_names'] = db_names
    print(f"DB names to process: {db_names}")
    # Invoke the appropriate function based on the action
    if action == "start":
        response = invoke_rds_on_dependency(event)
    elif action == "stop":
        response = invoke_rds_off_dependency(event)
    else:
        response = invoke_start_stop_rds(event)
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
# Directly define the name-to-db mapping
def get_name_to_db_mapping():
    # Static mapping of names to databases
    name_to_db_mapping = {
        "Ragul": ["db-1", "db-2","database-d"],
        "Navin": ["db-3"],
        "Swashi": ["db-4"],
        "Shubha": ["db-5", "db-6"]
    }
    print(f"Name-to-DB Mapping: {name_to_db_mapping}")  # Debugging output
    return name_to_db_mapping  # Ensure this returns a dictionary
# Function to invoke the rds_on_dependency Lambda
def invoke_rds_on_dependency(event):
    try:
        response = lambda_client.invoke(
            FunctionName='arn:aws:lambda:ap-south-1:183631326320:function:old_rds_on',  # Replace with actual ARN
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        response_payload = json.loads(response['Payload'].read())
        return response_payload
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error invoking rds_on_dependency: {str(e)}"
        }
# Function to invoke the rds_off_dependency Lambda
def invoke_rds_off_dependency(event):
    try:
        response = lambda_client.invoke(
            FunctionName='arn:aws:lambda:ap-south-1:183631326320:function:old_rds_off',  # Replace with actual ARN
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        response_payload = json.loads(response['Payload'].read())
        return response_payload
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error invoking rds_off_dependency: {str(e)}"
        }
# Function to invoke the start_stop_rds Lambda
def invoke_start_stop_rds(db_instance_ids, action):
    results = {}
    for db_instance_id in db_instance_ids:
        payload = {
            "instance_id": db_instance_id,
            "action": action
        }
        # Invoke the start_stop_rds Lambda
        try:
            response = lambda_client.invoke(
                FunctionName='arn:aws:lambda:ap-south-1:183631326320:function:start_stop_rds',  # Replace with your actual Lambda function name
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            # Collect the result for each DB
            results[db_instance_id] = json.loads(response['Payload'].read())
        except Exception as e:
            results[db_instance_id] = {"error": str(e)}
    return results





---------------------------------------------------------
{
  "action": "stop",
  "names": [
    "Navin",
    "Swashi",
    "Shubha"
  ]
}
