import os
import sys
import shutil
import configparser
from datetime import datetime

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def settings_path():
    return os.path.join(app_dir(), "settings.ini")

class Settings:
    DEFAULTS = {"window_width": 1200, "window_height": 780, "window_x": -1, "window_y": -1, "last_model_path": ""}
    
    def __init__(self):
        self._parser = configparser.ConfigParser()
        path = settings_path()
        if os.path.exists(path):
            try: self._parser.read(path)
            except Exception: pass
            
    def get_int(self, key, default=None):
        try: return self._parser.getint("settings", key)
        except Exception: return default if default is not None else self.DEFAULTS.get(key, 0)
        
    def set_int(self, key, value):
        if not self._parser.has_section("settings"): self._parser.add_section("settings")
        self._parser.set("settings", key, str(value))
        
    def get_str(self, key, default=""):
        try: return self._parser.get("settings", key)
        except Exception: return default if default is not None else self.DEFAULTS.get(key, "")
        
    def set_str(self, key, value):
        if not self._parser.has_section("settings"): self._parser.add_section("settings")
        self._parser.set("settings", key, str(value))
        
    def save(self):
        try:
            with open(settings_path(), "w", encoding="utf-8") as f: self._parser.write(f)
        except Exception: pass

def backups_dir():
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(appdata, "DER Analyzer", "backups")
    os.makedirs(path, exist_ok=True)
    return path

class BackupManager:
    MAX_BACKUPS = 3
    def create_backup(self, tmodel_path):
        if not os.path.exists(tmodel_path): return None
        base = os.path.splitext(os.path.basename(tmodel_path))[0]
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target = os.path.join(backups_dir(), f"{base}_{stamp}.tmodel")
        shutil.copy2(tmodel_path, target)
        self._prune(base)
        return target
    def _prune(self, base):
        folder = backups_dir()
        files = sorted((f for f in os.listdir(folder) if f.startswith(base + "_") and f.endswith(".tmodel")), reverse=True)
        for f in files[self.MAX_BACKUPS:]:
            try: os.remove(os.path.join(folder, f))
            except Exception: pass
    def list_backups(self, base):
        folder = backups_dir()
        files = sorted((f for f in os.listdir(folder) if f.startswith(base + "_") and f.endswith(".tmodel")), reverse=True)
        result = []
        for f in files:
            full = os.path.join(folder, f)
            try: size = os.path.getsize(full)
            except Exception: size = 0
            result.append({"name": f, "path": full, "size": size})
        return result
