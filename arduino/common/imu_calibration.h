#pragma once

#include <Arduino.h>
#include <math.h>

enum class MachineVariant {
  Dryer,
  Washer,
};

struct AxisCalibration {
  float offset;
  float scale;
};

struct IMUCalibration {
  AxisCalibration accel[3];
  AxisCalibration gyro[3];
};

inline int16_t applyAxisCalibration(int16_t raw, const AxisCalibration &cal) {
  const float adjusted = (static_cast<float>(raw) - cal.offset) * cal.scale;
  return static_cast<int16_t>(roundf(adjusted));
}

inline const IMUCalibration &getIMUCalibration(MachineVariant variant) {
  static const IMUCalibration dryerCalibration = {
      {
          {0.0f, 1.0f},
          {0.0f, 1.0f},
          {0.0f, 1.0f},
      },
      {
          {0.0f, 1.0f},
          {0.0f, 1.0f},
          {0.0f, 1.0f},
      }};

  static const IMUCalibration washerCalibration = {
      {
          {0.0f, 1.0f},
          {0.0f, 1.0f},
          {0.0f, 1.0f},
      },
      {
          {0.0f, 1.0f},
          {0.0f, 1.0f},
          {0.0f, 1.0f},
      }};

  return variant == MachineVariant::Dryer ? dryerCalibration
                                          : washerCalibration;
}


