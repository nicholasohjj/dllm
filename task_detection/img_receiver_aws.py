#!/usr/bin/env python3
"""
Camera Data Processor for AWS IoT Core Integration
This script receives camera images from local MQTT, processes them with YOLOv7,
and publishes detection results to AWS IoT Core for centralized state management.
"""

import os
import json
import time
import subprocess
import threading
import gc
from datetime import datetime
import paho.mqtt.client as mqtt

# AWS IoT imports (requires: pip install awsiotsdk)
try:
    from awscrt import mqtt as aws_mqtt, io
    from awsiot import mqtt_connection_builder
    AWS_IOT_AVAILABLE = True
except ImportError:
    print("WARNING: AWS IoT SDK not installed. Install with: pip install awsiotsdk")
    AWS_IOT_AVAILABLE = False

# Configuration
LOCAL_BROKER = 'localhost'
LOCAL_BROKER_PORT = 1883

# AWS IoT Core Configuration
# Update these with your actual AWS IoT endpoint and certificate paths
AWS_IOT_ENDPOINT = os.getenv('AWS_IOT_ENDPOINT', 'YOUR_AWS_IOT_ENDPOINT.iot.ap-southeast-1.amazonaws.com')
AWS_CLIENT_ID = os.getenv('AWS_CLIENT_ID', 'camera-processor-1')
AWS_CERT_PATH = os.getenv('AWS_CERT_PATH', './certs/certificate.pem.crt')
AWS_KEY_PATH = os.getenv('AWS_KEY_PATH', './certs/private.pem.key')
AWS_CA_PATH = os.getenv('AWS_CA_PATH', './certs/AmazonRootCA1.pem')
AWS_CAMERA_TOPIC = 'laundry/camera'

IMAGE_INPUT_FOLDER = 'images/'
JSON_OUTPUT_FOLDER = 'json_output/'

