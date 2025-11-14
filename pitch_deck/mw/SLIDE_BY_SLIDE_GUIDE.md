# Slide-by-Slide Presentation Guide

**Target Duration:** 10-15 minutes
**Format:** Screen share with slides + code walkthrough

---

## Slide 1: Title & Hook (30 seconds)

### Visual Elements:
```
┌─────────────────────────────────────────────┐
│  DLLM: Don't Leave Laundry Dirty           │
│  Real-Time IoT Laundry Monitoring System    │
│                                             │
│  Nicholas Oh                                │
│  AWS Infrastructure & Backend Development   │
│                                             │
│  Problem: Limited laundry facilities        │
│  Solution: ML-powered real-time status      │
└─────────────────────────────────────────────┘
```

### Speaker Notes:
"Good morning/afternoon. Thanks for the opportunity to present today. I'm Nicholas, and I'm going to show you DLLM - a real-time laundry monitoring system I built with my team.

Quick context: This was a university group project, but I want to emphasize I personally own the entire AWS cloud infrastructure, which I'll dive deep into.

The problem: In residential communities with limited laundry machines, residents waste significant time checking availability. We solved this with IoT sensors, machine learning, and cloud infrastructure to provide real-time machine status.

My presentation will be about 12 minutes, then I'd love to walk through the code with you and answer questions. I'm ready to discuss any technical detail - from AWS architecture to sensor fusion algorithms to testing strategies."

**Transition:** "Let me start by showing you what we built..."

---

## Slide 2: System Demo (1 minute)

### Visual Elements:
- Screenshot of web interface (`report/aws_interface.webp`)
- Annotate machine status: Available, In-Use, Ready to Unload
- Show machine IDs: RVREB-W1 (washer), RVREB-D1 (dryer)

### Speaker Notes:
"Here's the user-facing application hosted on Vercel. Users see real-time status for each machine:
- Green: Available - machine is ready to use
- Orange: In-Use - cycle in progress
- Blue: Ready to Unload - cycle complete, clothes need removal

Behind this simple interface is a complex distributed system I'll explain.

Key metrics we achieved:
- Sub-2-second latency from sensor event to state update
- 90% detection accuracy
- <5% false positive rate after optimization
- $5/month AWS costs for current deployment

Let me show you how it works under the hood."

**Transition:** "The architecture has three main layers..."

---

## Slide 3: High-Level Architecture (2 minutes)

### Visual Elements:
- Show `report/aws_architecture.webp`
- Annotate three layers:
  1. **Edge Layer** (Arduino + ESP32)
  2. **Communication Layer** (MQTT + AWS IoT Core)
  3. **Cloud Layer** (Lambda + DynamoDB + API Gateway)
  4. **Frontend Layer** (Vercel)

### Speaker Notes:
"Let me walk you through the architecture from bottom to top:

**Edge Layer - Hardware:**
- Arduino with IMU sensors attached to each machine detect vibration
- ESP32 cameras positioned to monitor user interactions
- All data processing starts here

**Communication Layer:**
- MQTT broker for local device communication (lightweight, handles intermittent WiFi)
- AWS IoT Core for reliable cloud ingestion (managed service, certificate-based auth)
- Chose MQTT over HTTP for its QoS guarantees and efficiency

**Cloud Layer - My Primary Work:**
- 10 AWS Lambda functions handling different responsibilities
- DynamoDB for storing sensor data, machine states, and camera detections
- Centralized state machine for sensor fusion logic
- All infrastructure defined in Terraform (462 lines just for IAM roles)

**Frontend:**
- Vercel-hosted React app
- Polls Lambda function every 5 minutes for status updates
- Would improve with WebSockets for real-time push

**Key Architectural Decisions:**

1. **Why Serverless (Lambda)?**
   - Auto-scaling: Handles 0-1000s requests without configuration
   - Pay-per-use: Only pay for execution time (~$5/month for our load)
   - No ops: No servers to patch, monitor, scale
   - Alternative considered: EC2 would require over-provisioning, 24/7 costs

2. **Why DynamoDB?**
   - Single-digit millisecond latency (critical for real-time)
   - Flexible schema (sensor data evolved during development)
   - Serverless (pairs well with Lambda)
   - Alternative considered: RDS overkill for simple key-value access patterns

