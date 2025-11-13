import json
import joblib
import pandas as pd
import numpy as np
import sys
import argparse
import requests
from datetime import datetime

COllECT_ANGLE_THRESHOLD = 150

def calculate_angle(x1,y1,x2,y2,x3,y3):
    # Calculate the angle in radians and convert to degrees
    radians = np.arctan2(y3 - y2, x3 -x2) - np.arctan2(y1 - y2, x1 - x2)
    angle = np.abs(radians * 180.0 / np.pi)
    # If the angle is greater than 180 degrees, adjust it
    return angle if angle <= 180.0 else (360 - angle)

def get_prediction(keypoints):
    #check if head node confidence level > 0.5
    if (keypoints[2] > 0.5 or keypoints[5] > 0.5 or keypoints[8] > 0.5 or keypoints[11] > 0.5 or keypoints[14] > 0.5):

        pred = [[0,0,0]]

         # ML predicts use head node data to predict where head is 
        df = pd.DataFrame([keypoints])

        # predict dryer or washer or walking with (any one of the) head coordinates
        if keypoints[2] > 0.5:         
            df = df.iloc[:, 0:2]
            clf = joblib.load("json_model_2.joblib")
            head_predict = clf.predict(df)
            pred[0][1] = head_predict[0]
            
        elif keypoints[5] > 0.5:
            df = df.iloc[:, 3:5]
            clf = joblib.load("json_model_2.joblib")
            head_predict = clf.predict(df)
            pred[0][1] = head_predict[0]
            
        elif keypoints[8] > 0.5:
            df = df.iloc[:, 6:8]
            clf = joblib.load("json_model_2.joblib")
            head_predict = clf.predict(df)
            pred[0][1] = head_predict[0]
            
        elif keypoints[11] > 0.5:
            df = df.iloc[:, 9:11]
            clf = joblib.load("json_model_2.joblib")
            head_predict = clf.predict(df)[0]
            pred[0][1] = head_predict
            
        elif keypoints[13] > 0.5:
            df = df.iloc[:, 12:14]
            clf = joblib.load("json_model_2.joblib")
            head_predict = clf.predict(df)[0]
            pred[0][1] = head_predict

        # check if shoulder and hip and knee of one side of the body is present (aka their confidence lvl > 0.5)
        if ((keypoints[17] > 0.5 and keypoints[35] > 0.5 and keypoints[41] > 0.5) or (keypoints[20] > 0.5 and keypoints[38] > 0.5 and keypoints[44] > 0.5)):

            angle = calculate_angle(keypoints[15], keypoints[16], keypoints[33], keypoints[34], keypoints[39], keypoints[40])

            #check if angle between shoulder, knee and hip < 150
            if (angle < COllECT_ANGLE_THRESHOLD):
                pred[0][0] = 1 #got ppl
                pred[0][2] = 1 #collect
                return pred

            else:
                pred[0][0] = 1 #got ppl but no collect
                return pred

        else:
            return pred

    else:
        return [[0,0,0]]


parser = argparse.ArgumentParser(description="Process the filename from command line arguments.")
parser.add_argument('-f', '--file', type=str, default="empty.json", help="Filename to process")
args = parser.parse_args()
input_json = args.file
filepath = input_json.rsplit('.', 1)[0]
time_stamp = filepath.rsplit('/', 1)[1]

with open(input_json, 'r') as file:
    data = json.load(file)
pose_keypoints = data.get("pose_keypoints_2d", [])

if not pose_keypoints:
    print("Error: 'pose_keypoints_2d' data not found or is empty.")
    sys.exit()
    
prediction = get_prediction(pose_keypoints)
       
is_person = prediction[0][0] == 1
is_washer = prediction[0][1] == 0
is_dryer = prediction[0][1] == 1
is_walking = prediction[0][1] == 2
is_collect = prediction[0][2] == 1

print("person :", is_person)
print("washer :", is_washer)
print("dryer :", is_dryer)
print("walking :", is_walking)
print("collect :", is_collect)

# Determine device ID and type
washer_id = 'RVREB-W1'
dryer_id = 'RVREB-D1'
device_id = washer_id if is_washer else dryer_id
device_type = 'washer' if is_washer else 'dryer'

# Calculate confidence based on prediction
# Higher confidence if person detected with clear bending action
confidence = 0.8 if is_person and is_collect else 0.6 if is_person else 0.3
### Send data to AWS Lambda function (processCameraDataFunction)

# Lambda function URL for camera data processing
lambda_url = 'https://v6uenqf62ikboz5ejqojqkstp40rgawe.lambda-url.ap-southeast-1.on.aws/'  

# Prepare camera detection data for AWS
# Convert timestamp to Unix timestamp
timestamp_dt = datetime.strptime(time_stamp, '%Y%m%d-%H%M%S')
unix_timestamp = timestamp_dt.timestamp()

json_data = {
    "machine_id": device_id,
    "timestamp": unix_timestamp,
    "device_type": device_type,
    "event_type": "person_detected" if is_person else "no_detection",
    "is_bending": is_collect,  # is_collect indicates bending/loading action
    "confidence": confidence,
    "sensor_type": "camera",
    # Additional context
    "is_person": is_person,
    "is_walking": is_walking
}

print(f"\nSending camera detection data to AWS:")
print(json.dumps(json_data, indent=2))

# Send POST request
try:
    response = requests.post(lambda_url, json=json_data)
    
    if response.status_code == 200:
        print("\n✓ Data posted successfully:", response.json())
    else:
        print(f"\n✗ Failed to post data (status {response.status_code}):", response.text)
except Exception as e:
    print(f"\n✗ Error sending data to AWS: {e}")
