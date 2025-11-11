import json
import joblib
import pandas as pd
import numpy as np
import sys
import argparse
import requests

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

states_df = pd.read_csv("machine_state.csv",index_col="machine_id")
print("\nInitial State",states_df)


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


# machine_ids = ['RVREB-D6', 'RVREB-D1', 'RVREB-W6', 'RVREB-W1', 'RVREB-D4', 'RVREB-W3', 'RVREB-W8', 'RVREB-W4', 'RVREB-W5', 'RVREB-W2', 'RVREB-D5', 'RVREB-D2', 'RVREB-D3', 'RVREB-W7']
washer_id = 'RVREB-W1'
dryer_id = 'RVREB-D1'
device_id = washer_id if is_washer else dryer_id
is_available = 0
device_state = states_df.loc[device_id]

is_idle = device_state['is_idle']
is_in_use = device_state['is_in_use']
is_spin = device_state['is_spin']
has_clothes = device_state['has_clothes']
last_time_stamp = device_state['last_time_stamp']
print("last_time_stamp: ", last_time_stamp)
print("time_stamp: ", time_stamp)

# DF: is_idle, is_in_use, is_spin, has_clothes, last_time_stamp
if is_person and is_collect:
    if is_dryer: 
        if is_idle and not has_clothes:
            is_available = 0
            states_df.loc[device_id] = [0, 1, 0, 1, time_stamp]
        elif not is_idle:
            last_time = pd.to_datetime(last_time_stamp)
            current_time = pd.to_datetime(time_stamp)
            if (current_time - last_time).total_seconds() > 1200: # time lapse of 20 minutes after using
                is_available = 1
                states_df.loc[device_id] = [1, 0, 0, 0, time_stamp]
        else:
            is_available = 0
            states_df.loc[device_id] = [0, 1, 0, 1, time_stamp]
    elif is_washer:  # to include vibration data
        if is_idle: # from no one using to start using washing machine
            is_available = 0
            states_df.loc[device_id] = [0, 1, 0, 1, time_stamp]
        elif not is_idle:
            last_time = pd.to_datetime(last_time_stamp)
            current_time = pd.to_datetime(time_stamp)
            if (current_time - last_time).total_seconds() > 1200: # time lapse of 20 minutes after using
                is_available = 1
                states_df.loc[device_id] = [1, 0, 0, 0, time_stamp]
        else:
            is_available = 0
            states_df.loc[device_id] = [0, 1, 0, 1, time_stamp]

states_df.to_csv("machine_state.csv", index_label="machine_id")
print("final_state", states_df)
### Send data to AWS Lambda function

# Replace with your Lambda function URL
lambda_url = 'https://v6uenqf62ikboz5ejqojqkstp40rgawe.lambda-url.ap-southeast-1.on.aws/'  

# JSON data to post
json_data = {
    "machine_id": device_id,
    "available": str(is_available),    
}

print(json_data)
# # Send POST request
response = requests.post(lambda_url, json=json_data)

# # Check response
if response.status_code == 200:
     print("Data posted successfully:", response.json())
else:
     print("Failed to post data:", response.text)
