"""
Hardware Monitor - Backend Data Engine
Thread-safe hardware info collection for Linux systems.
Supports CPU, GPU (NVIDIA/AMD/Intel), Disk (NVMe/SATA/SSD), RAM, and Motherboard.
"""

import os
import re
import time
import glob
import platform
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import psutil

# Safe NVIDIA NVML import
_HAS_NVML = False
try:
    import pynvml
    pynvml.nvmlInit()
    _HAS_NVML = True
except Exception:
    _HAS_NVML = False


def _safe_read_file(path: str) -> str:
    """Safely reads a single-line sysfs/procfs file."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def get_cpu_model_name() -> str:
    """Retrieves CPU Model Name from /proc/cpuinfo or lscpu."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "x86_64 Processor"


def get_motherboard_info() -> Dict[str, str]:
    """Reads DMI motherboard and BIOS information."""
    vendor = _safe_read_file("/sys/class/dmi/id/board_vendor")
    name = _safe_read_file("/sys/class/dmi/id/board_name")
    bios = _safe_read_file("/sys/class/dmi/id/bios_version")
    product = _safe_read_file("/sys/class/dmi/id/product_name")

    v_str = vendor if vendor and "O.E.M" not in vendor else "Standard PC"
    m_str = name if name and "O.E.M" not in name else (product or "Mainboard")

    return {
        "vendor": v_str,
        "model": m_str,
        "bios_version": bios or "N/A",
    }


def get_system_overview() -> Dict[str, str]:
    """Retrieves OS and kernel release details."""
    os_name = "Linux"
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')
                    break

    return {
        "os_name": os_name,
        "kernel": platform.release(),
        "arch": platform.machine(),
        "hostname": platform.node(),
    }


def get_cpu_temperatures() -> Dict[str, Any]:
    """
    Multi-tier CPU Temperature Reader:
    1. psutil.sensors_temperatures() (coretemp, k10temp, zenpower, cpu_thermal, acpitz)
    2. /sys/class/hwmon/
    3. /sys/class/thermal/thermal_zone*
    """
    package_temp: Optional[float] = None
    core_temps: List[float] = []

    # 1. psutil
    try:
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        for key in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz", "soc_thermal"):
            if key in temps and temps[key]:
                for entry in temps[key]:
                    if "Package" in entry.label or "Tctl" in entry.label or entry.label == "":
                        if package_temp is None and entry.current is not None:
                            package_temp = float(entry.current)
                    elif "Core" in entry.label or "Tdie" in entry.label:
                        if entry.current is not None:
                            core_temps.append(float(entry.current))

                if package_temp is None and temps[key]:
                    package_temp = float(temps[key][0].current)
                break
    except Exception:
        pass

    # 2. Direct sysfs fallback if package_temp is still None
    if package_temp is None:
        try:
            for tz in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
                type_path = os.path.join(tz, "type")
                temp_path = os.path.join(tz, "temp")
                ztype = _safe_read_file(type_path).lower()
                if any(k in ztype for k in ["x86_pkg", "cpu", "acpitz", "soc"]):
                    raw = _safe_read_file(temp_path)
                    if raw and raw.isdigit():
                        val = int(raw) / 1000.0
                        if 10.0 <= val <= 125.0:
                            package_temp = val
                            break
        except Exception:
            pass

    return {
        "package": package_temp,
        "cores": core_temps,
    }


def get_gpu_info() -> Dict[str, Any]:
    """
    Multi-tier GPU reader:
    1. NVIDIA NVML (pynvml)
    2. AMD DRM sysfs & hwmon
    3. Intel i915/xe DRM sysfs
    4. Fallback: sysfs /proc/bus/pci / sensors
    """
    # 1. Try NVIDIA via NVML
    if _HAS_NVML:
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                
                temp = None
                try:
                    temp = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
                except Exception:
                    pass

                util = 0.0
                try:
                    rates = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    util = float(rates.gpu)
                except Exception:
                    pass

                vram_total = 0.0
                vram_used = 0.0
                try:
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    vram_total = round(mem.total / (1024 ** 2), 0)
                    vram_used = round(mem.used / (1024 ** 2), 0)
                except Exception:
                    pass

                return {
                    "vendor": "NVIDIA",
                    "model": name,
                    "temperature": temp,
                    "usage_percent": util,
                    "vram_total_mb": vram_total,
                    "vram_used_mb": vram_used,
                    "driver": "NVIDIA Proprietary",
                }
        except Exception:
            pass

    # 2. Try AMD / Intel via DRM Sysfs
    for card_path in sorted(glob.glob("/sys/class/drm/card[0-9]")):
        device_dir = os.path.join(card_path, "device")
        if not os.path.exists(device_dir):
            continue

        uevent = _safe_read_file(os.path.join(device_dir, "uevent"))
        driver_match = re.search(r"DRIVER=([a-zA-Z0-9_\-]+)", uevent)
        driver = driver_match.group(1) if driver_match else "drm"

        # Vendor determination
        vendor_id = _safe_read_file(os.path.join(device_dir, "vendor"))
        vendor = "Generic GPU"
        if "0x1002" in vendor_id:
            vendor = "AMD Radeon"
        elif "0x8086" in vendor_id:
            vendor = "Intel Graphics"
        elif "0x10de" in vendor_id:
            vendor = "NVIDIA"

        # Temperature from hwmon child
        gpu_temp = None
        for hwmon in glob.glob(os.path.join(device_dir, "hwmon", "hwmon*")):
            for t_file in glob.glob(os.path.join(hwmon, "temp*_input")):
                t_val = _safe_read_file(t_file)
                if t_val and t_val.isdigit():
                    v = int(t_val) / 1000.0
                    if 10.0 <= v <= 120.0:
                        gpu_temp = v
                        break

        # Usage %
        gpu_usage = 0.0
        busy_file = os.path.join(device_dir, "gpu_busy_percent")
        if os.path.exists(busy_file):
            b_val = _safe_read_file(busy_file)
            if b_val and b_val.isdigit():
                gpu_usage = float(b_val)

        # Model name resolution
        model_name = f"{vendor} ({driver})"
        if vendor == "Intel Graphics":
            model_name = "Intel HD/UHD Integrated Graphics"
        elif vendor == "AMD Radeon":
            model_name = "AMD Radeon Graphics"

        return {
            "vendor": vendor,
            "model": model_name,
            "temperature": gpu_temp,
            "usage_percent": gpu_usage,
            "vram_total_mb": 0.0,
            "vram_used_mb": 0.0,
            "driver": driver,
        }

    return {
        "vendor": "Standard",
        "model": "Generic Display Adapter",
        "temperature": None,
        "usage_percent": 0.0,
        "vram_total_mb": 0.0,
        "vram_used_mb": 0.0,
        "driver": "Generic",
    }


