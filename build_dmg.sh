#!/usr/bin/env bash
# ============================================================================
# build_dmg.sh — Đóng gói DK Clock v1.0 thành file .dmg cho macOS
# (Tự động tăng version sau mỗi lần build)
# ============================================================================
set -e

APP_ID="dk-clock"                      # Tên file dmg
APP_DISPLAY_NAME="DK Clock"            # Tên app hiển thị
APP_EXEC_NAME="DKClock"                # Tên app folder trong dist/ (DKClock.app)
BUILD_SCRIPT="./build_macos.sh"
VERSION_FILE="VERSION.txt"

# --- 0. Quản lý & Tự động tăng Version ---
if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0" > "$VERSION_FILE"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d ' \n\r')
BASE_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2}')
BUILD_NUM=$(echo "$CURRENT_VERSION" | awk -F. '{print $3}')

if [ -z "$BUILD_NUM" ]; then
    BUILD_NUM=0
fi

NEXT_BUILD_NUM=$((BUILD_NUM + 1))
NEW_VERSION="${BASE_VERSION}.${NEXT_BUILD_NUM}"

echo "$NEW_VERSION" > "$VERSION_FILE"
VERSION="$NEW_VERSION"

echo "=========================================="
echo "==> Version cũ: $CURRENT_VERSION"
echo "==> Version mới (Auto-increment): $VERSION"
echo "=========================================="

# --- 1. Build .app mới nhất ---
if [ ! -x "$BUILD_SCRIPT" ]; then
    echo "❌ Không tìm thấy $BUILD_SCRIPT (chưa chmod +x hoặc sai thư mục)."
    exit 1
fi
echo "==> Build .app mới nhất..."
"$BUILD_SCRIPT"

APP_PATH="dist/${APP_EXEC_NAME}.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ Không thấy ${APP_PATH} - build_macos.sh có thể đã lỗi."
    exit 1
fi

# --- 2. Dựng thư mục tạm để đóng gói DMG ---
DMG_STAGING="pkgroot_dmg"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"

# Copy file .app vào thư mục tạm
cp -R "$APP_PATH" "$DMG_STAGING/"

# Tạo Symlink đến /Applications để người dùng dễ dàng kéo-thả
ln -s /Applications "$DMG_STAGING/Applications"

# --- 3. Đóng gói .dmg ---
OUT_DIR="installer/macos"
mkdir -p "$OUT_DIR"
OUT_DMG="${OUT_DIR}/${APP_ID}_v${VERSION}_macOS.dmg"

rm -f "$OUT_DMG"

echo "==> Đang nén file .dmg..."
hdiutil create -volname "${APP_DISPLAY_NAME} v${VERSION}" \
               -srcfolder "$DMG_STAGING" \
               -ov -format UDZO "$OUT_DMG"

# Dọn dẹp thư mục tạm
rm -rf "$DMG_STAGING"

echo ""
echo "✅ Đã tạo gói: ${OUT_DMG}"
echo "   Mở file DMG và kéo ${APP_EXEC_NAME}.app vào thư mục Applications để cài đặt."