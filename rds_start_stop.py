import boto3
import json
def lambda_handler(event, context):
    # Print the event for debugging
    print("Received event:", json.dumps(event))
    # Ensure event contains the required keys
    if 'instance_id' not in event or 'action' not in event:
        return {
            'statusCode': 400,
            'body': 'Missing "instance_id" or "action" in the request.'
        }
    rds = boto3.client('rds')
    instance_id = event['instance_id']
    action = event['action']
    if action == 'start':
        response = rds.start_db_instance(DBInstanceIdentifier=instance_id)
        message = f'Starting RDS instance {instance_id}.'
    elif action == 'stop':
        response = rds.stop_db_instance(DBInstanceIdentifier=instance_id)
        message = f'Stopping RDS instance {instance_id}.'
    else:
        message = f'Invalid action: {action}. Only "start" or "stop" allowed.'
    return {
        'statusCode': 200,
        'body': message
    }
