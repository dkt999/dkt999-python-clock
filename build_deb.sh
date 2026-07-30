#!/usr/bin/env bash
# ============================================================================
# build_deb.sh — Đóng gói DK Clock v1.0 thành file .deb cho Ubuntu / Debian
# (Tự động tăng version sau mỗi lần build để cài đè/nâng cấp)
# ============================================================================
set -e

APP_ID="dk-clock"                      # tên gói deb (viết thường, gạch ngang)
APP_DISPLAY_NAME="DK Clock v1.0"       # Tên hiển thị trên App Menu
APP_EXEC_NAME="DKClock"                # Tên file binary đã build trong dist/
MAINTAINER="Dinh Kim Thach <dinhkimthach.name.vn>"
ARCH="amd64"
ICON_SRC="assets/icon.png"             # Dùng trực tiếp icon.png
BUILD_SCRIPT="./build_ubuntu.sh"
VERSION_FILE="VERSION.txt"

# --- 0. Quản lý & Tự động tăng Version ---
if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0" > "$VERSION_FILE"
fi

# Đọc version hiện tại
CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d ' \n\r')

# Tách chuỗi Major.Minor.Build (Ví dụ: 1.0.0 -> 1.0 và 0)
BASE_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2}')
BUILD_NUM=$(echo "$CURRENT_VERSION" | awk -F. '{print $3}')

# Nếu chưa có Build_Num thì gán bằng 0
if [ -z "$BUILD_NUM" ]; then
    BUILD_NUM=0
fi

# Tăng Build Number lên 1
NEXT_BUILD_NUM=$((BUILD_NUM + 1))
NEW_VERSION="${BASE_VERSION}.${NEXT_BUILD_NUM}"

# Cập nhật lại vào file VERSION.txt
echo "$NEW_VERSION" > "$VERSION_FILE"
VERSION="$NEW_VERSION"

echo "=========================================="
echo "==> Version cũ: $CURRENT_VERSION"
echo "==> Version mới (Auto-increment): $VERSION"
echo "=========================================="

# --- 1. Build binary mới nhất ---
if [ ! -x "$BUILD_SCRIPT" ]; then
    echo "❌ Không tìm thấy $BUILD_SCRIPT (chưa chmod +x hoặc sai thư mục)."
    exit 1
fi
echo "==> Build binary mới nhất..."
"$BUILD_SCRIPT"

if [ ! -f "dist/${APP_EXEC_NAME}" ]; then
    echo "❌ Không thấy dist/${APP_EXEC_NAME} - build_ubuntu.sh có thể đã lỗi."
    exit 1
fi

# --- 2. Dựng cây thư mục gói .deb ---
PKG_ROOT="pkgroot_deb"
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/opt/${APP_ID}"
mkdir -p "$PKG_ROOT/usr/bin"
mkdir -p "$PKG_ROOT/usr/share/applications"
mkdir -p "$PKG_ROOT/usr/share/pixmaps"

# 2a. Copy Binary chính vào /opt/dk-clock/
cp "dist/${APP_EXEC_NAME}" "$PKG_ROOT/opt/${APP_ID}/${APP_EXEC_NAME}"
chmod 755 "$PKG_ROOT/opt/${APP_ID}/${APP_EXEC_NAME}"

# 2b. Symlink vào PATH để gõ "dk-clock" trong terminal là mở app
ln -sf "/opt/${APP_ID}/${APP_EXEC_NAME}" "$PKG_ROOT/usr/bin/${APP_ID}"

# 2c. Copy Icon ứng dụng
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$PKG_ROOT/usr/share/pixmaps/${APP_ID}.png"
    echo "==> Đã copy icon ứng dụng."
else
    echo "⚠️  Không thấy ${ICON_SRC}, bỏ qua bước copy icon."
fi

# 2d. File .desktop (Hiển thị tên DK Clock v1.0 trong Menu)
cat > "$PKG_ROOT/usr/share/applications/${APP_ID}.desktop" << EOF
[Desktop Entry]
Name=${APP_DISPLAY_NAME}
Comment=DK Clock - Trình đồng hồ, Báo thức và Đếm ngược đa năng
Exec=/usr/bin/${APP_ID}
Icon=${APP_ID}
Terminal=false
Type=Application
Categories=Utility;Clock;DesktopSettings;
StartupWMClass=${APP_EXEC_NAME}
EOF

# 2e. control - Khai báo thông tin gói
INSTALLED_SIZE=$(du -sk "$PKG_ROOT/opt/${APP_ID}" | cut -f1)
cat > "$PKG_ROOT/DEBIAN/control" << EOF
Package: ${APP_ID}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: ${MAINTAINER}
Description: DK Clock v1.0 - Ứng dụng đồng hồ đa năng cross-platform
 DK Clock v1.0 - Trình đồng hồ đa nền tảng (Ubuntu/Windows/macOS) 
 tích hợp World Clock, Báo thức, Đếm ngược và Bấm giờ giao diện Fluent Design.
EOF

# 2f. postinst - Cập nhật menu/cache sau khi cài
cat > "$PKG_ROOT/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
update-desktop-database -q /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true
exit 0
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postinst"

# 2g. postrm - Dọn cache khi gỡ
cat > "$PKG_ROOT/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
update-desktop-database -q /usr/share/applications 2>/dev/null || true
exit 0
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postrm"

chmod 755 "$PKG_ROOT/DEBIAN"

# --- 3. Đóng gói .deb ---
mkdir -p "installer/ubuntu"
OUT_DEB="installer/ubuntu/${APP_ID}_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$PKG_ROOT" "$OUT_DEB"

echo ""
echo "✅ Đã tạo thành công: ${OUT_DEB}"
echo "   Lệnh cài đè / nâng cấp:"
echo "     sudo apt install ./${OUT_DEB}"