class CameraDataProcessor:
    def __init__(self):
        # Local MQTT client (receives raw images from ESP32)
        self.local_client = mqtt.Client()
        self.local_client.on_connect = self.on_local_connect
        self.local_client.on_message = self.on_local_message
        
        # AWS IoT connection (publishes detection results)
        self.aws_connection = None
        if AWS_IOT_AVAILABLE:
            self.setup_aws_connection()
        else:
            print("WARNING: Running in local-only mode without AWS IoT connection")
        
        # Track recent detections for temporal consistency
        self.recent_detections = {}  # machine_id -> list of recent detection times
        
    def setup_aws_connection(self):
        """Setup AWS IoT Core MQTT connection"""
        try:
            # Check if certificate files exist
            if not all(os.path.exists(p) for p in [AWS_CERT_PATH, AWS_KEY_PATH, AWS_CA_PATH]):
                print(f"ERROR: AWS IoT certificates not found. Please place them in:")
                print(f"  - {AWS_CERT_PATH}")
                print(f"  - {AWS_KEY_PATH}")
                print(f"  - {AWS_CA_PATH}")
                print("Running in local-only mode.")
                return
            
            # Create event loop
            event_loop_group = io.EventLoopGroup(1)
            host_resolver = io.DefaultHostResolver(event_loop_group)
            client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
            
            # Build MQTT connection
            self.aws_connection = mqtt_connection_builder.mtls_from_path(
                endpoint=AWS_IOT_ENDPOINT,
                cert_filepath=AWS_CERT_PATH,
                pri_key_filepath=AWS_KEY_PATH,
                ca_filepath=AWS_CA_PATH,
                client_bootstrap=client_bootstrap,
                client_id=AWS_CLIENT_ID,
                clean_session=False,
                keep_alive_secs=30
            )
            
            print(f"Connecting to AWS IoT Core at {AWS_IOT_ENDPOINT}...")
            connect_future = self.aws_connection.connect()
            connect_future.result()
            print("✓ Connected to AWS IoT Core!")
            
        except Exception as e:
            print(f"ERROR: Failed to connect to AWS IoT Core: {e}")
            print("Running in local-only mode.")
            self.aws_connection = None
    
    def on_local_connect(self, client, userdata, flags, rc):
        """Callback when connected to local MQTT broker"""
        print(f"Connected to local MQTT broker with result code: {rc}")
        client.subscribe("/cam/room")
        print("Subscribed to /cam/room")
    
    def on_local_message(self, client, userdata, message):
        """Receive raw image from ESP32, process locally, publish results to AWS"""
        if message.topic == "/cam/room":
            print(f"\nReceived camera image ({len(message.payload)} bytes)")
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}.jpg"
            filepath = os.path.join(IMAGE_INPUT_FOLDER, filename)
            
            # Save image locally
            os.makedirs(IMAGE_INPUT_FOLDER, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(message.payload)
            print(f"Saved to: {filepath}")
            
            # Process image in background thread to not block MQTT
            thread = threading.Thread(
                target=self.process_and_publish,
                args=(filename,),
                daemon=True
            )
            thread.start()
    
    def process_and_publish(self, filename):
        """Process camera image and publish results to AWS IoT Core"""
        try:
            # Run YOLOv7 pose detection
            detection_result = self.process_camera_image(filename)
            
            if detection_result:
                print(f"Detection result: {json.dumps(detection_result, indent=2)}")
                
                # Publish to AWS IoT Core
                if self.aws_connection:
                    self.publish_to_aws(detection_result)
                else:
                    print("AWS IoT not connected - result not published to cloud")
            else:
                print("No person detected in image")
            
        except Exception as e:
            print(f"ERROR processing image: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            gc.collect()
    
    def process_camera_image(self, filename):
        """Run YOLOv7 pose detection and classification"""
        try:
            # Run img_processing.py (existing YOLOv7 processing)
            print("Running pose detection...")
            result = subprocess.run(
                ['python3', 'img_processing.py', '-f', filename],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode != 0:
                print(f"ERROR in img_processing: {result.stderr}")
                return None
            
            # Get the output JSON file
            file_base = filename.split('.')[0]
            json_path = os.path.join(JSON_OUTPUT_FOLDER, f"{file_base}.json")
            
            if not os.path.exists(json_path):
                print(f"No pose JSON found at {json_path}")
                return None
            
            # Load pose keypoints
            with open(json_path, 'r') as f:
                pose_data = json.load(f)
            
            # Run classification model
            detection = self.classify_pose(pose_data['pose_keypoints_2d'], file_base)
            
            return detection
            
        except Exception as e:
            print(f"ERROR in process_camera_image: {e}")
            return None
    
    def classify_pose(self, keypoints, timestamp):
        """
        Classify pose using existing logic from CS3237_camera_model_3.py
        Returns detection result with confidence
        """
        try:
            # Import the get_prediction function
            import sys
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from CS3237_camera_model_3 import get_prediction, calculate_angle
            
            prediction = get_prediction(keypoints)
            
            is_person = prediction[0][0] == 1
            is_washer = prediction[0][1] == 0
            is_dryer = prediction[0][1] == 1
            is_walking = prediction[0][1] == 2
            is_collecting = prediction[0][2] == 1
            
            if not is_person:
                return None
            
            # Calculate confidence based on keypoint confidence values
            confidence = self.calculate_confidence(keypoints)
            
            # Determine machine ID
            # In production, this should be mapped from camera position
            # For now, use classification result
            if is_washer:
                machine_id = "RVREB-W1"
                device_type = "washer"
            elif is_dryer:
                machine_id = "RVREB-D1"
                device_type = "dryer"
            else:
                # Walking/unknown - skip
                return None
            
            # Update temporal tracking
            if machine_id not in self.recent_detections:
                self.recent_detections[machine_id] = []
            
            self.recent_detections[machine_id].append(time.time())
            
            # Keep only last 10 seconds of detections
            cutoff = time.time() - 10
            self.recent_detections[machine_id] = [
                t for t in self.recent_detections[machine_id] if t > cutoff
            ]
            
            # Calculate temporal consistency confidence
            num_recent = len(self.recent_detections[machine_id])
            temporal_confidence = min(num_recent / 2.0, 1.0)  # Max at 2 detections
            
            # Combined confidence
            combined_confidence = (confidence * 0.7 + temporal_confidence * 0.3)
            
            return {
                "machine_id": machine_id,
                "device_type": device_type,
                "event_type": "person_detected",
                "is_bending": is_collecting,
                "confidence": round(combined_confidence, 3),
                "timestamp": int(time.time()),
                "sensor_type": "camera",
                "temporal_detections": num_recent,
                "raw_confidence": round(confidence, 3)
            }
            
        except Exception as e:
            print(f"ERROR in classify_pose: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_confidence(self, keypoints):
        """Calculate confidence score from keypoint confidence values"""
        # Keypoints format: [x1, y1, conf1, x2, y2, conf2, ...]
        confidences = [keypoints[i] for i in range(2, len(keypoints), 3)]
        
        if not confidences:
            return 0.0
        
        # Use average of top 70% confidence keypoints
        confidences_sorted = sorted(confidences, reverse=True)
        top_70_percent = confidences_sorted[:max(1, int(len(confidences_sorted) * 0.7))]
        avg_confidence = sum(top_70_percent) / len(top_70_percent)
        
        return avg_confidence
    
    def publish_to_aws(self, detection_result):
        """Publish detection result to AWS IoT Core"""
        if not self.aws_connection:
            print("AWS IoT connection not available")
            return
        
        try:
            payload = json.dumps(detection_result)
            
            print(f"Publishing to AWS IoT Core topic '{AWS_CAMERA_TOPIC}'...")
            publish_future, packet_id = self.aws_connection.publish(
                topic=AWS_CAMERA_TOPIC,
                payload=payload,
                qos=aws_mqtt.QoS.AT_LEAST_ONCE
            )
            
            publish_future.result()
            print(f"✓ Published to AWS IoT Core (packet_id: {packet_id})")
            
        except Exception as e:
            print(f"ERROR publishing to AWS: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Start the processor"""
        print("=" * 60)
        print("Camera Data Processor for AWS IoT Core")
        print("=" * 60)
        print(f"Local MQTT Broker: {LOCAL_BROKER}:{LOCAL_BROKER_PORT}")
        print(f"AWS IoT Endpoint: {AWS_IOT_ENDPOINT}")
        print(f"AWS Client ID: {AWS_CLIENT_ID}")
        print(f"Camera Topic: {AWS_CAMERA_TOPIC}")
        print("=" * 60)
        
        # Ensure directories exist
        os.makedirs(IMAGE_INPUT_FOLDER, exist_ok=True)
        os.makedirs(JSON_OUTPUT_FOLDER, exist_ok=True)
        
        print("\nConnecting to local MQTT broker...")
        self.local_client.connect(LOCAL_BROKER, LOCAL_BROKER_PORT, 60)
        print("Starting MQTT loop...")
        self.local_client.loop_forever()

def main():
    """Main entry point"""
    processor = CameraDataProcessor()
    try:
        processor.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        if processor.aws_connection:
            disconnect_future = processor.aws_connection.disconnect()
            disconnect_future.result()
            print("Disconnected from AWS IoT Core")

if __name__ == "__main__":
    main()

