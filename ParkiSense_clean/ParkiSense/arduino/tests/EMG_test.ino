const int emgPin = A0;

// ---------- Sampling and printing ----------
const int samplesPerWindow = 25;              // Window for RMS
const unsigned long printInterval = 250;      // Serial Monitor update interval (ms)

// ---------- Initial calibration ----------
const int calibrationSamples = 500;           // Initial resting samples
const int sampleDelayMs = 1;                  // Delay between samples

// ---------- Adaptive threshold parameters ----------
const float highMultiplier = 3.5;             // High threshold = noiseFloor * highMultiplier
const float lowMultiplier  = 2.2;             // Low threshold  = noiseFloor * lowMultiplier

const float minThresholdHigh = 18.0;          // Safety minimums
const float minThresholdLow  = 10.0;

// ---------- Baseline adaptation ----------
const float baselineAlpha = 0.02;             // Slow baseline adaptation in rest
const float noiseAlpha    = 0.02;             // Slow noise floor adaptation in rest
const float restUpdateFactor = 1.2;           // Update baseline only if rms < thresholdLow * factor

// ---------- State variables ----------
float baseline = 0.0;
float noiseFloor = 0.0;
float thresholdHigh = 0.0;
float thresholdLow = 0.0;

bool contractionState = false;
unsigned long lastPrintTime = 0;

// -----------------------------------------------------------------------------
// Helper: max for float
float maxFloat(float a, float b) {
  return (a > b) ? a : b;
}

// -----------------------------------------------------------------------------
// Initial calibration at rest
void calibrateEMG() {
  long sum = 0;
  long sumSq = 0;

  for (int i = 0; i < calibrationSamples; i++) {
    int raw = analogRead(emgPin);
    sum += raw;
    sumSq += (long)raw * raw;
    delay(sampleDelayMs);
  }

  float mean = (float)sum / calibrationSamples;
  float meanSq = (float)sumSq / calibrationSamples;
  float variance = meanSq - (mean * mean);

  if (variance < 0) variance = 0;

  baseline = mean;
  noiseFloor = sqrt(variance);

  // Adaptive thresholds with minimum safety values
  thresholdHigh = maxFloat(noiseFloor * highMultiplier, minThresholdHigh);
  thresholdLow  = maxFloat(noiseFloor * lowMultiplier,  minThresholdLow);
}

// -----------------------------------------------------------------------------
// Read one RMS window
void readEMGWindow(float &rawAvg, float &emgRms) {
  long rawSum = 0;
  float sqDiffSum = 0.0;

  for (int i = 0; i < samplesPerWindow; i++) {
    int raw = analogRead(emgPin);
    rawSum += raw;

    float diff = raw - baseline;
    sqDiffSum += diff * diff;

    delay(sampleDelayMs);
  }

  rawAvg = (float)rawSum / samplesPerWindow;
  emgRms = sqrt(sqDiffSum / samplesPerWindow);
}

// -----------------------------------------------------------------------------
// Update baseline and noise floor slowly when the muscle seems to be at rest
void updateAdaptiveReference(float rawAvg, float emgRms) {
  // Only adapt if the signal looks like rest
  if (!contractionState && emgRms < (thresholdLow * restUpdateFactor)) {
    baseline = (1.0 - baselineAlpha) * baseline + baselineAlpha * rawAvg;
    noiseFloor = (1.0 - noiseAlpha) * noiseFloor + noiseAlpha * emgRms;

    thresholdHigh = maxFloat(noiseFloor * highMultiplier, minThresholdHigh);
    thresholdLow  = maxFloat(noiseFloor * lowMultiplier,  minThresholdLow);
  }
}

// -----------------------------------------------------------------------------
// Update contraction state with hysteresis
void updateState(float emgRms) {
  if (!contractionState && emgRms > thresholdHigh) {
    contractionState = true;
  } 
  else if (contractionState && emgRms < thresholdLow) {
    contractionState = false;
  }
}

// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(9600);
  delay(1000);

  Serial.println("EMG final base - starting calibration");
  Serial.println("Keep the muscle relaxed...");

  calibrateEMG();

  Serial.println("Calibration completed");
  Serial.print("Initial baseline: ");
  Serial.println(baseline, 2);
  Serial.print("Initial noiseFloor: ");
  Serial.println(noiseFloor, 2);
  Serial.print("Initial thresholdHigh: ");
  Serial.println(thresholdHigh, 2);
  Serial.print("Initial thresholdLow: ");
  Serial.println(thresholdLow, 2);

  Serial.println("time_ms,raw_avg,emg_rms,baseline,noise_floor,threshold_high,threshold_low,state");
}

// -----------------------------------------------------------------------------
void loop() {
  float rawAvg = 0.0;
  float emgRms = 0.0;

  readEMGWindow(rawAvg, emgRms);
  updateState(emgRms);
  updateAdaptiveReference(rawAvg, emgRms);

  unsigned long currentTime = millis();

  if (currentTime - lastPrintTime >= printInterval) {
    lastPrintTime = currentTime;

    Serial.print(currentTime);
    Serial.print(",");
    Serial.print(rawAvg, 2);
    Serial.print(",");
    Serial.print(emgRms, 2);
    Serial.print(",");
    Serial.print(baseline, 2);
    Serial.print(",");
    Serial.print(noiseFloor, 2);
    Serial.print(",");
    Serial.print(thresholdHigh, 2);
    Serial.print(",");
    Serial.print(thresholdLow, 2);
    Serial.print(",");
    Serial.println(contractionState ? "CONTRACTION" : "REST");
  }
}
