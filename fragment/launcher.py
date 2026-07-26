"""
Project: Xray Fragment Tester - Linux Native Version
Original Author: github.com/sasanxxx
Linux Port: Optimized for Fedora 44 & General Linux Distributions
"""
import tkinter as tk
from tkinter import messagebox, font, filedialog
import json
import subprocess
import os
import platform
import sys
from core import generate_config

BEST_RESULT_FILENAME = "best_result.json"

DEFAULT_PARAMS = {
    "fragment_length": "5-10, 20-40",
    "fragment_interval": "10-20, 20-30",
    "server_name": "www.google.com, www.microsoft.com",
    "dns_server_url": "https://dns.google/dns-query, https://cloudflare-dns.com/dns-query",
    "websites_to_test": "https://www.google.com, https://www.youtube.com"
}

def get_params_from_gui(single_values=False):
    params = {}
    for key, entry in entries.items():
        value = entry.get().strip()
        if not value:
            raise ValueError(f"Field '{labels[key]}' cannot be empty.")
        if not single_values:
            params[key] = [s.strip() for s in value.split(',')]
        else:
            params[key] = value.split(',')[0].strip()
    return params

def get_python_command():
    """تشخیص دستور صحیح پایتون بر اساس سیستم‌عامل"""
    if platform.system() == "Windows":
        return "python"
    else:
        return "python3"

def get_terminal_command():
    """تشخیص ترمینال پیش‌فرض سیستم (بهینه‌شده برای فدورا و سایر توزیع‌ها)"""
    if platform.system() == "Windows":
        return ["cmd", "/k"]
    
    # لیست ترمینال‌های رایج لینوکس به ترتیب اولویت
    terminals = [
        (["gnome-terminal", "--"], "GNOME Terminal"),      # پیش‌فرض فدورا و اوبونتو
        (["konsole", "-e"], "KDE Konsole"),                # پیش‌فرض KDE Plasma
        (["xfce4-terminal", "-x"], "XFCE Terminal"),       # پیش‌فرض XFCE
        (["mate-terminal", "-x"], "MATE Terminal"),        # پیش‌فرض MATE
        (["lxterminal", "-e"], "LXTerminal"),              # پیش‌فرض LXDE/LXQt
        (["alacritty", "-e"], "Alacritty"),                # ترمینال مدرن
        (["kitty"], "Kitty")                               # ترمینال مدرن
    ]
    
    for cmd, name in terminals:
        try:
            # بررسی وجود دستور در سیستم
            subprocess.run(["which", cmd[0]], capture_output=True, check=True)
            print(f"✓ Detected terminal: {name}")
            return cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # اگر هیچ ترمینالی پیدا نشد، None برمی‌گردانیم تا برنامه کرش نکند
    print("⚠ Warning: No dedicated terminal emulator found. Will run in background.")
    return None

