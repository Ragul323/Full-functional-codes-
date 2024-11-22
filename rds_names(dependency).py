import json
def lambda_handler(event, context):
    # Name to RDS instance mappings
    name_to_db_mapping = {
        "Ragul": ["db-1", "db-2","database-d"],
        "Navin": ["db-3"],
        "Swashi": ["db-4"],
        "Shubha": ["db-5", "db-6"]
    }
    return {    
        'statusCode': 200,
        'body': json.dumps(name_to_db_mapping)
    }
