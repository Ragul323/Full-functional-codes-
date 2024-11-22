import boto3
import time
import uuid
rds_client = boto3.client('rds')
def lambda_handler(event, context):
    # Retrieve parameters from JSON input
    running_instance_id = event.get('running_instance_id')
    snapshot_id = event.get('snapshot_id')
    if not running_instance_id or not snapshot_id:
        return {
            'statusCode': 400,
            'body': 'Error: Missing required parameters in input JSON. Please provide running_instance_id and snapshot_id.'
        }
    # Step 1: Check if the RDS instance exists
    try:
        print(f"Checking existence of RDS instance: {running_instance_id}")
        rds_client.describe_db_instances(DBInstanceIdentifier=running_instance_id)
        instance_exists = True
    except rds_client.exceptions.DBInstanceNotFoundFault:
        print(f"RDS instance {running_instance_id} not found.")
        instance_exists = False
    except Exception as e:
        print(f"Error checking RDS instance: {e}")
        return {
            'statusCode': 500,
            'body': f"Failed to check RDS instance {running_instance_id}: {str(e)}"
        }
    # Step 2: If the RDS instance exists, rename it
    if instance_exists:
        try:
            # Generate a new identifier for renaming the existing instance
            new_instance_id = f"{running_instance_id}-old-{uuid.uuid4().hex[:8]}"
            print(f"Renaming RDS instance {running_instance_id} to {new_instance_id}")
            rds_client.modify_db_instance(
                DBInstanceIdentifier=running_instance_id,
                NewDBInstanceIdentifier=new_instance_id,
                ApplyImmediately=True
            )
            # Wait until the instance is renamed
            waiter = rds_client.get_waiter('db_instance_available')
            waiter.wait(DBInstanceIdentifier=new_instance_id)
            print(f"Renamed RDS instance to: {new_instance_id}")
            # Step 3: Delete the renamed RDS instance
            print(f"Deleting renamed RDS instance: {new_instance_id}")
            rds_client.delete_db_instance(
                DBInstanceIdentifier=new_instance_id,
                SkipFinalSnapshot=True
            )
            # Wait until the instance is deleted
            waiter = rds_client.get_waiter('db_instance_deleted')
            waiter.wait(DBInstanceIdentifier=new_instance_id)
            print(f"Deleted renamed RDS instance: {new_instance_id}")
            # Add a delay to ensure the instance identifier is fully released before restoration
            print("Waiting 20 seconds before restoring...")
            time.sleep(20)  # Adjust delay time if necessary
        except Exception as e:
            print(f"Error renaming or deleting RDS instance: {e}")
            return {
                'statusCode': 500,
                'body': f"Failed to rename or delete RDS instance {running_instance_id}: {str(e)}"
            }
    # Step 4: Restore the RDS instance from the snapshot (using the original identifier)
    try:
        print(f"Restoring RDS instance from snapshot: {snapshot_id} as {running_instance_id}")
        response = rds_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=running_instance_id,
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceClass='db.t3.micro',  # Adjust to your required instance class
            MultiAZ=False,
            PubliclyAccessible=True  # Set to True or False as required
        )
        # Wait until the instance is available
        waiter = rds_client.get_waiter('db_instance_available')
        waiter.wait(DBInstanceIdentifier=running_instance_id)
        print(f"Restored RDS instance: {running_instance_id} from snapshot {snapshot_id}")
    except Exception as e:
        print(f"Error restoring RDS instance: {e}")
        return {
            'statusCode': 500,
            'body': f"Failed to restore RDS instance from snapshot {snapshot_id}: {str(e)}"
        }
    return {
        'statusCode': 200,
        'body': f"Successfully renamed {running_instance_id} (if it existed), deleted it, and restored it from snapshot {snapshot_id}"
    }
