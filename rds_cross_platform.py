import boto3
# Assume role in another account
def assume_role(account_id, role_name):
    sts_client = boto3.client('sts')
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::183631326320:role/lambda_rds_roles",
        RoleSessionName="CrossAccountRDSAccess"
    )
    return assumed_role['Credentials']
# Check the status of an RDS instance
def is_db_running(rds_client, db_instance_id):
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        status = response['DBInstances'][0]['DBInstanceStatus']
        print(f"DB Status for {db_instance_id}: {status}")
        return status == "available"
    except Exception as e:
        print(f"Error checking status for {db_instance_id}: {e}")
        return False
# Manage RDS instances in the respective account
def manage_rds(credentials=None, database_instance_ids=[], action="start"):
    try:
        if credentials:
            rds_client = boto3.client(
                'rds',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            rds_client = boto3.client('rds')
        for db_instance_id in database_instance_ids:
            if action == "start":
                response = rds_client.start_db_instance(DBInstanceIdentifier=db_instance_id)
            elif action == "stop":
                response = rds_client.stop_db_instance(DBInstanceIdentifier=db_instance_id)
            print(f"Action '{action}' performed on {db_instance_id}: {response}")
    except Exception as e:
        print(f"Error managing RDS {database_instance_ids}: {e}")
# Lambda handler
def lambda_handler(event, context):
    print(f"Received event: {event}")
    action = event.get('action')  # 'start' or 'stop'
    target_db = event.get('target_db')  # e.g., 'database-2'
    # Database identifiers
    account_1_db_ids = ["database-1", "database-2"]  # Internal account
    account_2_db_ids = ["database-a", "database-b"]  # External account
    account_2_id = "183631326320"
    account_2_role = "lambda_rds_roles"
    # Setup RDS clients
    try:
        internal_rds_client = boto3.client('rds')
        external_credentials = assume_role(account_2_id, account_2_role)
        external_rds_client = boto3.client(
            'rds',
            aws_access_key_id=external_credentials['AccessKeyId'],
            aws_secret_access_key=external_credentials['SecretAccessKey'],
            aws_session_token=external_credentials['SessionToken']
        )
    except Exception as e:
        print(f"Error setting up RDS clients: {e}")
        return
    # Determine action based on target_db
    if target_db in account_1_db_ids:
        print(f"Target DB {target_db} is in internal account.")
        if target_db == "database-2":
            db_1_running = is_db_running(internal_rds_client, "database-1")
            db_a_running = is_db_running(external_rds_client, "database-a")
            db_b_running = is_db_running(external_rds_client, "database-b")
            print(f"DB-1 Running: {db_1_running}, DB-A Running: {db_a_running}, DB-B Running: {db_b_running}")
            if action == "stop":
                if db_1_running or db_a_running or db_b_running:
                    manage_rds(database_instance_ids=["database-2"], action="stop")
                else:
                    manage_rds(database_instance_ids=["database-2", "database-1"], action="stop")
            elif action == "start":
                if not db_1_running:
                    manage_rds(database_instance_ids=["database-1"], action="start")
                manage_rds(database_instance_ids=["database-2"], action="start")
    elif target_db in account_2_db_ids:
        print(f"Target DB {target_db} is in external account.")
        db_1_running = is_db_running(internal_rds_client, "database-1")
        db_2_running = is_db_running(internal_rds_client, "database-2")
        print(f"DB-1 Running: {db_1_running}, DB-2 Running: {db_2_running}")
        if action == "stop":
            if db_1_running and db_2_running:
                manage_rds(
                    credentials=external_credentials,
                    database_instance_ids=[target_db],
                    action="stop"
                )
        elif action == "start":
            if not db_1_running:
                manage_rds(database_instance_ids=["database-1"], action="start")
            manage_rds(
                credentials=external_credentials,
                database_instance_ids=[target_db],
                action="start"
            )
    else:
        print(f"Unknown target_db: {target_db}. No action performed.")