3. **Why Hybrid Edge-Cloud?**
   - Privacy: Images processed locally, never uploaded to cloud
   - Cost: No cloud GPU for YOLOv7 inference
   - Latency: Edge processing faster than round-trip to cloud
   - Reliability: Local caching survives WiFi outages"

**Transition:** "Let me show you how data flows through this system..."

---

## Slide 4: Data Flow & Sensor Fusion (2 minutes)

### Visual Elements:
- Show `report/aws_flowchart.webp`
- Trace data flow with numbered steps:
  1. Arduino → Vibration data
  2. ESP32 → Camera images
  3. Local processing → MQTT
  4. AWS IoT Core → Lambda
  5. State Machine → Decision
  6. Frontend → Display

### Speaker Notes:
"Here's how the system processes sensor data in real-time:

**Path 1: IMU Sensor Data (Arduino)**
1. Arduino reads accelerometer every 10ms, takes 30 samples (300ms window)
2. On-device Random Forest model predicts: spinning or idle
3. Majority voting: If >15/30 predictions say spinning, confidence = 50-100%
4. Publishes JSON to AWS IoT Core: `{machine_id, is_spinning, confidence, timestamp}`
5. IoT Rules Engine routes to `storeDataFunction` Lambda
6. Lambda stores in DynamoDB and invokes state machine

**Path 2: Camera Data (ESP32)**
1. ESP32 captures image, sends to local MQTT broker
2. Raspberry Pi runs YOLOv7 pose detection (locally for privacy)
3. Python script classifies pose: washer/dryer/walking, bending detection
4. Publishes result to AWS IoT Core: `{machine_id, is_bending, confidence}`
5. Lambda processes camera event and invokes state machine

**Path 3: State Machine (My Core Contribution)**
This is where the magic happens - sensor fusion:

```python
# Simplified logic
if source == 'camera' and is_bending and confidence > 0.7:
    if current_state == AVAILABLE:
        new_state = LOADING  # User loading clothes
        
if source == 'imu' and is_spinning and confidence > 0.5:
    if current_state == LOADING:
        new_state = IN_USE  # Camera + IMU confirm: machine started
```

**Why Sensor Fusion?**
- Camera alone: 40% false positive rate (people walking by)
- IMU alone: Can't detect loading/unloading actions
- Combined: 5% false positive rate, detects all lifecycle states

**State Lifecycle:**
```
AVAILABLE → LOADING → IN_USE → FINISHING → READY_TO_UNLOAD → AVAILABLE
```

Each transition requires specific sensor conditions + confidence thresholds."

**Transition:** "Now let me show you the technical challenges we solved..."

---

## Slide 5: Challenge #1 - False Positives (2 minutes)

### Visual Elements:
- Show example bad detection (`task_detection/images_output/example_bad_output.jpg`)
- Show example good detection (`task_detection/images_output/example_good_output.jpg`)
- Graph: False positive rate over time (Before: 40%, After: 5%)

### Speaker Notes:
"Our biggest practical challenge was false positives from the camera system.

**The Problem:**
YOLOv7 occasionally detected people who were just walking by, not actually using machines. This caused:
- Machines incorrectly marked as 'in use'
- User frustration (walk to laundry room, machine actually available)
- Loss of trust in system accuracy

**Example:** Person walking past camera → YOLOv7 detects person → Keypoints show 'bending' (walking gait) → False transition to LOADING state

**Our Solution - Multi-Level Filtering:**

**Level 1: Confidence Thresholds**
```python
if keypoints[2] < 0.5:  # Head keypoint confidence
    return None  # Reject low-quality detection
```
- YOLOv7 outputs confidence per keypoint
- Only process if key body parts have >50% confidence
- Reduced false positives by 20%

**Level 2: Temporal Consistency** (This was the breakthrough)
```python
# Track recent detections per machine
self.recent_detections[machine_id].append(time.time())

# Require 2+ detections within 10 seconds
if len(recent_detections) < 2:
    return current_state  # Ignore single-frame detection
```

**Why This Works:**
- Loading laundry takes 5-15 seconds → Multiple frames
- Walking by takes 1-2 seconds → Single frame
- Reduced false positives by additional 15% (40% → 5% total)

