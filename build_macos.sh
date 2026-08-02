#!/usr/bin/env bash
# ============================================================================
# build_macos.sh — Build DK Clock v1.0 thành App Bundle (.app) cho macOS
# ============================================================================
set -e

APP_NAME="DKClock"              # Tên ứng dụng
ENTRY_POINT="main.py"
PNG_ICON="assets/icon.png"      # Icon nguồn
ICNS_ICON="assets/icon.icns"    # Icon định dạng macOS
ASSETS_DIR="assets"

# --- 1. Kiểm tra thư mục gốc ---
if [ ! -f "$ENTRY_POINT" ]; then
    echo "❌ Không tìm thấy $ENTRY_POINT. Hãy chạy script này từ thư mục gốc project."
    exit 1
fi

# --- 2. Xử lý Icon (.png -> .icns) nếu chưa có .icns ---
if [ ! -f "$ICNS_ICON" ] && [ -f "$PNG_ICON" ]; then
    echo "==> Tạo icon.icns cho macOS từ icon.png..."
    ICONSET_DIR="assets/icon.iconset"
    mkdir -p "$ICONSET_DIR"
    sips -z 16 16     "$PNG_ICON" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null 2>&1
    sips -z 32 32     "$PNG_ICON" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null 2>&1
    sips -z 32 32     "$PNG_ICON" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null 2>&1
    sips -z 64 64     "$PNG_ICON" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null 2>&1
    sips -z 128 128   "$PNG_ICON" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null 2>&1
    sips -z 256 256   "$PNG_ICON" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null 2>&1
    sips -z 256 256   "$PNG_ICON" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null 2>&1
    sips -z 512 512   "$PNG_ICON" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null 2>&1
    sips -z 512 512   "$PNG_ICON" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null 2>&1
    sips -z 1024 1024 "$PNG_ICON" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null 2>&1
    iconutil -c icns "$ICONSET_DIR" -o "$ICNS_ICON"
    rm -rf "$ICONSET_DIR"
fi

# --- 3. Tạo virtualenv riêng cho build ---
if [ ! -d ".venv-build" ]; then
    echo "==> Tạo virtualenv .venv-build..."
    python3 -m venv .venv-build
fi
source .venv-build/bin/activate

echo "==> Cài dependencies..."
pip install --upgrade pip -q
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
else
    pip install PyQt6 PyQt6-Fluent-Widgets -q
fi
pip install pyinstaller -q

# --- 4. Dọn build cũ ---
rm -rf build dist "${APP_NAME}.spec"

# --- 5. Module ẩn cần thiết ---
HIDDEN_IMPORTS=(
    "--hidden-import=PyQt6.QtSvg"
    "--hidden-import=PyQt6.QtNetwork"
    "--hidden-import=PyQt6.QtMultimedia"
    "--hidden-import=PyQt6.QtMultimediaWidgets"
)

COLLECT_ALL=(
    "--collect-all=qfluentwidgets"
)

# --- 6. Dữ liệu đi kèm ---
ADD_DATA=()
if [ -d "$ASSETS_DIR" ]; then
    ADD_DATA+=("--add-data=${ASSETS_DIR}:${ASSETS_DIR}")
fi

# --- 7. Build macOS App Bundle ---
echo "==> Đang build ${APP_NAME}.app cho macOS..."
ICON_ARG=""
if [ -f "$ICNS_ICON" ]; then
    ICON_ARG="--icon=${ICNS_ICON}"
elif [ -f "$PNG_ICON" ]; then
    ICON_ARG="--icon=${PNG_ICON}"
fi

# Lưu ý: Trên macOS dùng --windowed hoặc --onedir để sinh ra file .app chuẩn
pyinstaller \
    --name "$APP_NAME" \
    --windowed \
    --onedir \
    $ICON_ARG \
    "${ADD_DATA[@]}" \
    "${HIDDEN_IMPORTS[@]}" \
    "${COLLECT_ALL[@]}" \
    "$ENTRY_POINT"

deactivate

echo ""
echo "✅ Build xong! Application bundle tại: dist/${APP_NAME}.app"