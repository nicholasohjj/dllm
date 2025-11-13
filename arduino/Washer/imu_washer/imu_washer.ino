//GND - GND
//VCC - VCC
//SDA - Pin 21
//SCL - Pin 22
#include <i2c.h>
#include <washer_clf.h>
#include <vibration.h>
#include <aws_pub.h>
#include <mqtt.h>
#include <sleep.h>
#include "../common/imu_calibration.h"

Eloquent::ML::Port::RandomForest classifier;

const IMUCalibration &imuCalibration =
    getIMUCalibration(MachineVariant::Washer);

int pred = 0;
int preds[30] = {};
// print acceleration readings and print
void print_acc(int16_t ax, int16_t ay, int16_t az) {
  // Acelerometro
  Serial.println("Acceleration: ");
  Serial.print("x axis: ");
  Serial.print(ax, DEC);
  Serial.print("| y axis: ");
  Serial.print(ay, DEC);
  Serial.print("| z axis: ");
  Serial.print(az, DEC);
  Serial.println("");
  String msg = String(ax) + "," + String(ay) + "," + String(az); 
}

// print gyroscope readings and print
void print_gyro(int16_t gx, int16_t gy, int16_t gz) {
  // Giroscopio
  Serial.println("Gyroscope: ");
  Serial.print("x axis: ");
  Serial.print(gx, DEC);
  Serial.print("| y axis: ");
  Serial.print(gy, DEC);
  Serial.print("| z axis: ");
  Serial.print(gz, DEC);
  Serial.println("");
  String msg = String(gx) + "," + String(gy) + "," + String(gz); 
}

void i2c_conf() {
  Serial.println("Setup I2C communication for imu sensor.");
  // Configurar acelerometro
  I2CwriteByte(MPU9250_ADDRESS, 28, ACC_FULL_SCALE_2_G);
  // Configurar giroscopio
  I2CwriteByte(MPU9250_ADDRESS, 27, GYRO_FULL_SCALE_2000_DPS);
  // Configurar magnetometro
  I2CwriteByte(MPU9250_ADDRESS, 0x37, 0x02);
  I2CwriteByte(MAG_ADDRESS, 0x0A, 0x01);

}

void setup() {
  Wire.begin();
  Serial.begin(115200);
  pinMode(vibr_Pin, INPUT); //set vibr_Pin input for vibration measurment
  network_conf(); // for sending data
  i2c_conf(); // set i2c communication for imu sensor
  // configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  // connectAWS();
  setup_mqtt();

  read_imu_publish();

  sleep();
}

void pred_washer_status(int16_t ax, int16_t ay, int16_t az) {
  int16_t acc_magn = sqrt(ax*ax + ay*ay + az*az);
  float X[] = {ax, ay, az, acc_magn};
  pred = classifier.predict(X);
  Serial.print("Result of predict with input X:");
  Serial.println(pred);
  delay(2000);
}

void get_acc_gyro_readings() {
  Serial.println("Getting imu sensor readings.");
  // ---  Lectura acelerometro y giroscopio ---
  uint8_t Buf[14];
  I2Cread(MPU9250_ADDRESS, 0x3B, 14, Buf);

  // Convertir registros acelerometro
  int16_t ax_raw = -(Buf[0] << 8 | Buf[1]);
  int16_t ay_raw = -(Buf[2] << 8 | Buf[3]);
  int16_t az_raw = Buf[4] << 8 | Buf[5];

  int16_t ax = applyAxisCalibration(ax_raw, imuCalibration.accel[0]);
  int16_t ay = applyAxisCalibration(ay_raw, imuCalibration.accel[1]);
  int16_t az = applyAxisCalibration(az_raw, imuCalibration.accel[2]);

  // Convertir registros giroscopio
  int16_t gx_raw = -(Buf[8] << 8 | Buf[9]);
  int16_t gy_raw = -(Buf[10] << 8 | Buf[11]);
  int16_t gz_raw = Buf[12] << 8 | Buf[13];

  int16_t gx = applyAxisCalibration(gx_raw, imuCalibration.gyro[0]);
  int16_t gy = applyAxisCalibration(gy_raw, imuCalibration.gyro[1]);
  int16_t gz = applyAxisCalibration(gz_raw, imuCalibration.gyro[2]);

  print_acc(ax, ay, az);
  pred_washer_status(ax, ay, az);
  print_gyro(gx, gy, gz);
}

void read_imu_publish() {
  int16_t total_magnitude = 0;
  
  for (int i = 0; i < 30; i += 1) {
    Serial.println(i);
    get_acc_gyro_readings();
    preds[i] = pred; 
    
    // Calculate vibration magnitude for confidence scoring
    // Note: ax, ay, az should be accessible - if not, calculate during get_acc_gyro_readings
    delay(10);
    
    get_vib_readings();
    delay(10);
  }
  Serial.println("Finish getting sensor reading.");

  Serial.print("Predicted result: ");
  int true_cnt = 0;
  for (int i = 0; i < 30; i += 1) {
    true_cnt += preds[i];
    Serial.print(preds[i]);
    Serial.print(" ");
  }
  Serial.println("");

  int pred_res = 0;
  float confidence = 0.0;
  
  if (true_cnt > 15) {
    Serial.println("Predicted as spinning.");
    pred_res = 1;
  } else {
    Serial.println("Predicted as not spinning.");
    pred_res = 0;
  }
  
  // Calculate confidence as percentage of positive predictions
  confidence = (float)true_cnt / 30.0;
  
  setup_wifi();
  
  String msg = "{\"machine_id\":\"RVREB-W1\",";
  msg += "\"device_type\":\"washer\",";
  msg += "\"is_spinning\":";
  msg += String(pred_res);
  msg += ",\"confidence\":";
  msg += String(confidence, 2);
  msg += ",\"timestamp\":";
  msg += String(millis());
  msg += ",\"sensor_type\":\"imu\"}";
  
  Serial.println("Publishing: " + msg);
  mqttClient.publish(publishTopic, msg, 0, false);

  delay(3000);
}

void loop() {}