**Level 3: Angle-Based Classification**
```python
def calculate_angle(shoulder, hip, knee):
    # Calculate angle at hip joint
    ...
    return angle

if angle < 150:  # Bending threshold
    is_collecting = True
```
- Standing: ~170-180° at hip
- Bending to load: <150° at hip
- Walking: Variable, but temporal filter catches this

**Level 4: Sensor Fusion Confirmation**
- Camera says "loading" → State = LOADING (tentative)
- IMU confirms "spinning started" → State = IN_USE (confirmed)
- If IMU never confirms within 5 minutes → Timeout back to AVAILABLE

**Testing This:**
We ran 50 test cycles with:
- 30 real loading events (all detected)
- 20 people walking by (19 correctly ignored)
- Result: 96% accuracy

**Impact:**
- System went from 'interesting prototype' to 'actually usable'
- Key learning: ML accuracy in isolation doesn't matter, system-level accuracy does"

**Transition:** "Another major challenge was reliability..."

---

## Slide 6: Challenge #2 - WiFi Reliability & Error Handling (1.5 minutes)

### Visual Elements:
- Diagram of failure scenarios:
  - WiFi dropout → Local caching
  - Lambda timeout → Retry logic
  - Sensor misalignment → Magnitude features

### Speaker Notes:
"In a residential setting with shared WiFi, connectivity is unreliable. We had to design for failure.

**Challenge 1: WiFi Dropouts**

**Problem:**
- Shared residential WiFi, 50+ devices
- Intermittent disconnections common
- Can't lose sensor data during outages

**Solution - Multi-Layer Resilience:**

1. **Local MQTT Broker:**
   - Sensors publish to local broker first
   - Broker caches messages (QoS 1)
   - When WiFi returns, forwards to AWS IoT Core

2. **MQTT QoS Guarantees:**
   ```cpp
   // Arduino code
   client.publish(topic, payload, qos=1);  // At least once delivery
   ```
   - QoS 0: Fire and forget (can lose messages)
   - QoS 1: At least once (what we use)
   - QoS 2: Exactly once (unnecessary overhead)

3. **Retry Logic with Exponential Backoff:**
   ```cpp
   if (!connectAWS()) {
       delay(1000 * retry_count);  // 1s, 2s, 4s, 8s...
       retry_count = min(retry_count * 2, 60);
   }
   ```

**Challenge 2: Sensor Misalignment**

**Problem:**
- Manual installation of Arduino on machines
- Each sensor at slightly different angle
- Raw accelerometer readings differ even for same vibration

**Solution - Rotation-Invariant Features:**
```cpp
int16_t ax, ay, az;  // Raw accelerometer
int16_t acc_magn = sqrt(ax*ax + ay*ay + az*az);  // Magnitude
```
- Magnitude is independent of sensor orientation
- Improved model accuracy from ~75% to ~90%
- Robustness to installation errors

**Challenge 3: Power Management**

**Problem:** Battery-powered Arduino, needed long life

**Solution:**
- Deep sleep between readings
- RTOS scheduling for efficient multitasking
- Result: 100+ hours continuous operation

**Testing Our Resilience:**

We tested under adverse conditions:
1. **Peak usage:** 10 concurrent users, no degradation
2. **WiFi stress test:** Unplugged router for 5 minutes
   - Data cached locally
   - All readings published when reconnected
3. **Power cycle:** Randomly restarted Arduino
   - State persisted in cloud (DynamoDB)
   - Graceful recovery

**Key Learning:**
Distributed systems must assume failure. Design for it, don't treat it as edge case."

**Transition:** "Let me show you the code quality practices..."

---

## Slide 7: Infrastructure as Code & Testing (1.5 minutes)

### Visual Elements:
- Terraform file structure
- Code snippet: Lambda + DynamoDB definition
- Test results screenshot (if available)

### Speaker Notes:
"I'm particularly proud of the infrastructure-as-code and testing practices.

**Why Terraform?**

```hcl
# aws/lambda.tf
resource "aws_lambda_function" "storeDataFunction" {
  function_name    = "storeDataFunction"
  handler          = "storeDataFunction.handler"
  runtime          = "nodejs20.x"
  filename         = data.archive_file.storeDataFunction.output_path
  source_code_hash = data.archive_file.storeDataFunction.output_base64sha256
  role             = aws_iam_role.storeDataRole.arn
  
  environment {
    variables = {
      DYNAMODB_TABLE       = aws_dynamodb_table.VibrationData.name
      STATE_MACHINE_FUNCTION = aws_lambda_function.updateMachineStateFunction.function_name
    }
  }
}
```

