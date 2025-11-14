**Project Proposal – Team 17**	  
**Team Members:**   
Chao Yi-Ju, Nicholas Oh Jia Jun, Cheah Hao Yi, James Wong Guan Xian  
**Project/Team Title: Don’t Leave Laundry Messy (DLLM)**

**Introduction / Problem Statement:**   
At Ridge View Residential College, laundry rooms are often crowded, and students struggle to find if there are machines available without making unnecessary trips. Additionally, there’s no reliable way for students to know if their laundry is finished without physically checking it out, which is inefficient and a waste of time. We aim to address such inefficiency to optimize laundry room usage by providing real-time updates on machine availability.

**Proposed IoT Solution:**   
We propose DLLM, a smart IoT-based laundry management system. This system will monitor the status of washing machines and dryers in real-time. It will display the available and occupied machines to the users and notify users via a web application when a subscribed machine completes with a cycle. The system will leverage non-invasive sensors to detect machine usage and integrate ESP32-S3-EYE cameras to detect crowd level in the laundry room. The data will be further uploaded to a cloud-based platform for machine learning forecasting and real-time user notifications.

**Sensors /Actuators /Hardware Used:**   
**Sensors:** 

- Vibration sensors will be added to detect machine movement, confirming whether the machine is actively running.  
- ESP32-S3-EYE camera will also be used for one of the IoT devices to record videos of the laundry room for better prediction and testing of the machine learning model.  
- Infrared human body sensors will be added to detect people entering the laundry room, this will help monitoring the crowd level of the laundry room.

**Microcontrollers:** ESP32 will gather sensor data and send it to the cloud in real-time.   
**Power Supply:** The system will use a power bank to provide stable power to the IoT device   
**Number of IoT Devices:** 4 devices will be deployed across the laundry room (2 for washing machines, 2 for dryers). 

**Real time processing:**  
The sensors would detect when a machine is being used, and send notification to the user via a web application using HTTP to AWS serving as the backend server. 

**Machine Learning Models/ Long-term Analytics:**  
Data collected from the vibration sensors, will be used to train machine learning models to decide the cycle of the laundry machine. It can help predict the duration of machine cycles and idle times, and determine if the machine is available. Furthermore, the idle time and occupied time correlates to the crowd level of the laundry room,  and the models will then utilize the cycles to predict machine availability trends and help optimize laundry room efficiency. For example, by analyzing past usage patterns, the system can forecast busy times and alert students when machines are likely to be available soon. We plan to use models such as **decision trees** or **time-series forecasting models** for this purpose. These models have been used in similar IoT systems for home automation and predictive maintenance, making them well-suited for our laundry monitoring application.	  
**System Architecture:** 

- **Sensors**: Mounted on each machine to detect usage status.  
- **ESP32**: Responsible for gathering sensor data and transmitting it wirelessly.  
- **Cloud Database**: Stores all real-time machine data, accessible to users.  
- **web application**: Using a web application, we can display machine status, send notifications, and allow students to check machine availability remotely.

**Other Cool Features:** 

- **web application Integration:** The app will provide users with push notifications when their laundry is complete or when machines become available.  
- **Predictive Analytics:** By analyzing historical data, the app will notify users of peak times and suggest optimal laundry periods.  
- **3D-Printed Cases:** We will design and 3D-print custom cases for the IoT device

**Progress so far:**  
We have identified the required hardware components (vibration sensors, ESP32 controllers, infrared sensors) and tested the reliability of the hardware. 

**Possible Limitations or Challenges:** 

- **Power Supply Issues:** Battery life may be a concern for long-term use. We are exploring low-power modes and efficient energy-saving mechanisms to extend battery life.  
- **WiFi Stability:** NUS's WiFi network may experience fluctuations, which could disrupt communication between devices and the server. To mitigate this, the ESP32 devices will cache data locally and transmit it when the network is stable.

**Timeline:**   
**Recess Week:** Finalize hardware selection and conduct initial sensor and ESP32 testing.  
**Weeks 7-8:** Develop the basic web application and integrate the backend system to handle real-time data updates. Begin training the machine learning model using data collected from the sensors. Integrate basic predictive features into the app for testing purposes.  
**Weeks 9:  First check in, collect feedback and areas of improvement.**  
**Week 10:** Refine the system based on pilot feedback and finalize the project for submission.  
**Week 11**: **Second check in, collect feedback and work on areas of improvement.**  
**Week 12-13**: Final project refinement and project submission.

**References:**  
**ESP32 Documentation** – "ESP32 Technical Reference Manual," Espressif Systems, 2023\. \[Online\]. Available: [https://www.espressif.com/en/support/download/documents](https://www.espressif.com/en/support/download/documents)  
**Machine Learning for IoT Applications** – H. Yin, "A Survey on Machine Learning for IoT Device Management," *IEEE Internet of Things Journal*, vol. 7, no. 3, pp. 2021-2034, Mar. 2020\.  
**Sensor Technology in Smart Homes** – A. Kumar et al., "Smart Home System for Energy Management Using IoT and Predictive Analytics," *International Journal of Smart Home*, vol. 12, no. 4, pp. 1-10, July 2022\.  
**Wireless Communication in IoT** – S. Patel, "Low Power Wireless Solutions for IoT Applications," *IEEE Communications Magazine*, vol. 58, no. 12, pp. 105-112, Dec. 2020\.