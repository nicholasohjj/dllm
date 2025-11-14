# Interview Cheat Sheet - Quick Reference

**Print this or keep on second monitor during interview**

---

## 🎯 Your 30-Second Elevator Pitch

"I built the AWS cloud infrastructure for DLLM, an IoT laundry monitoring system. I designed a serverless architecture with 10 Lambda functions, DynamoDB for storage, and a centralized state machine that fuses IMU sensor data with camera vision data. I used Terraform for infrastructure-as-code, implemented unit tests with mocked AWS services, and solved real-world challenges like sensor false positives through temporal consistency filtering. The system handles intermittent WiFi, processes sensor data in under 2 seconds, and costs under $5/month to operate."

---

## 📊 Key Numbers to Remember

| Metric | Value | Context |
|--------|-------|---------|
| **Accuracy** | ~90% | ML model detection rate |
| **Latency** | <2 seconds | Sensor event to state update |
| **Battery Life** | 100+ hours | Arduino continuous operation |
| **Cost** | $5/month | AWS infrastructure |
| **Lambda Functions** | 10 | Different responsibilities |
| **ML Model Size** | 8KB | Random Forest on Arduino |
| **Sampling Window** | 30 samples | 300ms for stability |
| **False Positive Reduction** | 40% → 5% | With temporal filtering |
| **Test Coverage** | Unit tests | Integration tests needed |

---

## 🏗️ Architecture Components (Your Ownership)

### You Built:
- ✅ **All AWS Infrastructure** (Terraform, 462 lines IAM alone)
- ✅ **10 Lambda Functions** (Node.js & Python)
- ✅ **State Machine** (Sensor fusion logic)
- ✅ **DynamoDB Design** (3 tables)
- ✅ **Testing** (Unit tests with moto)
- ✅ **IAM Roles** (Least privilege security)

### Teammates Built:
- Arduino IMU collection (Chao Yi-Ju)
- ESP32 camera + WiFi (Cheah Hao Yi)
- YOLOv7 integration (James Wong)
- Pose classification (Cheah Hao Yi, James Wong)

### You Integrated Everything:
- Connected Arduino → AWS IoT Core
- Connected ESP32 → MQTT → AWS
- State machine coordinates both sensors

---

## 🔑 Key Technical Decisions (Defend These)

| Choice | Why | Alternative |
|--------|-----|-------------|
| **AWS Lambda** | Serverless, auto-scale, pay-per-use | EC2 (over-provision) |
| **DynamoDB** | <10ms latency, flexible schema | RDS (overkill) |
| **Terraform** | IaC, version control, reproducible | CloudFormation (verbose) |
| **MQTT** | Lightweight, IoT-optimized, QoS | HTTP (polling) |
| **Edge Processing** | Privacy, latency, cost | Cloud GPU (expensive) |
| **Random Forest** | Fast, fits microcontroller | Neural net (too heavy) |

---

## 🎤 Talking Points by Topic

### When Asked About State Machine:
- "Centralized state management prevents race conditions"
- "Sensor fusion: Camera confirms loading, IMU confirms spinning"
- "Confidence thresholds prevent false positives (>0.5)"
- "Temporal consistency: Require 2+ detections in 10 seconds"
- "Domain knowledge: Cycle times (25 min washer, 35 min dryer)"

### When Asked About Challenges:
1. **False Positives** → Temporal filtering (40% → 5%)
2. **WiFi Instability** → Local caching, retry logic
3. **Sensor Misalignment** → Magnitude features, calibration
4. **Model Size** → Random Forest (20 trees, depth 4)

### When Asked About Scalability:
- "Current: 4 machines, <$5/month"
- "At 1000 locations: Regional deployment, DynamoDB Global Tables"
- "Replace polling with WebSockets for push updates"
- "AWS IoT Core supports millions of devices"
- "Terraform modules make locations reproducible"

### When Asked About Testing:
- "Unit tests with moto (mock DynamoDB)"
- "Would add: LocalStack for integration tests"
- "Would add: E2E tests in staging environment"
- "Would add: Load tests (Locust) for concurrency"
- "Gap: No integration or chaos testing"

### When Asked About Security:
- "Issue: Lambda URLs have authorization_type = 'NONE'"
- "Fix: Add API Gateway with API keys"
- "Fix: Input validation with JSON Schema"
- "Fix: Rate limiting and WAF"
- "IAM roles correctly scoped (least privilege)"

---

## 💻 Code Sections to Explain

### 1. State Machine Core (updateMachineStateFunction.py:16-61)
```python
source = event.get('source')  # 'camera' or 'imu'
if source == 'camera':
    new_state = process_camera_event(...)
elif source == 'imu':
    new_state = process_imu_event(...)
```
**Key:** Single entry point, source-based routing

### 2. Temporal Consistency (img_receiver_aws.py:226-243)
```python
self.recent_detections[machine_id].append(time.time())
cutoff = time.time() - 10
self.recent_detections[machine_id] = [t for t in ... if t > cutoff]
num_recent = len(self.recent_detections[machine_id])
temporal_confidence = min(num_recent / 2.0, 1.0)
combined_confidence = (confidence * 0.7 + temporal_confidence * 0.3)
```
**Key:** Require 2+ detections in 10s, combine with pose confidence

### 3. Sensor Fusion (updateMachineStateFunction.py:121-153)
```python
if is_spinning == 1:
    if current_state == STATE_LOADING:
        return STATE_IN_USE  # Camera + IMU confirm
    elif current_state == STATE_AVAILABLE:
        recent_loading = get_recent_camera_detections(...)
        if recent_loading:
            return STATE_IN_USE  # Late camera detection
```
**Key:** IMU confirms camera events, handles missed camera events

### 4. Arduino Majority Voting (imu_dryer.ino:111-145)
```cpp
for (int i = 0; i < 30; i += 1) {
    get_acc_gyro_readings();
    preds[i] = pred;
}
if (true_cnt > 15) {  // Majority
    pred_res = 1;
}
confidence = (float)true_cnt / 30.0;
```
**Key:** 30-sample window, majority voting rejects noise

---

## 🚨 Anticipated Tough Questions

### "What if two Lambda functions update the same machine simultaneously?"
→ "Race condition exists. Would add optimistic locking (version numbers) or DynamoDB transactions. Short-term: events are complementary, so less critical. Long-term: event sourcing."

### "How do you handle duplicate events?"
→ "Current gap. MQTT QoS=1 allows duplicates. Would add idempotency keys (hash of machine_id+timestamp+sensor_type), store in ProcessedEvents table with TTL. AWS Lambda Powertools has built-in support."

### "Your ML model is trained on limited data. How do you prevent overfitting?"
→ "Simple models (Random Forest depth 4), feature engineering (magnitude), cross-validation. Would add: data augmentation, active learning with user feedback, monitoring confidence scores in production."

### "Why not use containers instead of Lambda?"
→ "Lambda advantages: Auto-scaling, pay-per-use, no ops. Our workload: Event-driven, sub-second execution, low frequency. Containers better for: Long-running processes, custom runtimes, high frequency. Could use Fargate if we needed persistent connections."

### "How would you scale to 1000 locations?"
→ "Regional deployment (Route53 geo-routing), DynamoDB Global Tables, WebSockets for push, AWS IoT Core (supports millions), Terraform modules per location, monitoring dashboard. Cost: ~$5-10K/month."

---

## 🎯 Your Strengths to Highlight

1. **Full-Stack Thinking:** Hardware → Edge → Cloud → Frontend integration
2. **Production Mindset:** Error handling, retry logic, testing, security
3. **Trade-off Analysis:** Every decision has pros/cons, you considered both
4. **Problem-Solving:** Real bugs (false positives, WiFi drops), real fixes
5. **Communication:** Can explain complex systems clearly
6. **Learning Agility:** University project → Production-quality thinking

---

## ❌ What NOT to Say