def get_disk_temperatures() -> Dict[str, Optional[float]]:
    """
    Collects temperatures for disks using psutil and sysfs hwmon nodes.
    """
    disk_temps: Dict[str, Optional[float]] = {}

    # 1. psutil sensors
    try:
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        for key, entries in temps.items():
            if "nvme" in key or "drivetemp" in key:
                for entry in entries:
                    if entry.current is not None:
                        disk_temps[key] = float(entry.current)
    except Exception:
        pass

    # 2. sysfs hwmon
    try:
        for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
            name = _safe_read_file(os.path.join(hwmon, "name"))
            if any(k in name.lower() for k in ["nvme", "drivetemp"]):
                for t_file in glob.glob(os.path.join(hwmon, "temp*_input")):
                    val_str = _safe_read_file(t_file)
                    if val_str and val_str.isdigit():
                        disk_temps[name] = int(val_str) / 1000.0
    except Exception:
        pass

    return disk_temps


@dataclass
class DiskDeviceSnapshot:
    name: str
    model: str
    size_gb: float
    mountpoint: str
    used_gb: float
    free_gb: float
    usage_percent: float
    read_speed_mbs: float = 0.0
    write_speed_mbs: float = 0.0
    temperature: Optional[float] = None


@dataclass
class HardwareSnapshot:
    # CPU
    cpu_model: str
    cpu_cores_physical: int
    cpu_cores_logical: int
    cpu_freq_mhz: float
    cpu_usage_percent: float
    cpu_package_temp: Optional[float]
    cpu_core_temps: List[float]
    
    # GPU
    gpu_vendor: str
    gpu_model: str
    gpu_usage_percent: float
    gpu_temp: Optional[float]
    gpu_vram_total_mb: float
    gpu_vram_used_mb: float
    gpu_driver: str

    # RAM & Swap
    ram_total_gb: float
    ram_used_gb: float
    ram_free_gb: float
    ram_usage_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_usage_percent: float

    # Disks
    disks: List[DiskDeviceSnapshot]

    # Motherboard & System
    mb_vendor: str
    mb_model: str
    mb_bios: str
    os_name: str
    kernel_version: str
    uptime_seconds: float
    timestamp: float = field(default_factory=time.time)


