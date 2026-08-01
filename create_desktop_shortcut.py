import os
from win32com.client import Dispatch

def create_shortcuts():
    desktop_paths = [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop")
    ]
    
    target_bat = r"D:\godji\Launch_AI_Godji.bat"
    
    shell = Dispatch('WScript.Shell')
    for d_path in desktop_paths:
        if os.path.exists(d_path):
            lnk_path = os.path.join(d_path, "AI Godji.lnk")
            shortcut = shell.CreateShortCut(lnk_path)
            shortcut.Targetpath = target_bat
            shortcut.WorkingDirectory = r"D:\godji"
            shortcut.Description = "AI Godji One-Click Master Launcher"
            shortcut.save()
            print(f"Successfully created shortcut at: {lnk_path}")

if __name__ == "__main__":
    create_shortcuts()