def start_test():
    try:
        params_to_save = get_params_from_gui()
        with open("params.json", "w", encoding='utf-8') as f:
            json.dump(params_to_save, f, indent=2)
        
        # استفاده از مسیر مطلق برای جلوگیری از خطاهای یافت نشدن فایل
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "A.py")
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Main script file 'A.py' not found at:\n{script_path}")
            return
        
        python_cmd = get_python_command()
        terminal_cmd = get_terminal_command()
        
        if platform.system() == "Windows":
            full_command = terminal_cmd + [python_cmd, f'"{script_path}"']
            subprocess.Popen(full_command, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            if terminal_cmd:
                # اگر ترمینال پیدا شد، در پنجره جدید باز کن
                full_command = terminal_cmd + [python_cmd, script_path]
                subprocess.Popen(full_command)
                print("✓ Test started in a new terminal window.")
            else:
                # اگر ترمینال پیدا نشد، در پس‌زمینه اجرا کن (جلوگیری از خطای xterm)
                subprocess.Popen([python_cmd, script_path])
                print("✓ Test started in the background (no terminal found).")
                messagebox.showinfo(
                    "Info", 
                    "Test started in the background.\nPlease check the console/terminal where you launched this app for output."
                )
                
    except Exception as e:
        messagebox.showerror("Error", str(e))

def generate_config_from_params(params: dict):
    try:
        base_config_filename = "Xray_Config (Fragment).json"
        
        if not os.path.exists(base_config_filename):
            messagebox.showerror(
                "Error", 
                f"Base config file '{base_config_filename}' not found.\n\n"
                f"Please create this file in:\n{os.getcwd()}"
            )
            return
        
        with open(base_config_filename, "r", encoding='utf-8') as f:
            base_config = json.load(f)
            
        final_config = generate_config(base_config, params)
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Config As...",
            initialfile="generated_config.json",
            initialdir=os.getcwd()
        )
        
        if file_path:
            with open(file_path, "w", encoding='utf-8') as f:
                # ensure_ascii=False برای پشتیبانی صحیح از کاراکترهای فارسی/یونیکد
                json.dump(final_config, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Configuration file saved successfully to:\n{file_path}")
            
    except json.JSONDecodeError as e:
        messagebox.showerror("Error", f"Invalid JSON in base config file:\n{str(e)}")
    except FileNotFoundError:
        messagebox.showerror("Error", f"Base config file '{base_config_filename}' not found.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def generate_manual_config():
    try:
        params = get_params_from_gui(single_values=True)
        generate_config_from_params(params)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def generate_best_config():
    try:
        if not os.path.exists(BEST_RESULT_FILENAME):
            messagebox.showerror(
                "Error", 
                f"Best result file '{BEST_RESULT_FILENAME}' not found.\n\n"
                f"Please run a test first using the 'Start Test' button."
            )
            return
        
        with open(BEST_RESULT_FILENAME, 'r', encoding='utf-8') as f:
            best_params = json.load(f)
        
        if "websites_to_test" not in best_params:
             best_params["websites_to_test"] = "https://www.google.com"
        
        generate_config_from_params(best_params)

    except json.JSONDecodeError as e:
        messagebox.showerror("Error", f"Invalid JSON in best result file:\n{str(e)}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# --- GUI Setup ---
window = tk.Tk()
window.title("Xray Fragment Tester - Linux Edition")
window.geometry("650x340")
window.resizable(False, False)

# تلاش برای بارگذاری آیکون (اختیاری)
try:
    if os.path.exists("icon.png"):
        window.iconphoto(False, tk.PhotoImage(file="icon.png"))
except Exception:
    pass

form_frame = tk.Frame(window, padx=10, pady=10)
form_frame.pack(fill="x", expand=True)

entries = {}
labels = {
    "fragment_length": "Fragment Length",
    "fragment_interval": "Fragment Interval",
    "server_name": "Server Name",
    "dns_server_url": "DNS Server URL",
    "websites_to_test": "Websites to Test"
}

# بارگذاری پارامترهای قبلی
try:
    best_params = {}
    if os.path.exists(BEST_RESULT_FILENAME):
        with open(BEST_RESULT_FILENAME, 'r', encoding='utf-8') as f:
            best_params = json.load(f)
    
    if os.path.exists("params.json"):
        with open("params.json", 'r', encoding='utf-8') as f:
            last_params = json.load(f)
        if isinstance(last_params.get("websites_to_test"), list):
            best_params["websites_to_test"] = ", ".join(last_params["websites_to_test"])
        else:
            best_params["websites_to_test"] = str(last_params.get("websites_to_test", ""))
            
except Exception as e:
    print(f"Warning: Could not load previous parameters: {e}")
    best_params = {}

# ساخت فرم
for i, (key, text) in enumerate(labels.items()):
    label = tk.Label(form_frame, text=text, anchor="w", font=("Arial", 9))
    label.grid(row=i, column=0, sticky="w", padx=5, pady=5)
    
    entry = tk.Entry(form_frame, width=60, font=("Arial", 9))
    entry.grid(row=i, column=1, sticky="ew", padx=5, pady=5)
    
    # مقدار پیش‌فرض
    default_value = ""
    if best_params and key in best_params:
        value = best_params[key]
        if isinstance(value, list):
            default_value = ", ".join(value)
        else:
            default_value = str(value)
    elif key in DEFAULT_PARAMS:
        default_value = DEFAULT_PARAMS[key]
        
    entry.insert(0, default_value)
    entries[key] = entry

form_frame.grid_columnconfigure(1, weight=1)

# دکمه‌ها
button_frame = tk.Frame(window)
button_frame.pack(pady=10)

start_button = tk.Button(
    button_frame, 
    text="▶ Start Test", 
    command=start_test, 
    bg="#28a745", 
    fg="white", 
    font=("Arial", 10, "bold"), 
    width=20,
    cursor="hand2"
)
start_button.pack(side="left", padx=5)

generate_manual_button = tk.Button(
    button_frame, 
    text="📝 Generate From Fields", 
    command=generate_manual_config, 
    bg="#007bff", 
    fg="white", 
    font=("Arial", 10, "bold"), 
    width=20,
    cursor="hand2"
)
generate_manual_button.pack(side="left", padx=5)

generate_best_button = tk.Button(
    button_frame, 
    text="⭐ Generate Best Config", 
    command=generate_best_config, 
    bg="#ffc107", 
    fg="black", 
    font=("Arial", 10, "bold"), 
    width=20,
    cursor="hand2"
)
generate_best_button.pack(side="left", padx=5)

# شعار
slogan_font = font.Font(family="Consolas", size=9, slant="italic")
slogan_label = tk.Label(
    window, 
    text="...because we can! | Linux Native Edition (Fedora Optimized)", 
    font=slogan_font, 
    fg="#555555"
)
slogan_label.pack(pady=5)

# نمایش اطلاعات سیستم در کنسول هنگام اجرا
print("=" * 60)
print(" Xray Fragment Tester - Linux Edition")
print("=" * 60)
print(f" Python Version : {sys.version.split()[0]}")
print(f" Platform       : {platform.system()} {platform.release()}")
print(f" Working Dir    : {os.getcwd()}")
print("=" * 60)

window.mainloop()
