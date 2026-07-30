"""System information — OS version, hostname, uptime, memory, CPU."""

import platform
import socket

from .exceptions import SystemInfoError


class SystemInfoService:
    def get_system_info(self) -> dict:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot_time = psutil.boot_time()
            import datetime as dt
            uptime_seconds = (dt.datetime.now() - dt.datetime.fromtimestamp(boot_time)).total_seconds()
            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "os_release": platform.release(),
                "hostname": socket.gethostname(),
                "username": self._get_username(),
                "cpu": str(cpu_count),
                "cpu_percent": cpu_percent,
                "ram_total_gb": round(memory.total / (1024**3), 1),
                "ram_used_gb": round(memory.used / (1024**3), 1),
                "ram_percent": memory.percent,
                "ram_available_gb": round(memory.available / (1024**3), 1),
                "disk_total_gb": round(disk.total / (1024**3), 1),
                "disk_used_gb": round(disk.used / (1024**3), 1),
                "disk_free_gb": round(disk.free / (1024**3), 1),
                "disk_percent": disk.percent,
                "uptime_seconds": int(uptime_seconds),
                "architecture": platform.machine(),
                "processor": platform.processor(),
            }
        except ImportError:
            raise SystemInfoError("psutil is not installed")
        except Exception as e:
            raise SystemInfoError(f"Failed to get system info: {e}")

    def get_disk_usage(self) -> list[dict]:
        try:
            import psutil
            disks = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent": usage.percent,
                    })
                except PermissionError:
                    continue
            return disks
        except ImportError:
            raise SystemInfoError("psutil is not installed")
        except Exception as e:
            raise SystemInfoError(f"Failed to get disk usage: {e}")

    def get_network_info(self) -> dict:
        try:
            import psutil
            net = psutil.net_io_counters()
            addrs = psutil.net_if_addrs()
            interfaces = []
            for name, addr_list in addrs.items():
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        interfaces.append({
                            "name": name,
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast,
                        })
            return {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "interfaces": interfaces,
            }
        except ImportError:
            raise SystemInfoError("psutil is not installed")
        except Exception as e:
            raise SystemInfoError(f"Failed to get network info: {e}")

    def _get_username(self) -> str:
        try:
            import os
            return os.environ.get("USERNAME") or os.environ.get("USER") or ""
        except Exception:
            return ""
