# git clone https://github.com/WongKinYiu/yolov7.git
# make folder - images/ images_output/ json_output/
# wget https://github.com/WongKinYiu/yolov7/releases/download/v0.1/yolov7-w6-pose.pt

import argparse
import sys
import threading
import gc
import os
import torch
import cv2
from torchvision import transforms
import numpy as np
import json

sys.path.append('yolov7')
from utils.datasets import letterbox
from utils.general import non_max_suppression_kpt
from utils.plots import output_to_keypoint, plot_skeleton_kpts

gc.enable()
# Initialize parser
parser = argparse.ArgumentParser(description="Process the filename from command line arguments.")
# Add an argument for the filename with a default value
parser.add_argument('-f', '--file', type=str, default="empty.jpg", help="Filename to process")
# Parse the arguments
args = parser.parse_args()
input_image = args.file
file_name, file_format = input_image.split("/")[-1].split(".")
path_input_image = 'images/' + input_image
# path_input_image = input_image 
path_output_json = 'json_output/' + file_name + '.json'
path_output_image = 'images_output/' + file_name + '_out.' + file_format

def rotate_image(filepath, rotation_type):
    # Read the image from the file path
    image = cv2.imread(filepath)
    
    # Check if the image was loaded successfully
    if image is None:
        print("Error: Image not found.")
        return

    # Rotate based on specified type
    if rotation_type == '90_clockwise':
        rotated_image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_type == '90_counterclockwise':
        rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotation_type == '180':
        rotated_image = cv2.rotate(image, cv2.ROTATE_180)
    else:
        print("Invalid rotation type. Use '90_clockwise', '90_counterclockwise', or '180'.")
        return    
    # Write the rotated image back to the same file path
    cv2.imwrite(filepath, rotated_image)
    print(f"Rotated image saved to {filepath}")

thr = threading.Thread(rotate_image(path_input_image, '90_clockwise'))
thr.start()

def clear_resources():
  gc.collect()
  torch.cuda.empty_cache()

th_cl = threading.Thread(clear_resources())
th_cl.start()

# Initialize the model
model_weight = "yolov7-w6-pose.pt"
device_type = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
device = torch.device(device_type)
weights = torch.load(model_weight, map_location=device)
model = weights['model']
for param in model.parameters():
    param.grad = None
_ = model.float().eval()
if device_type != "cpu":
  model.half().to(device)
print(device_type)

def process_image(image_path, rotate=None):
  image = cv2.imread(image_path)
  # image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
  image = letterbox(image, 960, stride=128, auto=True)[0]
  image = transforms.ToTensor()(image)
  image = torch.tensor(np.array([image.numpy()]))
  if device_type != "cpu":
    image = image.half().to(device)
  output, _ = model(image)
  output = non_max_suppression_kpt(output, 0.25, 0.65, nc=model.yaml['nc'], nkpt=model.yaml['nkpt'], kpt_label=True)
  with torch.no_grad():
    output = output_to_keypoint(output)
  image_tensor = image
  gc.collect()
  torch.cuda.empty_cache()
  return output, image_tensor

def save_output(output, image_tensor, output_image_path, output_json_path, label=None):
  keypoints = output[0, 7:].T.tolist()
  with open(output_json_path, 'w') as json_file:
    json.dump({"pose_keypoints_2d": keypoints}, json_file)
  # Draw bounding boxes and keypoints on the image
  nimg = image_tensor[0].permute(1, 2, 0) * 255
  nimg = nimg.cpu().numpy().astype(np.uint8)
  nimg = cv2.cvtColor(nimg, cv2.COLOR_RGB2BGR)
  for idx in range(output.shape[0]):
    plot_skeleton_kpts(nimg, output[idx, 7:].T, 3)
  if label: # write label at the corner of image
    text_coordinate = (50, 50)
    cv2.putText(nimg, label, text_coordinate, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 5)
  # Save the modified image with detection lines
  cv2.imwrite(output_image_path, nimg)

def output_to_pose_coordinate(output):
  if len(output) == 0:
    return []
  keypoints = output[0, 7:].T.tolist()
  pose_coordinate = []
  for i in range(0, len(keypoints), 3):
    pose_coordinate.append((keypoints[i], keypoints[i+1]))
  return pose_coordinate

# Function to calculate the angle between three keypoints (a, b, c)
def calculate_angle(a, b, c):
    a = np.array(a)  # First keypoint
    b = np.array(b)  # Middle keypoint (joint)
    c = np.array(c)  # Last keypoint
    # Calculate the angle in radians and convert to degrees
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    # If the angle is greater than 180 degrees, adjust it
    return angle if angle <= 180.0 else (360 - angle)

def display_image(fp):
  image = cv2.imread(fp)
  if image is None:
    print("Error in finding image to display")
    return
  cv2.imshow("Image Display", image)
  cv2.waitKey(3000)
  cv2.destroyAllWindows()


# Pose coordinate definition:
  # 0: Nose
  # 1: Left Eye
  # 2: Right Eye
  # 3: Left Ear
  # 4: Right Ear
  # 5: Left Shoulder
  # 6: Right Shoulder
  # 7: Left Elbow
  # 8: Right Elbow
  # 9: Left Wrist
  # 10: Right Wrist
  # 11: Left Hip
  # 12: Right Hip
  # 13: Left Knee
  # 14: Right Knee
  # 15: Left Ankle
  # 16: Right Ankle
print(path_input_image)
output, image_tensor = process_image(path_input_image, cv2.ROTATE_90_CLOCKWISE)
pose_coordinate = output_to_pose_coordinate(output)
if len(pose_coordinate) == 0:
  print("No person detected.")
  display_image(path_input_image)
else:  
  save_output(output, image_tensor, path_output_image, path_output_json)
  display_image(path_output_image)
  thr = threading.Thread(target=os.system,
                            args=(f'python3 CS3237_camera_model_3.py -f {path_output_json}',))
  thr.start()
  # os.remove(path_output_image)
  # os.remove(path_output_json)
print(f"Output image: {path_output_image}: {pose_coordinate}")
# os.remove(path_input_image)

clear_resources()
  