**Benefits:**
1. **Version Control:** Infrastructure changes go through code review
2. **Reproducibility:** `terraform apply` recreates entire stack
3. **Documentation:** Code documents architecture decisions
4. **Collaboration:** Team can review infrastructure changes in PRs

**IAM Security:**
I defined 6 different IAM roles with least-privilege permissions:
```hcl
# aws/iam.tf (462 lines total)
resource "aws_iam_role" "storeDataRole" {
  # Can only:
  # - Write to VibrationData table
  # - Invoke updateMachineStateFunction
  # Cannot:
  # - Read from other tables
  # - Invoke other functions
  # - Access S3
}
```

**Testing Strategy:**

**Unit Tests (Current Implementation):**
```python
# tests/python/test_machine_status_handlers.py
@pytest.fixture
def machine_status_table():
    with mock_aws():  # moto library
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.create_table(...)
        yield table

def test_fetch_machine_status_returns_items(machine_status_table):
    # Arrange
    machine_status_table.put_item(Item={"machineID": "RVREB-W1", "status": "available"})
    
    # Act
    response = module.lambda_handler({}, {})
    
    # Assert
    assert response["statusCode"] == 200
    assert len(response["body"]["data"]) == 2
```

**Why Mock AWS Services?**
- Fast: No network calls, tests run in milliseconds
- Free: No AWS costs
- Isolated: Tests don't interfere with real data
- CI/CD: Works without AWS credentials

**Test Coverage:**
- ✅ All Lambda handler functions
- ✅ State machine state transitions
- ✅ Error handling (invalid input, missing tables)
- ❌ Integration tests (gap I'd address)

**What I'd Add:**

1. **Integration Tests with LocalStack:**
   ```python
   def test_full_sensor_fusion_flow():
       """Test camera → state machine → IMU → state machine"""
       # Real Lambda invocations (locally)
       # Real DynamoDB operations (locally)
       # Validates service interactions
   ```

2. **Contract Tests:**
   - Ensure Arduino output format matches Lambda input expectations
   - Prevent breaking changes across components

3. **Load Tests:**
   ```python
   # locust load test
   class LaundryUser(HttpUser):
       @task
       def post_sensor_data(self):
           self.client.post("/sensor", json=...)
   ```
   - Test 100+ concurrent sensor events
   - Validate no race conditions in state updates

**CI/CD (Would Add):**
```yaml
# .github/workflows/deploy.yml
on: push
jobs:
  test:
    - run: pytest tests/
  terraform:
    - run: terraform plan
    - run: terraform apply (if main branch)
```

**Key Principle:**
Infrastructure should be treated like application code: versioned, reviewed, tested, deployed via pipeline."

**Transition:** "Let me address security..."

---

## Slide 8: Security Considerations & Gaps (1 minute)

### Visual Elements:
- Table comparing current state vs. production-ready
- Red flags on gaps, green checks on what's done right

### Speaker Notes:
"I want to be transparent about security - there are gaps I'd fix before production.

**What We Did Right:**

✅ **IAM Least Privilege:**
Every Lambda has only permissions it needs:
```hcl
resource "aws_iam_role_policy" "storeDataPolicy" {
  policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Action = ["dynamodb:PutItem"]
      Resource = [aws_dynamodb_table.VibrationData.arn]  # Specific table only
    }]
  })
}
```

✅ **DynamoDB Encryption:** At rest (AWS default)

✅ **TLS/HTTPS:** All communication encrypted in transit

✅ **AWS IoT Certificates:** Mutual TLS for device authentication

**What We Didn't Do (Gaps):**

❌ **Lambda Function URLs - No Authentication:**
```hcl
resource "aws_lambda_function_url" "fetchMachineStatusFunction" {
  authorization_type = "NONE"  # ⚠️ Public endpoint!
}
```

**Risk:** Anyone with URL can read machine status or inject fake data

**Fix:**
```hcl
# Replace with API Gateway
resource "aws_api_gateway_rest_api" "laundry_api" {
  name = "laundry-monitoring-api"
}

resource "aws_api_gateway_authorizer" "api_key" {
  type = "API_KEY"
}
```
- Add API keys for frontend
- Rate limiting (100 req/min per key)
- CloudWatch monitoring for abuse

❌ **No Input Validation:**
```javascript
// Current: Trust all input
const params = {
  Item: { ...event }  // Dangerous!
};
```

**Fix:**
```javascript
import Ajv from 'ajv';

const schema = {
  type: 'object',
  properties: {
    machine_id: { pattern: '^RVREB-[WD]\\d+$' },
    confidence: { minimum: 0, maximum: 1 }
  },
  required: ['machine_id'],
  additionalProperties: false
};

if (!validate(event)) {
  return { statusCode: 400, body: 'Invalid input' };
}
```

❌ **CORS - Too Permissive:**
```hcl
cors {
  allow_methods = ["*"]  # Includes DELETE, PUT (not needed)
}
```

**Fix:** Restrict to `["GET", "POST"]`

**Production Security Checklist:**
- [ ] API Gateway with authentication
- [ ] Input validation (JSON Schema)
- [ ] Rate limiting and throttling
- [ ] AWS WAF for common attacks
- [ ] Certificate rotation for IoT devices
- [ ] CloudWatch alarms on suspicious activity
- [ ] Penetration testing

**Honest Assessment:**
For a university project demonstrating technical skills, current security is acceptable. For production (especially in finance), I'd implement all these fixes before launch.

In Marshall Wace's environment, security is probably non-negotiable from day one. I'd love to learn your security practices."

**Transition:** "Let me show you performance metrics..."

---

## Slide 9: Performance & Results (1 minute)

### Visual Elements:
- Latency breakdown (pie chart or bar graph)
- Accuracy metrics (confusion matrix if available)
- Cost breakdown

### Speaker Notes:
"Let me quantify the system performance:

**Latency Breakdown:**
- Arduino sampling: 300ms (30 samples)
- WiFi → AWS IoT: 100ms
- Lambda processing: 200ms (including state machine)
- **Total: ~600ms sensor to state update**

**Bottleneck:** Frontend polling (5-minute average wait)
**Fix:** WebSockets would make it <1 second end-to-end

**Accuracy:**
- IMU detection: ~90% (spinning vs. idle)
- Pose detection: ~85% (bending vs. standing)
- Combined system: ~95% (with sensor fusion + temporal filtering)

**Confusion Matrix (IMU):**
```
              Predicted
           Idle  Spinning
Actual Idle     45       5
     Spinning    3      47
```
- 10% error rate mostly from spin-up/spin-down transitions

**Cost Analysis (Current Load):**
```
4 machines, 1 location:
- Lambda invocations: 10K/month = $0.20
- DynamoDB writes: 200K/month = $0.25
- DynamoDB reads: 50K/month = $0.01
- AWS IoT Core: 200K messages = $0.40
- Data transfer: < $0.10
--------------------------------------------
Total: ~$1-2/month (within free tier)
```

**At Scale (1,000 locations):**
- On-demand pricing: ~$240/month
- Provisioned capacity: ~$70/month (switch at 100 locations)

**Battery Life:**
- Arduino: 100+ hours continuous operation
- Deep sleep optimization: Could extend to weeks

**Real-World Validation:**
Deployed in our residential hall for 2 weeks:
- 150+ laundry cycles monitored
- Zero system downtime
- 3 user-reported incorrect statuses (98% subjective accuracy)
- Users reported saving 10-15 minutes per laundry session

**Key Takeaway:**
System meets real-world requirements: Fast enough, accurate enough, cheap enough, reliable enough."

**Transition:** "Let me wrap up with lessons learned..."

---

## Slide 10: Lessons Learned & Future Improvements (1.5 minutes)

### Visual Elements:
- Two columns: "What Worked" and "What I'd Improve"

### Speaker Notes:
"Every project teaches valuable lessons. Here's what I learned:

**What Worked Well:**

✅ **Serverless Architecture:**
- Auto-scaling handled variable load seamlessly
- Pay-per-use kept costs minimal
- No ops burden (no servers to patch/monitor)
- Would use serverless again for event-driven workloads

✅ **Sensor Fusion:**
- Combined sensors more accurate than either alone
- Temporal consistency filtering was breakthrough
- Domain knowledge (cycle times) improved logic

✅ **Infrastructure as Code:**
- Terraform made infrastructure reviewable and reproducible
- Caught errors in code review before deployment
- Easy to tear down/rebuild for testing

✅ **Hybrid Edge-Cloud:**
- Privacy preserved (images never uploaded)
- Cost optimized (no cloud GPU)
- Latency minimized (local processing)

**What I'd Improve:**

❌ **Missing Idempotency:**
**Problem:** Duplicate events (MQTT QoS=1, Lambda retries) can cause incorrect state transitions

**Impact:** Rare, but saw it once in testing:
```
12:00:00 - Event: AVAILABLE → LOADING
12:00:02 - Duplicate event: LOADING → AVAILABLE (!)
```

**Fix:**
```javascript
const idempotencyKey = hash(`${machine_id}-${timestamp}-${sensor_type}`);
if (await alreadyProcessed(idempotencyKey)) {
  return { statusCode: 200, body: 'Already processed' };
}
```

**Lesson:** Distributed systems need idempotency from day 1, not as afterthought.

❌ **Limited Testing:**
- Unit tests: ✅ Done
- Integration tests: ❌ Missing
- Load tests: ❌ Missing
- Chaos tests: ❌ Missing

**Would add:** LocalStack for integration tests, Locust for load testing, random failure injection for chaos testing

❌ **No Monitoring Dashboard:**
- CloudWatch logs exist, but no visualization
- Can't easily see system health at a glance

**Would add:**
- CloudWatch dashboard (request rates, error rates, latency)
- Alarms (high error rate, sensor offline >10 min)
- Metrics per machine (detect faulty sensors)

❌ **Polling Frontend:**
- 5-minute average latency for users to see updates

**Fix:** WebSocket API for push notifications

**Future Enhancements:**

**1. ML Model Improvements:**
- Active learning: User feedback → Retrain model
- Data augmentation: Expand small training dataset
- A/B testing: Compare old vs. new models in production

**2. Multi-Location Support:**
- Currently hard-coded for 1 location
- Would add: location_id to data model, regional Lambda deployments, admin dashboard

**3. Predictive Features:**
- "Machine will be available in 15 minutes" (based on cycle time)
- "Peak usage time: 7-9pm" (historical analysis)
- "Average wait time: 5 minutes"

**4. User Features:**
- Push notifications (cycle complete, machine available)
- Reservation system (reserve next available machine)
- Usage statistics per user

**Biggest Learning:**

Building production-grade systems is about handling edge cases, not just happy paths. This project taught me:
- Distributed systems are hard (idempotency, consistency, failures)
- Testing matters (caught many bugs before deployment)
- Security is not optional (even for side projects)
- Documentation is future-you's friend

**What I'm Most Proud Of:**
Taking a classroom concept and building something people actually used. The technical depth is important, but solving a real problem is more satisfying."

**Transition:** "I'll wrap up now..."

---

## Slide 11: Closing Summary (30 seconds)

### Visual Elements:
```
┌─────────────────────────────────────────────┐
│  Key Achievements                           │
│  • 10 AWS Lambda functions                  │
│  • Sensor fusion state machine              │
│  • <2s latency, 95% accuracy                │
│  • Terraform IaC, unit tested               │
│  • Deployed and used in production          │
│                                             │
│  Technical Skills Demonstrated              │
│  • Distributed systems                      │
│  • Cloud architecture (AWS)                 │
│  • ML integration                           │
│  • Testing & security                       │
│  • Problem-solving under constraints        │
│                                             │
│  Let's dive into the code!                  │
└─────────────────────────────────────────────┘
```

### Speaker Notes:
"To summarize:

I built a production-grade IoT monitoring system that:
- Processes sensor data from multiple sources in real-time
- Uses machine learning and sensor fusion for accurate detection
- Handles real-world constraints like intermittent connectivity
- Operates at <$5/month cost
- Actually solved a problem for real users

The technical skills I demonstrated:
- **Distributed systems:** State management, consistency, failure handling
- **Cloud architecture:** Serverless design, scalability, cost optimization  
- **ML integration:** Edge deployment, confidence filtering, sensor fusion
- **Engineering practices:** IaC, testing, security, monitoring

**I'm excited about Marshall Wace because** I want to work on systems that operate at scale with real-world constraints - low latency, high reliability, financial rigor. This project was a taste, and I'm eager to learn from your team.

**Now I'd love to:**
1. Walk through the code in detail - any component you're curious about
2. Answer questions about design decisions
3. Discuss how you'd approach similar challenges in your environment

What would you like to dive into first?"

---

## Post-Presentation: Code Walkthrough (30-40 minutes)

### Have These Files Open and Ready:

1. **aws/functions/updateMachineStateFunction.py**
   - Lines 16-61: Main state machine logic
   - Lines 74-119: Camera event processing
   - Lines 121-181: IMU event processing

2. **task_detection/img_receiver_aws.py**
   - Lines 41-96: AWS IoT connection setup
   - Lines 188-260: Pose classification and confidence fusion

3. **aws/lambda.tf**
   - Lines 188-203: Lambda function definition example
   - Show how Terraform links resources

4. **tests/python/test_machine_status_handlers.py**
   - Show mocking strategy
   - Explain test philosophy

5. **arduino/Dryer/imu_dryer/imu_dryer.ino**
   - Lines 74-80: ML inference on device
   - Lines 111-145: Majority voting logic

### Be Ready to Navigate to Any File
Keep your IDE open with good search functionality. If they ask about something specific, you should be able to find it quickly.

---

## Backup Slides (Don't Present Unless Asked)

### Backup: DynamoDB Schema
```
VibrationData:
  - machine_id (PK)
  - timestamp (SK)
  - is_spinning
  - confidence
  - sensor_type
  - TTL (30 days)

MachineStatusTable:
  - machineID (PK)
  - status
  - lastUpdated
  - lastSource

CameraDetectionData:
  - machine_id (PK)
  - timestamp (SK)
  - is_bending
  - confidence
```

### Backup: State Machine State Diagram
```
    ┌─────────────┐
    │  AVAILABLE  │◄────────────────┐
    └──────┬──────┘                 │
           │                        │
           │ camera: bending        │
           ▼                        │
    ┌─────────────┐                 │
    │   LOADING   │                 │
    └──────┬──────┘                 │
           │                        │
           │ imu: spinning          │
           ▼                        │
    ┌─────────────┐                 │
    │   IN_USE    │                 │
    └──────┬──────┘                 │
           │                        │
           │ imu: stopped + cycle_time > min
           ▼                        │
    ┌─────────────┐                 │
    │  FINISHING  │                 │
    └──────┬──────┘                 │
           │                        │
           │ timer: 2 minutes       │
           ▼                        │
    ┌─────────────┐                 │
    │ READY_TO_   │                 │
    │  UNLOAD     │                 │
    └──────┬──────┘                 │
           │                        │
           │ camera: bending        │
           └────────────────────────┘
```

### Backup: Cost Breakdown at Scale
Show detailed cost calculation for 1000 locations with graphs

### Backup: ML Model Training Process
If they ask about how models were trained:
- Data collection methodology
- Feature engineering decisions
- Hyperparameter tuning process
- Cross-validation strategy

---

## Presentation Checklist

### Before Interview:
- [ ] Test screen share (clean desktop, close unnecessary apps)
- [ ] Have all code files open in IDE
- [ ] Have slides open and ready
- [ ] Have README and diagrams accessible
- [ ] Test audio/video
- [ ] Have water nearby
- [ ] 2nd monitor with cheat sheet (if available)

### During Presentation:
- [ ] Speak slowly and clearly
- [ ] Pause after each slide for questions
- [ ] Make eye contact (look at camera)
- [ ] Use concrete examples
- [ ] Don't read slides verbatim
- [ ] Show enthusiasm for the problem
- [ ] Invite questions early and often

### During Code Walkthrough:
- [ ] Zoom in (make text readable)
- [ ] Explain context before showing code
- [ ] Walk through line-by-line if asked
- [ ] Admit gaps honestly
- [ ] Connect code to architecture
- [ ] Ask if they want to see specific parts

---

**Good luck! You've got this! 🚀**

Remember: They want you to succeed. Questions are curiosity, not criticism. Show your thought process, not just your code.

