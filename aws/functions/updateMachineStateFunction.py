import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

# State definitions
STATE_AVAILABLE = "available"
STATE_LOADING = "loading"
STATE_IN_USE = "in-use"
STATE_FINISHING = "finishing"
STATE_READY_TO_UNLOAD = "ready-to-unload"

def lambda_handler(event, context):
    """
    Centralized state machine that processes both IMU and camera events
    """
    print(f"Received event: {json.dumps(event)}")
    
    source = event.get('source')  # 'camera' or 'imu'
    data = event.get('data')
    machine_id = data.get('machine_id')
    
    if not machine_id:
        return {'statusCode': 400, 'body': 'Missing machine_id'}
    
    # Get table names from environment
    machine_status_table_name = os.getenv('MACHINE_STATUS_TABLE', 'MachineStatusTable')
    camera_table_name = os.getenv('CAMERA_DETECTION_TABLE', 'CameraDetectionData')
    
    machine_status_table = dynamodb.Table(machine_status_table_name)
    camera_table = dynamodb.Table(camera_table_name)
    
    # Get current machine state
    current_state = get_machine_state(machine_status_table, machine_id)
    
    # Process event based on source
    if source == 'camera':
        new_state = process_camera_event(machine_id, data, current_state, camera_table)
    elif source == 'imu':
        new_state = process_imu_event(machine_id, data, current_state, camera_table, machine_status_table)
    else:
        return {'statusCode': 400, 'body': 'Invalid source'}
    
    # Update machine state if changed
    if new_state != current_state:
        update_machine_state(machine_status_table, machine_id, new_state, data, source)
    else:
        print(f"No state change for {machine_id}, keeping: {current_state}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'machine_id': machine_id,
            'previous_state': current_state,
            'new_state': new_state,
            'source': source
        })
    }

def get_machine_state(table, machine_id):
    """Get current state from DynamoDB"""
    try:
        response = table.get_item(Key={'machineID': machine_id})
        if 'Item' in response:
            return response['Item'].get('status', STATE_AVAILABLE)
        return STATE_AVAILABLE
    except Exception as e:
        print(f"Error getting machine state: {e}")
        return STATE_AVAILABLE

def process_camera_event(machine_id, data, current_state, camera_table):
    """
    Process camera detection event
    """
    is_bending = data.get('is_bending', False)
    confidence = data.get('confidence', 0)
    
    # Low confidence - ignore
    if confidence < 0.5:
        print(f"Low confidence camera detection: {confidence}")
        return current_state
    
    # Check for recent detections (temporal consistency)
    recent_detections = get_recent_camera_detections(camera_table, machine_id, seconds=10)
    
    if len(recent_detections) < 2:
        # Not enough temporal consistency - might be passing by
        print(f"Insufficient temporal consistency: {len(recent_detections)} detections")
        return current_state
    
    # Person bending detected with high confidence
    if is_bending and confidence > 0.7:
        if current_state == STATE_AVAILABLE:
            # Person loading clothes
            print(f"State transition: {current_state} -> {STATE_LOADING}")
            return STATE_LOADING
        
        elif current_state == STATE_READY_TO_UNLOAD:
            # Person unloading clothes
            print(f"State transition: {current_state} -> {STATE_AVAILABLE}")
            return STATE_AVAILABLE
        
        elif current_state == STATE_IN_USE:
            # Check if machine has been running long enough
            state_duration = get_state_duration(machine_id)
            
            # Typical wash cycle: 30-60 min, dryer: 45-90 min
            device_type = data.get('device_type', 'washer')
            min_cycle_time = 25 * 60 if device_type == 'washer' else 35 * 60
            
            if state_duration > min_cycle_time:
                # Likely unloading after cycle complete
                print(f"State transition: {current_state} -> {STATE_AVAILABLE} (cycle complete)")
                return STATE_AVAILABLE
    
    return current_state

