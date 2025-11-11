# run this file, it will call the img_processing.py file to process the image
# img_processing.py will call the CS3237_camera_model.py file to process the image if a person is detected

import os
import threading
import time
import paho.mqtt.client as mqtt
import gc

import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk

broker_ip_addr = 'localhost'
image_input_folder = 'images/'
first_image_path = image_input_folder + "test_img.jpg"

def write_image_to_process(payload):
    gc.collect()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = image_input_folder + f"{timestamp}.jpg"
    with open(filename, "wb") as f:
        f.write(payload)
        print(f"Write to file: {filename}")

    thr = threading.Thread(target=os.system,
                           args=(f'python3 img_processing.py -f {timestamp}.jpg',))
    thr.start()
    return filename

# Function to simulate image update
# def update_image_function(app, image_path):
#     # Replace with the new image path
#     app.update_image(image_path)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code: " + str(rc))
    client.subscribe("/cam/#")
    client.subscribe("laundry/vibration") #CHANGE

def on_message(client, userdata, message):
    print("Received message from " + message.topic + " : "+ str(message.payload[:10]))
    
    if message.topic == "/cam/room" :
        # print("Received image from room camera")
        write_image_to_process(message.payload)
        # update_image_function(app, file_name)

    ## add more elif statements for other topics
    elif message.topic == "laundry/vibration": #CHANGE
        thr = threading.Thread(target=os.system, 
                           args=(f'python3 wash_data.py -i {message.payload.decode('UTF-8')}',))
        thr.start()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker_ip_addr, 1883, 60)

client.loop_forever()

class ImageDisplayApp:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("Image Display")
        
        # Load the initial image
        self.image_path = image_path
        self.load_image()

        # Display the image
        self.label = Label(root, image=self.img)
        self.label.pack()

    def load_image(self):
        # Open the image and resize it (optional)
        image = Image.open(self.image_path)
        image = image.resize((500, 500))  # Resize to a suitable size
        image = image.rotate(90)  # Rotate the image to the right (-90)
        self.img = ImageTk.PhotoImage(image)

    def update_image(self, new_image_path):
        # Update the image with a new one
        self.image_path = new_image_path
        self.load_image()
        self.label.config(image=self.img)
        self.label.image = self.img  # Keep a reference to the image to avoid garbage collection


root = tk.Tk()
app = ImageDisplayApp(root, first_image_path)

# Start the MQTT client loop in a separate thread
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.start()

root.mainloop()
