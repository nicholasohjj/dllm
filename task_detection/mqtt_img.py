import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import time
import paho.mqtt.client as mqtt
import threading

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

# Function to simulate image update
def update_image_function(app, image_path):
    # Replace with the new image path
    app.update_image(image_path)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code: " + str(rc))
    client.subscribe("/cam/#")



def on_message(client, userdata, message):
    print("Received message from " + message.topic + " : "+ str(message.payload[:10]))
    
    if message.topic == "/cam/room" :
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}.jpg"
        with open(filename, "wb") as f:
                f.write(message.payload)
        print(f"Write to file: {filename}")
        update_image_function(app, filename)
        # os.remove(filename)

image_path = "test_img.jpg"
root = tk.Tk()
app = ImageDisplayApp(root, image_path)
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)

# Start the MQTT client loop in a separate thread
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.start()

root.mainloop()