class HardwareEngine:
    """Core hardware inspection and sampling engine."""

    def __init__(self):
        self.cpu_model = get_cpu_model_name()
        self.cores_phys = psutil.cpu_count(logical=False) or 1
        self.cores_log = psutil.cpu_count(logical=True) or 1
        self.mb_info = get_motherboard_info()
        self.sys_info = get_system_overview()
        self.disk_models = self._discover_disk_models()

        self.last_io_time = time.time()
        self.last_io_counters = psutil.disk_io_counters(perdisk=True) or {}

    def _discover_disk_models(self) -> Dict[str, str]:
        models = {}
        for block_path in glob.glob("/sys/block/sd*") + glob.glob("/sys/block/nvme*"):
            dev_name = os.path.basename(block_path)
            model_file = os.path.join(block_path, "device", "model")
            model = _safe_read_file(model_file)
            if not model:
                model = _safe_read_file(os.path.join(block_path, "model"))
            models[dev_name] = model if model else "Solid State / Hard Disk Drive"
        return models

    def sample(self) -> HardwareSnapshot:
        now = time.time()
        dt = max(now - self.last_io_time, 0.001)

        # 1. CPU
        cpu_usage = psutil.cpu_percent(interval=None)
        freq_info = psutil.cpu_freq()
        cpu_freq = freq_info.current if freq_info else 0.0
        cpu_temps = get_cpu_temperatures()

        # 2. GPU
        gpu_data = get_gpu_info()

        # 3. RAM & Swap
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        ram_total = round(vm.total / (1024 ** 3), 2)
        ram_used = round(vm.used / (1024 ** 3), 2)
        ram_free = round(vm.available / (1024 ** 3), 2)
        swap_total = round(swap.total / (1024 ** 3), 2)
        swap_used = round(swap.used / (1024 ** 3), 2)

        # 4. Disks & IO Rates
        current_io = psutil.disk_io_counters(perdisk=True) or {}
        disk_temps = get_disk_temperatures()

        disks_snapshot: List[DiskDeviceSnapshot] = []
        partitions = psutil.disk_partitions(all=False)
        seen_devices = set()

        for p in partitions:
            if not p.device.startswith("/dev/"):
                continue
            if p.device in seen_devices:
                continue
            seen_devices.add(p.device)

            try:
                du = psutil.disk_usage(p.mountpoint)
                dev_base = os.path.basename(p.device)
                disk_base = re.sub(r"p?[0-9]+$", "", dev_base)
                model_name = self.disk_models.get(disk_base, self.disk_models.get(dev_base, "Storage Drive"))

                # IO Speeds
                read_speed = 0.0
                write_speed = 0.0
                if dev_base in current_io and dev_base in self.last_io_counters:
                    r_diff = current_io[dev_base].read_bytes - self.last_io_counters[dev_base].read_bytes
                    w_diff = current_io[dev_base].write_bytes - self.last_io_counters[dev_base].write_bytes
                    read_speed = round(max(r_diff, 0) / dt / (1024 * 1024), 1)
                    write_speed = round(max(w_diff, 0) / dt / (1024 * 1024), 1)
                elif disk_base in current_io and disk_base in self.last_io_counters:
                    r_diff = current_io[disk_base].read_bytes - self.last_io_counters[disk_base].read_bytes
                    w_diff = current_io[disk_base].write_bytes - self.last_io_counters[disk_base].write_bytes
                    read_speed = round(max(r_diff, 0) / dt / (1024 * 1024), 1)
                    write_speed = round(max(w_diff, 0) / dt / (1024 * 1024), 1)

                # Disk Temp
                d_temp = None
                for k, tval in disk_temps.items():
                    if disk_base in k or dev_base in k:
                        d_temp = tval
                        break
                if d_temp is None and disk_temps:
                    d_temp = next(iter(disk_temps.values()))

                disks_snapshot.append(
                    DiskDeviceSnapshot(
                        name=dev_base,
                        model=model_name,
                        size_gb=round(du.total / (1024 ** 3), 1),
                        mountpoint=p.mountpoint,
                        used_gb=round(du.used / (1024 ** 3), 1),
                        free_gb=round(du.free / (1024 ** 3), 1),
                        usage_percent=du.percent,
                        read_speed_mbs=read_speed,
                        write_speed_mbs=write_speed,
                        temperature=d_temp,
                    )
                )
            except Exception:
                continue

        # If no mounted partitions found under /dev, list physical disks directly
        if not disks_snapshot:
            for d_name, d_model in self.disk_models.items():
                disks_snapshot.append(
                    DiskDeviceSnapshot(
                        name=d_name,
                        model=d_model,
                        size_gb=0.0,
                        mountpoint="/",
                        used_gb=0.0,
                        free_gb=0.0,
                        usage_percent=0.0,
                        temperature=disk_temps.get(d_name),
                    )
                )

        self.last_io_counters = current_io
        self.last_io_time = now

        uptime = now - psutil.boot_time()

        return HardwareSnapshot(
            cpu_model=self.cpu_model,
            cpu_cores_physical=self.cores_phys,
            cpu_cores_logical=self.cores_log,
            cpu_freq_mhz=cpu_freq,
            cpu_usage_percent=cpu_usage,
            cpu_package_temp=cpu_temps["package"],
            cpu_core_temps=cpu_temps["cores"],
            gpu_vendor=gpu_data["vendor"],
            gpu_model=gpu_data["model"],
            gpu_usage_percent=gpu_data["usage_percent"],
            gpu_temp=gpu_data["temperature"],
            gpu_vram_total_mb=gpu_data["vram_total_mb"],
            gpu_vram_used_mb=gpu_data["vram_used_mb"],
            gpu_driver=gpu_data["driver"],
            ram_total_gb=ram_total,
            ram_used_gb=ram_used,
            ram_free_gb=ram_free,
            ram_usage_percent=vm.percent,
            swap_total_gb=swap_total,
            swap_used_gb=swap_used,
            swap_usage_percent=swap.percent,
            disks=disks_snapshot,
            mb_vendor=self.mb_info["vendor"],
            mb_model=self.mb_info["model"],
            mb_bios=self.mb_info["bios_version"],
            os_name=self.sys_info["os_name"],
            kernel_version=self.sys_info["kernel"],
            uptime_seconds=uptime,
            timestamp=now,
        )
