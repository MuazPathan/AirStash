# ⚡ AirStash — Local LAN File & Clipboard Bridge

A zero-cloud, single-file Python utility that turns your laptop into a high-speed local Wi-Fi transfer hub and bi-directional clipboard bridge for your phone.

## ✨ Features
- **Single-File Architecture:** Entire Flask backend + Neo-Brutalist Dark UI packed into `airstash.py`.
- **Instant QR Pairing:** Automatically detects your LAN IPv4 address and prints an ASCII QR code in the terminal.
- **Session PIN Auth:** Generates a unique 4-digit token on every startup to block unauthorized LAN access.
- **Bi-Directional Clipboard:** Push text from phone to laptop clipboard or pull laptop clipboard to phone in one tap.
- **Raw Multi-File Streaming:** Upload uncompressed photos, PDFs, APKs, or design assets straight to `./AirStash_Drop` with live progress tracking and one-click ZIP bundling.

## 🚀 Quick Start
Run Start.bat

     OR

```bash
python -m pip install flask pyperclip qrcode
python airstash.py