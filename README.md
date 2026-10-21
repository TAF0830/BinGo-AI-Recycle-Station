
```markdown
# ♻️ BinGo: Smart AI Waste Sorting & Gamified Recycling Station

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20App-lightgrey.svg)](https://flask.palletsprojects.com/)
[![ESP32-S3](https://img.shields.io/badge/Hardware-ESP32--S3-red.svg)](https://www.espressif.com/)
[![TensorFlow / Keras](https://img.shields.io/badge/AI-Keras%20%2F%20MobileNet-orange.svg)](https://teachablemachine.withgoogle.com/)

**BinGo** is an intelligent, hardware-integrated recycling station designed to automate waste segregation and promote eco-friendly behavior. Powered by a lightweight Deep Learning vision model and an **ESP32-S3** microcontroller, BinGo accurately identifies waste categories in real time, actuates hardware status indicators, and provides users with a gamified mobile platform to earn rewards and redeem vouchers.

---

## 🌟 Key Features

- 🧠 **Real-Time AI Vision Classification**: Utilizes a MobileNet-based Keras image classification model to classify items across multiple waste streams and filter background noise with high confidence.
- ⚡ **Physical Hardware Actuation**: Seamless serial communication with an **ESP32-S3** microcontroller driving LED indicators (GPIO 4–7) to guide users through the physical sorting process.
- 🔄 **Smart Deposit Verification**: State-machine-based deposit verification that detects item presentation, waits for disposal, and automatically awards points once the background clear-frame threshold is reached.
- 📱 **Mobile Web Application**:
  - Zero-installation mobile web interface accessible via dynamic QR code or local network.
  - Real-time station pairing, active session heartbeats, and auto-lock standby protection.
  - Digital reward wallet displaying live balance updates, sorting history, and sponsor voucher redemptions.
- 🔊 **Voice Feedback**: Real-time auditory confirmation using Text-to-Speech (TTS) to provide an accessible and interactive user experience.

---

## 🏗️ System Architecture


```

```
                   ┌────────────────────────┐
                   │  Camera (OpenCV Feed)  │
                   └───────────┬────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │ AI Inference (Keras / Model) │
                └───────┬──────────────┬───────┘
                        │              │
  Serial Commands (b"0"-b"4")   Detection State & Points
                        │              │
                        ▼              ▼
       ┌──────────────────────┐  ┌───────────────────────┐
       │ ESP32-S3 Controller  │  │ Flask Web Server      │
       └──────────┬───────────┘  └───────────┬───────────┘
                  │                          │
                  ▼                          ▼
       [ Status LEDs: GPIO 4-7 ]  [ Mobile Client Interface ]

```

```

---

## 🗂️ Classification & Pin Mapping

| Class Index | Category | Serial Command | Target Pin | LED Indicator | Reward Points |
| :---: | :--- | :---: | :---: | :---: | :---: |
| `0` | **Food Waste** | `b"1"` | GPIO 7 | 🟢 Green | +3 pts |
| `1` | **General Waste** | `b"2"` | GPIO 6 | 🟡 Yellow | +1 pt |
| `2` | **Recyclable Waste** | `b"3"` | GPIO 5 | ⚪ White | +10 pts |
| `3` | **Special Waste** | `b"4"` | GPIO 4 | 🔴 Red | +15 pts |
| `4` | **Background / Idle** | `b"0"` | — | All LEDs OFF | — |

---

## 🛠️ Tech Stack

- **Software & Backend**: Python 3, Flask, OpenCV (`cv2`), TensorFlow / `tf_keras`, `pyttsx3`, `pyserial`
- **Frontend**: HTML5, TailwindCSS, Vanilla JavaScript (Fetch API, LocalStorage/Cookies)
- **Hardware & Microcontroller**: ESP32-S3, Arduino C++, External LEDs & Resistors
- **Networking & Tunnelling**: ngrok

---

## 📁 Repository Structure

```text
├── esp32_firmware/
│   └── esp32_firmware.ino      # ESP32-S3 microcontroller firmware
├── keras_model.h5              # Pre-trained Keras model weights
├── labels.txt                  # Output class label order mapping
├── main.py                     # Core vision processing thread & Flask web server
├── users.json                  # Local database for user sessions, balances & vouchers
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation

```

---

## 🚀 Getting Started

### 1. Hardware Setup & Flashing

1. Open `esp32_firmware/esp32_firmware.ino` using the Arduino IDE.
2. Select your board as **ESP32S3 Dev Module**.
3. Wire your LEDs with current-limiting resistors to **GPIO 4, 5, 6, and 7**.
4. Flash the code to your ESP32-S3 and note down the connected serial port (e.g., `COM6`).

### 2. Environment Configuration

Clone the repository and install the dependencies:

```bash
git clone [https://github.com/your-username/BinGo.git](https://github.com/your-username/BinGo.git)
cd BinGo

pip install -r requirements.txt

```

*Required packages:*

```text
flask
opencv-python
numpy
tf-keras
tensorflow
pyserial
pyttsx3

```

### 3. Running BinGo

1. Verify the serial port in `main.py`:
```python
SERIAL_PORT = "COM6"
BAUD_RATE = 115200

```


2. Start the station:
```bash
python main.py

```


3. Access the dashboard locally via `http://127.0.0.1:5000`.
4. To allow mobile access via public URL, start an ngrok tunnel explicitly specifying IPv4:
```bash
ngrok http 127.0.0.1:5000

```



---

## 📱 User Workflow

1. **Authentication**: The system stays in a secure locked state until a user scans the station QR code and taps **"Start Deposit"** on their mobile interface.
2. **Identification**: The user holds the waste item in front of the camera. The AI processes the frame and confirms the category once confidence exceeds 75%.
3. **Hardware Indication**: The station transmits the designated command to the ESP32-S3, illuminating the corresponding category LED to guide disposal.
4. **Deposit Confirmation**: Once the item leaves the camera view for over 1.2 seconds, the station awards eco-points, provides TTS confirmation, and resets the LEDs.
5. **Reward Redemption**: Accumulated points can be instantly redeemed for merchant vouchers directly inside the digital wallet interface.

---

## 📄 License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).

```

```
