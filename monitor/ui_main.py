"""
Hardware Monitor - UI Layer
PyQt6 implementation of CPU-Z style compact hardware and thermal monitor.
"""

import os
import sys
from typing import Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QLabel, QProgressBar, QGridLayout,
    QScrollArea, QFrame
)
from PyQt6.QtGui import QFont, QIcon

from monitor.backend import HardwareEngine, HardwareSnapshot, DiskDeviceSnapshot


class MonitorWorker(QThread):
    """Background worker thread collecting system hardware snapshots."""
    snapshot_ready = pyqtSignal(object)

    def __init__(self, interval: float = 1.0):
        super().__init__()
        self.interval = interval
        self.running = True
        self.engine = HardwareEngine()

    def run(self):
        while self.running:
            try:
                snapshot = self.engine.sample()
                self.snapshot_ready.emit(snapshot)
            except Exception as e:
                pass
            self.msleep(int(self.interval * 1000))

    def stop(self):
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    """Main CPU-Z style Hardware Monitor Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPU-Z Linux / Hardware Monitor")
        self.setFixedSize(430, 560)
        self.init_ui()
        self.load_styles()

        # Start worker thread
        self.worker = MonitorWorker(interval=1.0)
        self.worker.snapshot_ready.connect(self.on_snapshot_received)
        self.worker.start()

    def load_styles(self):
        qss_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def init_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # 1. Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)

        v_title = QVBoxLayout()
        v_title.setSpacing(1)
        title_label = QLabel("CPU-Z • HARDWARE MONITOR")
        title_label.setObjectName("AppTitle")
        subtitle_label = QLabel("Linux Hardware & Thermal Inspector")
        subtitle_label.setObjectName("AppSubtitle")
        v_title.addWidget(title_label)
        v_title.addWidget(subtitle_label)
        header_layout.addLayout(v_title)

        header_layout.addStretch()

        self.hdr_badge = QLabel("CPU: --°C")
        self.hdr_badge.setObjectName("HeaderBadge")
        header_layout.addWidget(self.hdr_badge)

        main_layout.addWidget(header_frame)

        # 2. Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs, stretch=1)

        # Build Tabs
        self.tab_cpu = self.build_cpu_tab()
        self.tab_gpu = self.build_gpu_tab()
        self.tab_ram = self.build_ram_tab()
        self.tab_disk = self.build_disk_tab()
        self.tab_sys = self.build_sys_tab()

        self.tabs.addTab(self.tab_cpu, "CPU")
        self.tabs.addTab(self.tab_gpu, "GPU")
        self.tabs.addTab(self.tab_ram, "Bellek")
        self.tabs.addTab(self.tab_disk, "Diskler")
        self.tabs.addTab(self.tab_sys, "Sistem")

        # 3. Footer Bar
        footer_frame = QFrame()
        footer_frame.setObjectName("FooterFrame")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(10, 4, 10, 4)

        self.footer_status = QLabel("Yenileme: 1.0 sn • QThread Aktif")
        self.footer_status.setObjectName("FooterText")
        footer_layout.addWidget(self.footer_status)
        footer_layout.addStretch()

        self.footer_uptime = QLabel("Uptime: --")
        self.footer_uptime.setObjectName("FooterText")
        footer_layout.addWidget(self.footer_uptime)

        main_layout.addWidget(footer_frame)

    # ================= CPU TAB =================
    def build_cpu_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(8)

        # Processor Group
        gb_proc = QGroupBox("İşlemci (Processor)")
        gl_proc = QGridLayout(gb_proc)
        gl_proc.setContentsMargins(8, 12, 8, 8)
        gl_proc.setHorizontalSpacing(10)
        gl_proc.setVerticalSpacing(5)

        self.lbl_cpu_name = QLabel("İşlemci Belirleniyor...")
        self.lbl_cpu_name.setProperty("class", "FieldValueBold")
        self.lbl_cpu_name.setWordWrap(True)
        gl_proc.addWidget(self.lbl_cpu_name, 0, 0, 1, 2)

        gl_proc.addWidget(QLabel("Çekirdek / İzlek:", objectName="lbl"), 1, 0)
        self.lbl_cpu_cores = QLabel("-- Çekirdek / -- İzlek")
        self.lbl_cpu_cores.setProperty("class", "FieldValue")
        gl_proc.addWidget(self.lbl_cpu_cores, 1, 1)

        gl_proc.addWidget(QLabel("Çalışma Frekansı:", objectName="lbl"), 2, 0)
        self.lbl_cpu_freq = QLabel("-- MHz")
        self.lbl_cpu_freq.setProperty("class", "FieldValue")
        gl_proc.addWidget(self.lbl_cpu_freq, 2, 1)

        layout.addWidget(gb_proc)

        # Real-time Metrics Group
        gb_live = QGroupBox("Anlık Yük & Sıcaklık")
        gl_live = QGridLayout(gb_live)
        gl_live.setContentsMargins(8, 12, 8, 8)
        gl_live.setHorizontalSpacing(10)
        gl_live.setVerticalSpacing(6)

        gl_live.addWidget(QLabel("İşlemci Kullanımı:"), 0, 0)
        self.lbl_cpu_usage = QLabel("0.0%")
        self.lbl_cpu_usage.setProperty("class", "FieldValueBold")
        gl_live.addWidget(self.lbl_cpu_usage, 0, 1, Qt.AlignmentFlag.AlignRight)

        self.bar_cpu_usage = QProgressBar()
        self.bar_cpu_usage.setRange(0, 100)
        self.bar_cpu_usage.setTextVisible(False)
        gl_live.addWidget(self.bar_cpu_usage, 1, 0, 1, 2)

        gl_live.addWidget(QLabel("Paket Sıcaklığı:"), 2, 0)
        self.lbl_cpu_pkg_temp = QLabel("-- °C")
        self.lbl_cpu_pkg_temp.setProperty("class", "TempBadge")
        gl_live.addWidget(self.lbl_cpu_pkg_temp, 2, 1, Qt.AlignmentFlag.AlignRight)

        gl_live.addWidget(QLabel("Çekirdek Sıcaklıkları:"), 3, 0)
        self.lbl_cpu_core_temps = QLabel("--")
        self.lbl_cpu_core_temps.setProperty("class", "FieldValue")
        gl_live.addWidget(self.lbl_cpu_core_temps, 3, 1, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(gb_live)
        layout.addStretch()
        return widget

    # ================= GPU TAB =================
    def build_gpu_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(8)

        gb_gpu = QGroupBox("Ekran Kartı (Display Adapter)")
        gl_gpu = QGridLayout(gb_gpu)
        gl_gpu.setContentsMargins(8, 12, 8, 8)
        gl_gpu.setHorizontalSpacing(10)
        gl_gpu.setVerticalSpacing(5)

        self.lbl_gpu_name = QLabel("GPU Bilgisi Alınıyor...")
        self.lbl_gpu_name.setProperty("class", "FieldValueBold")
        self.lbl_gpu_name.setWordWrap(True)
        gl_gpu.addWidget(self.lbl_gpu_name, 0, 0, 1, 2)

        gl_gpu.addWidget(QLabel("Üretici / Sürücü:"), 1, 0)
        self.lbl_gpu_vendor_drv = QLabel("--")
        self.lbl_gpu_vendor_drv.setProperty("class", "FieldValue")
        gl_gpu.addWidget(self.lbl_gpu_vendor_drv, 1, 1)

        gl_gpu.addWidget(QLabel("VRAM (Video Bellek):"), 2, 0)
        self.lbl_gpu_vram = QLabel("-- MB")
        self.lbl_gpu_vram.setProperty("class", "FieldValue")
        gl_gpu.addWidget(self.lbl_gpu_vram, 2, 1)

        layout.addWidget(gb_gpu)

        gb_live = QGroupBox("Anlık Yük & Sıcaklık")
        gl_live = QGridLayout(gb_live)
        gl_live.setContentsMargins(8, 12, 8, 8)
        gl_live.setHorizontalSpacing(10)
        gl_live.setVerticalSpacing(6)

        gl_live.addWidget(QLabel("GPU Kullanımı:"), 0, 0)
        self.lbl_gpu_usage = QLabel("0.0%")
        self.lbl_gpu_usage.setProperty("class", "FieldValueBold")
        gl_live.addWidget(self.lbl_gpu_usage, 0, 1, Qt.AlignmentFlag.AlignRight)

        self.bar_gpu_usage = QProgressBar()
        self.bar_gpu_usage.setRange(0, 100)
        self.bar_gpu_usage.setTextVisible(False)
        gl_live.addWidget(self.bar_gpu_usage, 1, 0, 1, 2)

        gl_live.addWidget(QLabel("GPU Sıcaklığı:"), 2, 0)
        self.lbl_gpu_temp = QLabel("-- °C")
        self.lbl_gpu_temp.setProperty("class", "TempBadge")
        gl_live.addWidget(self.lbl_gpu_temp, 2, 1, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(gb_live)
        layout.addStretch()
        return widget

    # ================= RAM & MOTHERBOARD TAB =================
    def build_ram_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(8)

        # RAM Group
        gb_ram = QGroupBox("Sistem Belleği (RAM)")
        gl_ram = QGridLayout(gb_ram)
        gl_ram.setContentsMargins(8, 12, 8, 8)
        gl_ram.setHorizontalSpacing(10)
        gl_ram.setVerticalSpacing(5)

        gl_ram.addWidget(QLabel("Toplam / Kullanılan:"), 0, 0)
        self.lbl_ram_cap = QLabel("-- / -- GB")
        self.lbl_ram_cap.setProperty("class", "FieldValueBold")
        gl_ram.addWidget(self.lbl_ram_cap, 0, 1, Qt.AlignmentFlag.AlignRight)

        self.bar_ram_usage = QProgressBar()
        self.bar_ram_usage.setRange(0, 100)
        self.bar_ram_usage.setTextVisible(False)
        gl_ram.addWidget(self.bar_ram_usage, 1, 0, 1, 2)

        gl_ram.addWidget(QLabel("Kullanılabilir Bellek:"), 2, 0)
        self.lbl_ram_free = QLabel("-- GB")
        self.lbl_ram_free.setProperty("class", "FieldValue")
        gl_ram.addWidget(self.lbl_ram_free, 2, 1, Qt.AlignmentFlag.AlignRight)

        gl_ram.addWidget(QLabel("Takas Alanı (Swap):"), 3, 0)
        self.lbl_swap_info = QLabel("-- GB")
        self.lbl_swap_info.setProperty("class", "FieldValue")
        gl_ram.addWidget(self.lbl_swap_info, 3, 1, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(gb_ram)

        # Motherboard Group
        gb_mb = QGroupBox("Anakart & BIOS (Mainboard)")
        gl_mb = QGridLayout(gb_mb)
        gl_mb.setContentsMargins(8, 12, 8, 8)
        gl_mb.setHorizontalSpacing(10)
        gl_mb.setVerticalSpacing(5)

        gl_mb.addWidget(QLabel("Üretici (Vendor):"), 0, 0)
        self.lbl_mb_vendor = QLabel("--")
        self.lbl_mb_vendor.setProperty("class", "FieldValue")
        gl_mb.addWidget(self.lbl_mb_vendor, 0, 1)

        gl_mb.addWidget(QLabel("Model Adı:"), 1, 0)
        self.lbl_mb_model = QLabel("--")
        self.lbl_mb_model.setProperty("class", "FieldValueBold")
        gl_mb.addWidget(self.lbl_mb_model, 1, 1)

        gl_mb.addWidget(QLabel("BIOS Sürümü:"), 2, 0)
        self.lbl_mb_bios = QLabel("--")
        self.lbl_mb_bios.setProperty("class", "FieldValue")
        gl_mb.addWidget(self.lbl_mb_bios, 2, 1)

        layout.addWidget(gb_mb)
        layout.addStretch()
        return widget

    # ================= DISK TAB =================
    def build_disk_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        self.layout_disk = QVBoxLayout(widget)
        self.layout_disk.setContentsMargins(10, 6, 10, 10)
        self.layout_disk.setSpacing(8)

        scroll.setWidget(widget)
        return scroll

    # ================= SYSTEM TAB =================
    def build_sys_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(8)

        gb_sys = QGroupBox("İşletim Sistemi & Çekirdek")
        gl_sys = QGridLayout(gb_sys)
        gl_sys.setContentsMargins(8, 12, 8, 8)
        gl_sys.setHorizontalSpacing(10)
        gl_sys.setVerticalSpacing(5)

        gl_sys.addWidget(QLabel("Dağıtım (OS):"), 0, 0)
        self.lbl_os_name = QLabel("--")
        self.lbl_os_name.setProperty("class", "FieldValueBold")
        gl_sys.addWidget(self.lbl_os_name, 0, 1)

        gl_sys.addWidget(QLabel("Kernel Sürümü:"), 1, 0)
        self.lbl_kernel = QLabel("--")
        self.lbl_kernel.setProperty("class", "FieldValue")
        gl_sys.addWidget(self.lbl_kernel, 1, 1)

        gl_sys.addWidget(QLabel("Mimari:"), 2, 0)
        self.lbl_arch = QLabel("x86_64")
        self.lbl_arch.setProperty("class", "FieldValue")
        gl_sys.addWidget(self.lbl_arch, 2, 1)

        layout.addWidget(gb_sys)

        gb_about = QGroupBox("Hakkında")
        vl_about = QVBoxLayout(gb_about)
        vl_about.setContentsMargins(8, 10, 8, 8)
        lbl_about_txt = QLabel(
            "<b>CPU-Z Hardware Monitor for Linux</b><br>"
            "Minimalist, yüksek performanslı ve hafif donanım izleyici.<br>"
            "<i>PyQt6 & Python 3. Thread-Safe Engine.</i>"
        )
        lbl_about_txt.setWordWrap(True)
        vl_about.addWidget(lbl_about_txt)
        layout.addWidget(gb_about)

        layout.addStretch()
        return widget

    def update_temp_badge(self, label: QLabel, temp_val: Optional[float]):
        """Formats temperature and applies thermal color badge."""
        if temp_val is None or temp_val <= 0:
            label.setText("N/A")
            label.setProperty("class", "TempBadge")
            label.setStyle(label.style())
            return

        label.setText(f"{temp_val:.1f} °C")
        if temp_val >= 80.0:
            label.setProperty("class", "TempBadgeHot")
        elif temp_val >= 65.0:
            label.setProperty("class", "TempBadgeWarn")
        else:
            label.setProperty("class", "TempBadge")
        label.setStyle(label.style())

    def on_snapshot_received(self, snap: HardwareSnapshot):
        """Processes real-time hardware snapshot and updates the GUI."""
        # 1. Header
        if snap.cpu_package_temp:
            self.hdr_badge.setText(f"CPU: {snap.cpu_package_temp:.0f}°C | {snap.cpu_usage_percent:.0f}%")
        else:
            self.hdr_badge.setText(f"CPU: {snap.cpu_usage_percent:.0f}%")

        # 2. CPU Tab
        self.lbl_cpu_name.setText(snap.cpu_model)
        self.lbl_cpu_cores.setText(f"{snap.cpu_cores_physical} Fiziksel / {snap.cpu_cores_logical} Mantıksal")
        self.lbl_cpu_freq.setText(f"{snap.cpu_freq_mhz:.0f} MHz" if snap.cpu_freq_mhz else "N/A")
        self.lbl_cpu_usage.setText(f"{snap.cpu_usage_percent:.1f}%")
        self.bar_cpu_usage.setValue(int(snap.cpu_usage_percent))
        self.update_temp_badge(self.lbl_cpu_pkg_temp, snap.cpu_package_temp)

        if snap.cpu_core_temps:
            self.lbl_cpu_core_temps.setText(" | ".join(f"{t:.0f}°C" for t in snap.cpu_core_temps[:4]))
        else:
            self.lbl_cpu_core_temps.setText("Mevcut Değil")

        # 3. GPU Tab
        self.lbl_gpu_name.setText(snap.gpu_model)
        self.lbl_gpu_vendor_drv.setText(f"{snap.gpu_vendor} / {snap.gpu_driver}")
        if snap.gpu_vram_total_mb > 0:
            self.lbl_gpu_vram.setText(f"{snap.gpu_vram_used_mb:.0f} MB / {snap.gpu_vram_total_mb:.0f} MB")
        else:
            self.lbl_gpu_vram.setText("Paylaşımlı Bellek / Dinamik")

        self.lbl_gpu_usage.setText(f"{snap.gpu_usage_percent:.1f}%")
        self.bar_gpu_usage.setValue(int(snap.gpu_usage_percent))
        self.update_temp_badge(self.lbl_gpu_temp, snap.gpu_temp)

        # 4. RAM Tab
        self.lbl_ram_cap.setText(f"{snap.ram_used_gb:.1f} GB / {snap.ram_total_gb:.1f} GB")
        self.bar_ram_usage.setValue(int(snap.ram_usage_percent))
        self.lbl_ram_free.setText(f"{snap.ram_free_gb:.1f} GB")
        self.lbl_swap_info.setText(f"{snap.swap_used_gb:.1f} GB / {snap.swap_total_gb:.1f} GB ({snap.swap_usage_percent:.0f}%)")

        self.lbl_mb_vendor.setText(snap.mb_vendor)
        self.lbl_mb_model.setText(snap.mb_model)
        self.lbl_mb_bios.setText(snap.mb_bios)

        # 5. Disk Tab (Rebuild if count changed or update dynamically)
        while self.layout_disk.count() > 0:
            item = self.layout_disk.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for d in snap.disks:
            gb = QGroupBox(f"Sürücü: /dev/{d.name}")
            gl = QGridLayout(gb)
            gl.setContentsMargins(8, 12, 8, 8)
            gl.setHorizontalSpacing(10)
            gl.setVerticalSpacing(4)

            lbl_model = QLabel(d.model)
            lbl_model.setProperty("class", "FieldValueBold")
            gl.addWidget(lbl_model, 0, 0, 1, 2)

            gl.addWidget(QLabel(f"Bağlantı: {d.mountpoint}"), 1, 0)
            gl.addWidget(QLabel(f"{d.used_gb:.1f} GB / {d.size_gb:.1f} GB ({d.usage_percent:.0f}%)"), 1, 1, Qt.AlignmentFlag.AlignRight)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(d.usage_percent))
            bar.setTextVisible(False)
            gl.addWidget(bar, 2, 0, 1, 2)

            gl.addWidget(QLabel(f"Hız: Okuma {d.read_speed_mbs} MB/s • Yazma {d.write_speed_mbs} MB/s"), 3, 0)
            t_badge = QLabel()
            self.update_temp_badge(t_badge, d.temperature)
            gl.addWidget(t_badge, 3, 1, Qt.AlignmentFlag.AlignRight)

            self.layout_disk.addWidget(gb)

        self.layout_disk.addStretch()

        # 6. System Tab
        self.lbl_os_name.setText(snap.os_name)
        self.lbl_kernel.setText(snap.kernel_version)

        # 7. Footer Uptime
        mins, secs = divmod(int(snap.uptime_seconds), 60)
        hours, mins = divmod(mins, 60)
        self.footer_uptime.setText(f"Açık Kalma: {hours:02d}:{mins:02d}:{secs:02d}")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
