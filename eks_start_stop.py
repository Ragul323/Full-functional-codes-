import boto3
import json
eks_client = boto3.client('eks')
asg_client = boto3.client('autoscaling')
def get_auto_scaling_group(cluster_name, nodegroup_name):
    """Fetch the Auto Scaling Group name for the node group."""
    try:
        response = eks_client.describe_nodegroup(
            clusterName=cluster_name,
            nodegroupName=nodegroup_name
        )
        return response['nodegroup']['resources']['autoScalingGroups'][0]['name']
    except Exception as e:
        raise Exception(f"Error fetching ASG for {nodegroup_name}: {e}")
def save_scaling_configuration(asg_name):
    """Save the current scaling configuration as a tag."""
    try:
        response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        asg_info = response['AutoScalingGroups'][0]
        scaling_config = {
            "min_size": asg_info['MinSize'],
            "max_size": asg_info['MaxSize'],
            "desired_capacity": asg_info['DesiredCapacity']
        }
        # Store the scaling config as a tag
        asg_client.create_or_update_tags(
            Tags=[
                {
                    "ResourceId": asg_name,
                    "ResourceType": "auto-scaling-group",
                    "Key": "scaling_config",
                    "Value": json.dumps(scaling_config),
                    "PropagateAtLaunch": False
                }
            ]
        )
        print(f"Scaling configuration saved for {asg_name}: {scaling_config}")
    except Exception as e:
        raise Exception(f"Error saving scaling configuration for {asg_name}: {e}")
def restore_scaling_configuration(asg_name):
    """Restore the scaling configuration from the tag."""
    try:
        response = asg_client.describe_tags(Filters=[{"Name": "auto-scaling-group", "Values": [asg_name]}])
        scaling_config_tag = next(
            (tag for tag in response['Tags'] if tag['Key'] == 'scaling_config'),
            None
        )
        if not scaling_config_tag:
            raise Exception(f"No scaling configuration tag found for {asg_name}")
        scaling_config = json.loads(scaling_config_tag['Value'])
        # Restore the scaling configuration
        asg_client.update_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            MinSize=scaling_config['min_size'],
            MaxSize=scaling_config['max_size'],
            DesiredCapacity=scaling_config['desired_capacity']
        )
        print(f"Scaling configuration restored for {asg_name}: {scaling_config}")
    except Exception as e:
        raise Exception(f"Error restoring scaling configuration for {asg_name}: {e}")
def stop_cluster(cluster_name, nodegroup_name):
    """Stop a cluster by setting desired capacity to 0 and saving the scaling config for all nodes."""
    try:
        asg_name = get_auto_scaling_group(cluster_name, nodegroup_name)
        save_scaling_configuration(asg_name)
        response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        current_capacity = response['AutoScalingGroups'][0]['DesiredCapacity']
        if current_capacity > 0:
            asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                MinSize=0,
                MaxSize=0,
                DesiredCapacity=0
            )
            print(f"All nodes in cluster {cluster_name} stopped successfully.")
        else:
            print(f"No nodes to stop in cluster {cluster_name}.")
    except Exception as e:
        raise Exception(f"Error stopping cluster {cluster_name}: {e}")
def start_cluster(cluster_name, nodegroup_name):
    """Start a cluster by restoring its scaling configuration for all nodes."""
    try:
        asg_name = get_auto_scaling_group(cluster_name, nodegroup_name)
        restore_scaling_configuration(asg_name)
        print(f"Cluster {cluster_name} started successfully.")
    except Exception as e:
        raise Exception(f"Error starting cluster {cluster_name}: {e}")
def check_ragul_status():
    """Check if Ragul's cluster is running or stopped."""
    try:
        # Assuming Ragul's cluster and nodegroup names are fixed
        asg_name = get_auto_scaling_group("ragul", "ragul_workernode")
        response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        desired_capacity = response['AutoScalingGroups'][0]['DesiredCapacity']
        return desired_capacity > 0  # If desired_capacity > 0, Ragul is running
    except Exception as e:
        raise Exception(f"Error checking Ragul's status: {e}")
def lambda_handler(event, context):
    """AWS Lambda function entry point."""
    try:
        for cluster_action in event["clusters"]:
            cluster_name = cluster_action["cluster_name"]
            nodegroup_name = cluster_action["nodegroup_name"]
            action = cluster_action["action"]
            # If the cluster is Yuvi, Arun, or Durga, check the status of Ragul
            if cluster_name in ["yuvi", "arun", "durga"]:
                ragul_is_running = check_ragul_status()
                # If Ragul is stopped, start it first
                if not ragul_is_running:
                    print("Ragul is stopped, starting Ragul first.")
                    start_cluster("ragul", "ragul_workernode")
                # Now start or stop the requested cluster
                if action == "stop":
                    stop_cluster(cluster_name, nodegroup_name)
                elif action == "start":
                    start_cluster(cluster_name, nodegroup_name)
                else:
                    raise Exception(f"Invalid action: {action}")
            else:
                # If the action is on Ragul, just perform it
                if action == "stop":
                    stop_cluster(cluster_name, nodegroup_name)
                elif action == "start":
                    start_cluster(cluster_name, nodegroup_name)
                else:
                    raise Exception(f"Invalid action: {action}")
        return {
            "statusCode": 200,
            "message": f"Operations completed for the provided clusters."
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "message": str(e)
        }



-------------------------------------------------------
{
  "clusters": [
    {
      "cluster_name": "arun",
      "nodegroup_name": "arun_workernode",
      "action": "start"
    },
    {
      "cluster_name": "yuvi",
      "nodegroup_name": "yuvi_workernode",
      "action": "start"
    },
    {
      "cluster_name": "durga",
      "nodegroup_name": "durga_workernode",
      "action": "stop"
    },
    {
      "cluster_name": "ragul",
      "nodegroup_name": "ragul_workernode",
      "action": "stop"
    }
  ]
}