def process_imu_event(machine_id, data, current_state, camera_table, machine_status_table):
    """
    Process IMU vibration event with sensor fusion
    """
    is_spinning = data.get('is_spinning', 0)
    confidence = data.get('confidence', 0)
    
    # Low confidence - ignore
    if confidence < 0.5:
        print(f"Low confidence IMU detection: {confidence}")
        return current_state
    
    if is_spinning == 1:
        # Machine started spinning
        if current_state == STATE_LOADING:
            # Confirmed: user loaded clothes and started machine
            print(f"State transition: {current_state} -> {STATE_IN_USE} (spinning confirmed)")
            return STATE_IN_USE
        
        elif current_state == STATE_AVAILABLE:
            # Machine spinning but no loading detected
            # Check for recent camera loading events
            recent_loading = get_recent_camera_detections(camera_table, machine_id, seconds=120)
            
            if recent_loading:
                # Camera detected loading within 2 minutes - valid
                print(f"State transition: {current_state} -> {STATE_IN_USE} (late camera detection)")
                return STATE_IN_USE
            else:
                # Spinning without loading detected - possible missed camera event
                # Conservative: mark as in-use
                print(f"State transition: {current_state} -> {STATE_IN_USE} (no camera, IMU only)")
                return STATE_IN_USE
    
    else:  # is_spinning == 0
        # Machine stopped spinning
        if current_state == STATE_IN_USE:
            # Check cycle duration
            state_duration = get_state_duration(machine_status_table, machine_id)
            
            # Get device type from data or machine_id
            device_type = data.get('device_type', get_device_type(machine_id))
            min_cycle_time = 25 * 60 if device_type == 'washer' else 35 * 60
            
            if state_duration > min_cycle_time:
                # Normal cycle completion
                print(f"State transition: {current_state} -> {STATE_FINISHING} (cycle duration: {state_duration}s)")
                return STATE_FINISHING
            else:
                # Too short - might be door opened mid-cycle or error
                print(f"Cycle too short ({state_duration}s), keeping in-use")
                return current_state
        
        elif current_state == STATE_FINISHING:
            # Already finishing, transition to ready to unload after 2 min
            finish_duration = get_state_duration(machine_status_table, machine_id)
            if finish_duration > 2 * 60:
                print(f"State transition: {current_state} -> {STATE_READY_TO_UNLOAD}")
                return STATE_READY_TO_UNLOAD
    
    return current_state

def get_recent_camera_detections(camera_table, machine_id, seconds=10):
    """Get camera detections within last N seconds"""
    try:
        cutoff_time = int((datetime.now() - timedelta(seconds=seconds)).timestamp())
        
        response = camera_table.query(
            KeyConditionExpression='machine_id = :mid AND #ts > :cutoff',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':mid': machine_id,
                ':cutoff': Decimal(str(cutoff_time))
            },
            ScanIndexForward=False,
            Limit=10
        )
        
        return response.get('Items', [])
    except Exception as e:
        print(f"Error querying recent detections: {e}")
        return []

def get_state_duration(table, machine_id):
    """Get how long machine has been in current state (seconds)"""
    try:
        response = table.get_item(Key={'machineID': machine_id})
        if 'Item' in response:
            last_updated = response['Item'].get('lastUpdated', 0)
            if isinstance(last_updated, Decimal):
                last_updated = float(last_updated)
            return datetime.now().timestamp() - last_updated
        return 0
    except Exception as e:
        print(f"Error getting state duration: {e}")
        return 0

def get_device_type(machine_id):
    """Determine if washer or dryer from machine_id"""
    if 'W' in machine_id:
        return 'washer'
    elif 'D' in machine_id:
        return 'dryer'
    return 'washer'

def update_machine_state(table, machine_id, new_state, event_data, source):
    """Update machine state in DynamoDB"""
    try:
        timestamp = datetime.now().timestamp()
        
        table.update_item(
            Key={'machineID': machine_id},
            UpdateExpression='SET #status = :status, lastUpdated = :timestamp, lastSource = :source',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': new_state,
                ':timestamp': Decimal(str(timestamp)),
                ':source': source
            }
        )
        
        print(f"Updated {machine_id} to {new_state} (source: {source})")
        
    except Exception as e:
        print(f"Error updating machine state: {e}")
        raise

