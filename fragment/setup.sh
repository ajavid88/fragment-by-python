#!/bin/bash

echo "==================================================="
echo "=      Xray Fragment Tester Setup Script          ="
echo "=           Linux/Fedora Edition                  ="
echo "==================================================="
echo ""

# --- بررسی و نصب پیش‌نیازهای سیستم ---
echo "[0/3] Checking system dependencies..."

# نصب unzip اگر موجود نیست
if ! command -v unzip &> /dev/null; then
    echo "Installing 'unzip'..."
    sudo dnf install -y unzip
fi

# نصب wget اگر موجود نیست
if ! command -v wget &> /dev/null; then
    echo "Installing 'wget'..."
    sudo dnf install -y wget
fi

# نصب tkinter (برای GUI)
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "Installing python3-tkinter..."
    sudo dnf install -y python3-tkinter
fi

echo "✓ System dependencies are ready."

echo ""
echo "[1/3] Installing Python libraries from requirements.txt..."
if [ -f "requirements.txt" ]; then
    # استفاده از --break-system-packages برای فدورا ۴۴ (PEP 668)
    pip3 install --break-system-packages -r requirements.txt
    if [ $? -ne 0 ]; then
        echo ""
        echo "✗ ERROR: Failed to install Python libraries."
        echo "Try: sudo dnf install python3-pip"
        exit 1
    fi
    echo "✓ Python libraries installed."
else
    echo "⚠ WARNING: requirements.txt not found. Skipping pip install."
fi

echo ""
echo "[2/3] Downloading latest Xray-core for Linux (64-bit)..."
wget -q --show-progress -O xray.zip "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
if [ $? -ne 0 ]; then
    echo ""
    echo "✗ ERROR: Failed to download Xray-core."
    echo "Please check your internet connection."
    exit 1
fi
echo "✓ Xray-core downloaded."

echo ""
echo "[3/3] Extracting Xray-core..."
unzip -o xray.zip
if [ $? -ne 0 ]; then
    echo ""
    echo "✗ ERROR: Failed to extract xray.zip."
    exit 1
fi

# پاک کردن فایل فشرده
rm -f xray.zip

# دادن دسترسی اجرا
chmod +x xray

echo "✓ xray binary is ready."

echo ""
echo "==================================================="
echo "=              Setup Complete!                    ="
echo "==================================================="
echo ""
echo "Next steps:"
echo "  1. Make sure you have 'core.py' and 'A.py' files"
echo "  2. Create 'Xray_Config (Fragment).json' base config"
echo "  3. Run: python3 launcher.py"
echo ""
echo "==================================================="
echo ""