- ❌ "I just followed a tutorial"
- ❌ "My teammate handled that" (without understanding)
- ❌ "It's production-ready" (it's a prototype with known gaps)
- ❌ "I don't know" (without "but here's how I'd find out")
- ❌ Criticize teammates' work
- ❌ Oversell capabilities

---

## ✅ What TO Say

- ✅ "This is a prototype with these limitations..."
- ✅ "I made a mistake here, here's what I learned..."
- ✅ "I haven't explored that - can you tell me more?"
- ✅ "Trade-off was X vs. Y, chose X because..."
- ✅ "In production, I'd also add..."
- ✅ "Let me walk you through the code..."

---

## 🔄 State Machine States (Memorize)

```
AVAILABLE → LOADING → IN_USE → FINISHING → READY_TO_UNLOAD → AVAILABLE
```

**Transitions:**
- Camera bending + Available → Loading
- IMU spinning + Loading → In-Use
- IMU stopped + In-Use + cycle_time > min → Finishing
- Timer + Finishing → Ready-to-Unload
- Camera bending + Ready → Available

---

## 📈 Performance Breakdown

**Total Latency: ~600ms sensor to state update**
1. Arduino sampling: 300ms (30 samples × 10ms)
2. WiFi → AWS IoT: 100ms
3. IoT Rules → Lambda: 50ms
4. storeData → DynamoDB: 20ms
5. Invoke state machine: 10ms
6. State machine logic: 100ms
7. Update DynamoDB: 20ms

**Bottleneck:** Frontend polling (5 min average)
**Fix:** WebSockets for push notifications

---

## 🛡️ Security Gaps (Be Honest)

| Issue | Impact | Fix |
|-------|--------|-----|
| No auth on Lambda URLs | Anyone can read/write | API Gateway + API keys |
| No input validation | Injection attacks | JSON Schema validation |
| No rate limiting | DDoS / runaway costs | API Gateway throttling |
| CORS allow_methods = "*" | Unnecessary exposure | Restrict to GET, POST |
| Hardcoded credentials (Arduino) | Physical security risk | Certificate rotation |

---

## 💡 If You Get Stuck

**Strategies:**
1. **Think aloud:** "Let me think through this..."
2. **Draw:** "Can I draw the architecture?"
3. **Clarify:** "Do you mean X or Y?"
4. **Admit gaps:** "I don't know that specific detail, but..."
5. **Redirect:** "I haven't implemented that, but here's how I'd approach it"

---

## 🎤 Questions to Ask Them

**Technical:**
- "What latency requirements do your trading systems have?"
- "How do you handle distributed state management?"
- "What's your approach to testing financial systems?"

**Culture:**
- "What qualities do successful engineers here have?"
- "How does Marshall Wace support continuous learning?"
- "What would success look like in my first 6 months?"

**Projects:**
- "What's a recent technical challenge you're proud of?"
- "How do you balance innovation with reliability?"

---

## 📝 Opening Script (Memorize)

"Thanks for the opportunity. I'll give you a 12-minute overview of DLLM, my IoT laundry monitoring system, then walk through the code in detail.

My primary contribution was the entire AWS infrastructure - 10 Lambda functions, DynamoDB design, sensor fusion state machine, testing, and security. I'm familiar with the full system including my teammates' Arduino and camera work, so happy to discuss any component.

Let's start with the problem: residential laundry facilities with limited machines create frustration and wasted time. My solution uses IMU sensors and cameras with machine learning to detect machine status in real-time..."

---

## 🏁 Closing Script

"To wrap up: This project taught me how to build production-grade distributed systems - testing, security, error handling, infrastructure as code. I learned to make technical trade-offs consciously, balancing privacy vs. simplicity, cost vs. performance.

I'm excited about Marshall Wace because I want to work on systems at scale with real-world constraints. This was a taste, and I'm eager to learn more.

Ready for your questions!"

---

## 🔑 Absolute Must-Remember

1. **Your role:** AWS infrastructure, Lambda functions, state machine, testing
2. **Key innovation:** Sensor fusion + temporal consistency → 5% false positives
3. **Biggest learning:** Distributed systems need idempotency from day 1
4. **Main gap:** No integration tests (would use LocalStack)
5. **Security issue:** Lambda URLs unauthenticated (would add API Gateway)

---

## ⏰ If Running Low on Time

**Priority code to show:**
1. State machine sensor fusion (updateMachineStateFunction.py)
2. Temporal consistency (img_receiver_aws.py)
3. Terraform Lambda definitions (lambda.tf)

**Priority topics to cover:**
1. Why serverless (auto-scale, cost, no ops)
2. How sensor fusion works (camera + IMU better than either)
3. Real challenges faced (false positives, WiFi, testing)

---

## 🎯 Final Reminders

- ✅ Speak slowly and clearly
- ✅ Pause for questions
- ✅ Use concrete examples with numbers
- ✅ Admit limitations honestly
- ✅ Show enthusiasm for the problem
- ✅ Connect to their domain (trading, low latency)
- ✅ Breathe and smile!

**You've got this! 🚀**

