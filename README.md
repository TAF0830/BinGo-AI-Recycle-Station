# BinGo: Edge-AI Waste Sorter & Rewards

An edge-computing recycling station running real-time waste classification, paired with an ESP32-S3 microcontroller and a mobile web dashboard.

---

## Demo Video & Hardware

<!-- You can directly drag and drop your .mp4 video file or photos here in GitHub edit mode to embed them -->

---

## What It Does

- **Real-Time AI Vision**: Detects and sorts waste into Food, General, Recyclable, and Special Waste via local webcam feed.
- **Physical Indication**: Sends serial commands to an ESP32-S3 microcontroller to trigger category LEDs/actuators.
- **Mobile Eco-Wallet**: Users scan the station's QR code to connect over cellular data (via ngrok tunnel) without local Wi-Fi limits, earning points and claiming vouchers (Tealive, Grab, Subway).
- **Session Protection**: Station stays locked until an active user connects; automatically resets on disconnection to protect point balances.

---

## Tech Stack

- **Computer Vision & Backend**: Python, OpenCV, TensorFlow / Keras, Flask
- **Embedded Controller**: ESP32-S3 (C++ / Arduino UART @ 115200 baud)
- **Mobile Web App**: HTML5, Vanilla JavaScript, Tailwind CSS
- **Networking**: Cloud tunneling via ngrok

---

## File Overview

- `main.py` - Core server managing camera inference, serial logic, and mobile endpoints.
- `esp32_firmware.ino` - Microcontroller code mapping serial inputs (0-4) to GPIO pins.
- `keras_model.h5` & `labels.txt` - Trained classification model and class index mappings.

---

## Getting Started

1. Connect the ESP32-S3 to your PC via USB (default: `COM6` at `115200` baud).

2. Install dependencies:
```bash
pip install opencv-python numpy tensorflow tf-keras pyserial pyttsx3 flask

```

3. Run the vision station (Terminal 1):

```bash
python main.py

```

4. Expose the server for mobile access (Terminal 2):

```bash
ngrok http 5000 --url [https://latrine-outscore-wharf.ngrok-free.dev](https://latrine-outscore-wharf.ngrok-free.dev)

```

5. Scan the displayed QR code on your smartphone to start depositing:

