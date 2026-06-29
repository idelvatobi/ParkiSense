const int emgPin = A0;

// ============================================================
// EMG CONFIG
// ============================================================
const int emgSamplesPerWindow = 25;
const int emgCalibrationSamples = 500;
const int emgSampleDelayMs = 1;

const float emgHighMultiplier = 3.5;
const float emgLowMultiplier  = 2.2;

const float emgMinThresholdHigh = 18.0;
const float emgMinThresholdLow  = 10.0;

const float emgBaselineAlpha = 0.02;
const float emgNoiseAlpha    = 0.02;
const float emgRestUpdateFactor = 1.2;

// EMG state
float emgBaseline = 0.0;
float emgNoiseFloor = 0.0;
float emgThresholdHigh = 0.0;
float emgThresholdLow = 0.0;

float emgRawAvg = 0.0;
float emgRms = 0.0;
bool emgContractionState = false;

// ============================================================
// HR CONFIG
// ============================================================
#include <Wire.h>

const int MIN_VALID_BPM = 40;
const int MAX_VALID_BPM = 180;
const int FILTER_SIZE   = 5;

int hrBuffer[FILTER_SIZE];
int hrBufferIndex = 0;
int hrValidCount  = 0;

int hrRawBPM = -1;
float hrFilteredBPM = 0.0;
bool hrValid = false;

// ============================================================
// TIMING
// ============================================================
unsigned long lastHRReadTime = 0;
unsigned long lastPrintTime = 0;

const unsigned long hrReadInterval = 500;
const unsigned long printInterval = 500;

// ============================================================
// HELPERS
// ============================================================
float maxFloat(float a, float b) {
  return (a > b) ? a : b;
}

// ============================================================
// EMG FUNCTIONS
// ============================================================
void calibrateEMG() {
  long sum = 0;
  long sumSq = 0;

  for (int i = 0; i < emgCalibrationSamples; i++) {
    int raw = analogRead(emgPin);
    sum += raw;
    sumSq += (long)raw * raw;
    delay(emgSampleDelayMs);
  }

  float mean = (float)sum / emgCalibrationSamples;
  float meanSq = (float)sumSq / emgCalibrationSamples;
  float variance = meanSq - (mean * mean);

  if (variance < 0) variance = 0;

  emgBaseline = mean;
  emgNoiseFloor = sqrt(variance);

  emgThresholdHigh = maxFloat(emgNoiseFloor * emgHighMultiplier, emgMinThresholdHigh);
  emgThresholdLow  = maxFloat(emgNoiseFloor * emgLowMultiplier, emgMinThresholdLow);
}

void readEMGWindow(float &rawAvg, float &rmsValue) {
  long rawSum = 0;
  float sqDiffSum = 0.0;

  for (int i = 0; i < emgSamplesPerWindow; i++) {
    int raw = analogRead(emgPin);
    rawSum += raw;

    float diff = raw - emgBaseline;
    sqDiffSum += diff * diff;

    delay(emgSampleDelayMs);
  }

  rawAvg = (float)rawSum / emgSamplesPerWindow;
  rmsValue = sqrt(sqDiffSum / emgSamplesPerWindow);
}

void updateEMGState(float rmsValue) {
  if (!emgContractionState && rmsValue > emgThresholdHigh) {
    emgContractionState = true;
  } 
  else if (emgContractionState && rmsValue < emgThresholdLow) {
    emgContractionState = false;
  }
}

void updateEMGAdaptiveReference(float rawAvg, float rmsValue) {
  if (!emgContractionState && rmsValue < (emgThresholdLow * emgRestUpdateFactor)) {
    emgBaseline = (1.0 - emgBaselineAlpha) * emgBaseline + emgBaselineAlpha * rawAvg;
    emgNoiseFloor = (1.0 - emgNoiseAlpha) * emgNoiseFloor + emgNoiseAlpha * rmsValue;

    emgThresholdHigh = maxFloat(emgNoiseFloor * emgHighMultiplier, emgMinThresholdHigh);
    emgThresholdLow  = maxFloat(emgNoiseFloor * emgLowMultiplier, emgMinThresholdLow);
  }
}

void updateEMG() {
  readEMGWindow(emgRawAvg, emgRms);
  updateEMGState(emgRms);
  updateEMGAdaptiveReference(emgRawAvg, emgRms);
}

// ============================================================
// HR FUNCTIONS
// ============================================================
void updateHRFilter(int bpm) {
  hrBuffer[hrBufferIndex] = bpm;
  hrBufferIndex = (hrBufferIndex + 1) % FILTER_SIZE;

  if (hrValidCount < FILTER_SIZE) hrValidCount++;
}

float computeHRFiltered() {
  if (hrValidCount == 0) return 0.0;

  long sum = 0;
  for (int i = 0; i < hrValidCount; i++) {
    sum += hrBuffer[i];
  }

  return (float)sum / hrValidCount;
}

void updateHR() {
  Wire.requestFrom(0x50, 1);

  if (Wire.available()) {
    unsigned char bpm = Wire.read();
    hrRawBPM = (int)bpm;

    hrValid = (hrRawBPM >= MIN_VALID_BPM && hrRawBPM <= MAX_VALID_BPM);

    if (hrValid) {
      updateHRFilter(hrRawBPM);
      hrFilteredBPM = computeHRFiltered();
    }
  }
}

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  while (!Serial);

  Wire.begin();

  for (int i = 0; i < FILTER_SIZE; i++) {
    hrBuffer[i] = 0;
  }

  Serial.println("Initializing integrated EMG + HR system...");
  Serial.println("Keep muscle relaxed and place finger on HR sensor.");
  Serial.println("time_ms,emg_raw_avg,emg_rms,emg_baseline,emg_noise_floor,emg_threshold_high,emg_threshold_low,emg_state,hr_raw_bpm,hr_filtered_bpm,hr_valid,hr_state");

  calibrateEMG();
}

// ============================================================
// LOOP
// ============================================================
void loop() {
  unsigned long currentTime = millis();

  // EMG updates continuously
  updateEMG();

  // HR updates at a slower interval
  if (currentTime - lastHRReadTime >= hrReadInterval) {
    lastHRReadTime = currentTime;
    updateHR();
  }

  // Unified serial output
  if (currentTime - lastPrintTime >= printInterval) {
    lastPrintTime = currentTime;

    Serial.print(currentTime);
    Serial.print(",");

    Serial.print(emgRawAvg, 2);
    Serial.print(",");
    Serial.print(emgRms, 2);
    Serial.print(",");
    Serial.print(emgBaseline, 2);
    Serial.print(",");
    Serial.print(emgNoiseFloor, 2);
    Serial.print(",");
    Serial.print(emgThresholdHigh, 2);
    Serial.print(",");
    Serial.print(emgThresholdLow, 2);
    Serial.print(",");
    Serial.print(emgContractionState ? "CONTRACTION" : "REST");
    Serial.print(",");

    Serial.print(hrRawBPM);
    Serial.print(",");

    if (hrValidCount > 0) {
      Serial.print(hrFilteredBPM, 1);
    } else {
      Serial.print("---");
    }

    Serial.print(",");
    Serial.print(hrValid ? 1 : 0);
    Serial.print(",");
    Serial.println(hrValid ? "VALID" : "NO_VALID_READING");
  }
}
