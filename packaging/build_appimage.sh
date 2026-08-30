#!/bin/bash
set -e

echo "=== 1. Building Standalone Binary with PyInstaller ==="
pip install pyinstaller

pyinstaller --noconfirm --clean --windowed \
    --name hardware-monitor \
    --add-data "monitor/style.qss:monitor" \
    --hidden-import "PyQt6" \
    --hidden-import "psutil" \
    --hidden-import "pynvml" \
    main.py

echo "=== 2. Setting up AppDir ==="
rm -rf AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

cp dist/hardware-monitor AppDir/usr/bin/
cp packaging/hardware-monitor.desktop AppDir/
cp packaging/hardware-monitor.desktop AppDir/usr/share/applications/ 2>/dev/null || true

# AppRun symlink / script
cat > AppDir/AppRun <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/hardware-monitor" "$@"
APPRUN
chmod +x AppDir/AppRun

# Download standard appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q -c "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

# Download or create placeholder icon
if [ ! -f "AppDir/hardware-monitor.png" ]; then
    python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (256, 256), color=(37, 99, 235, 255))
d = ImageDraw.Draw(img)
d.rectangle([(40, 40), (216, 216)], fill=(255, 255, 255, 230), outline=(220, 220, 220), width=6)
img.save('AppDir/hardware-monitor.png')
img.save('AppDir/usr/share/icons/hicolor/256x256/apps/hardware-monitor.png')
" 2>/dev/null || touch AppDir/hardware-monitor.png
fi

echo "=== 3. Packaging into AppImage ==="
ARCH=x86_64 ./appimagetool-x86_64.AppImage --appimage-extract-and-run AppDir Hardware-Monitor-x86_64.AppImage

echo "=== Done! Generated Hardware-Monitor-x86_64.AppImage ==="
