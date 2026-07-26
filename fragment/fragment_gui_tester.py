import json
import subprocess
import time
import csv
import os
import requests
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox

# --- تنظیمات ثابت ---
XRAY_PATH = "./xray"
BASE_CONFIG_FILE = "base_config.json"
TEST_URL = "https://www.google.com"
# ---------------------

# پارامترهای تست (پیش‌فرض‌های ریپو)
DEFAULT_FRAG_LENGTHS = "20-40,50-100,150-200"
DEFAULT_FRAG_INTERVALS = "1-20,20-50,50-100"

def load_base_config():
    """فایل کانفیگ پایه را بارگذاری می‌کند."""
    if not os.path.exists(BASE_CONFIG_FILE):
        messagebox.showerror("خطا", f"فایل کانفیگ پایه پیدا نشد: {BASE_CONFIG_FILE}")
        return None
    with open(BASE_CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_vless_info(config, user_params):
    """اطلاعات VLESS را به‌روز می‌کند و Stream را به TCP تغییر می‌دهد."""
    vless_outbound = next((item for item in config["outbounds"] if item.get("tag") == "fakeproxy-out"), None)
    if vless_outbound:
        vnext = vless_outbound["settings"]["vnext"][0]
        vnext["address"] = user_params['vless_addr']
        vnext["port"] = int(user_params['vless_port'])
        vnext["users"][0]["id"] = user_params['vless_uuid']
        vless_outbound["streamSettings"]["tlsSettings"]["serverName"] = user_params['vless_domain']
        
        # 🚨 تغییر کلیدی: تغییر Stream از WS به TCP برای اعمال Fragment
        vless_outbound["streamSettings"]["network"] = "tcp"
        if "wsSettings" in vless_outbound["streamSettings"]:
            del vless_outbound["streamSettings"]["wsSettings"]
            
        if "tcpSettings" not in vless_outbound["streamSettings"]:
            vless_outbound["streamSettings"]["tcpSettings"] = {"connectionReuse": True, "tcp": {}}
            
    # به‌روزرسانی Routing برای هدایت ترافیک به VLESS (fakeproxy-out)
    frag_rule = next((rule for rule in config["routing"]["rules"] if rule.get("port") == "0-65535"), None)
    if frag_rule:
        frag_rule["outboundTag"] = user_params['frag_outbound_tag']

    return config

def run_test_backend(config_path, test_url):
    """Xray را اجرا کرده و اتصال را تست می‌کند (بدون GUI)."""
    xray_process = subprocess.Popen([XRAY_PATH, "-c", config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5) 

    start_time = time.time()
    try:
        response = requests.get(test_url, proxies={"socks5": "127.0.0.1:10808"}, timeout=15)
        
        if response.status_code == 200:
            downloaded_bytes = len(response.content)
            elapsed_time = time.time() - start_time
            speed_mbps = (downloaded_bytes * 8) / (elapsed_time * 1024 * 1024) if elapsed_time > 0 else 0
            latency = int((time.time() - start_time) * 1000)
            result = {"Success": "Yes", "Speed_Mbps": f"{speed_mbps:.2f}", "Latency_ms": latency}
        else:
            result = {"Success": "No (HTTP Error)", "Speed_Mbps": 0, "Latency_ms": 0}

    except requests.exceptions.RequestException:
        result = {"Success": "No (Timeout/Refused)", "Speed_Mbps": 0, "Latency_ms": 0}
    finally:
        xray_process.terminate()
        xray_process.wait()
        time.sleep(2)

    return result

def start_testing(params):
    """منطق اصلی تست را اجرا می‌کند و نتایج را تحلیل می‌کند."""
    
    # 1. به‌روزرسانی کانفیگ پایه با ورودی‌های کاربر
    base_config = load_base_config()
    if not base_config:
        messagebox.showerror("خطا", "Base config loading failed.")
        return

    final_base_config = update_vless_info(base_config, params)
    
    FRAGMENT_LENGTHS = [l.strip() for l in params['frag_lengths_str'].split(',')]
    FRAGMENT_INTERVALS = [i.strip() for i in params['frag_intervals_str'].split(',')]
    
    results = []
    
    # --- تست Baseline (بدون Fragment) ---
    print("\n--- تست Baseline (بدون Fragment) ---")
    temp_config_base = final_base_config.copy()
    if "fragment" in temp_config_base["outbounds"][0]["settings"]:
        del temp_config_base["outbounds"][0]["settings"]["fragment"]
        
    config_path_base = "temp_base_config.json"
    with open(config_path_base, 'w') as f:
        json.dump(temp_config_base, f, indent=4)
        
    res = run_test_backend(config_path_base, params['test_url'])
    os.remove(config_path_base)
    
    base_result = {
        "Length": "Baseline", "Interval": "None", "Success": res["Success"], 
        "Speed_Mbps": res["Speed_Mbps"], "Latency_ms": res["Latency_ms"],
        "DNS_URL": params['dns_server'], "Test_Website": params['test_url'], "BEST_RESULT": "No"
    }
    results.append(base_result)
    print(f"Baseline Test: Status={res['Success']}, Speed={res['Speed_Mbps']} Mbps")

    # --- تست Grid Search ---
    for length in FRAGMENT_LENGTHS:
        for interval in FRAGMENT_INTERVALS:
            print(f"\n--- تست: Length={length}, Interval={interval} ---")
            
            temp_config = final_base_config.copy()
            
            vless_outbound = next((item for item in temp_config["outbounds"] if item.get("tag") == "fakeproxy-out"), None)
            
            if vless_outbound:
                 vless_outbound["settings"]["fragment"] = {
                    "packets": "tlshello", 
                    "length": length,
                    "interval": interval
                }
            else:
                messagebox.showerror("خطا", "VLESS Outbound not found!")
                return
            
            config_path = f"temp_config_{length.replace('-', '_')}_{interval.replace('-', '_')}.json"
            with open(config_path, 'w') as f:
                json.dump(temp_config, f, indent=4)
            
            res = run_test_backend(config_path, params['test_url'])
            os.remove(config_path)
            
            result = {
                "Length": length, "Interval": interval, "Success": res["Success"], 
                "Speed_Mbps": res["Speed_Mbps"], "Latency_ms": res["Latency_ms"],
                "DNS_URL": params['dns_server'], "Test_Website": params['test_url'], "BEST_RESULT": "No"
            }
            results.append(result)
            print(f"Result: Status={res['Success']}, Speed={res['Speed_Mbps']} Mbps")
            time.sleep(3) 

    # --- تحلیل نتایج و ذخیره بهترین کانفیگ ---
    df = pd.DataFrame(results)
    successful_tests = df[df['Success'] == 'Yes'].copy()
    
    if not successful_tests.empty:
        successful_tests['Speed_Numeric'] = pd.to_numeric(successful_tests['Speed_Mbps'], errors='coerce').fillna(0)
        best_row_index = successful_tests['Speed_Numeric'].idxmax()
        best_result = df.loc[best_row_index]
        
        df.loc[best_row_index, 'BEST_RESULT'] = 'Yes'
        
        # ساخت فایل کانفیگ نهایی
        final_config = final_base_config.copy()
        vless_outbound = next((item for item in final_config["outbounds"] if item.get("tag") == "fakeproxy-out"), None)
        if vless_outbound:
            vless_outbound["settings"]["fragment"] = {
                "packets": "tlshello", 
                "length": best_result['Length'],
                "interval": best_result['Interval']
            }
        
        best_config_path = "BEST-CONFIG.json"
        with open(best_config_path, 'w') as f:
            json.dump(final_config, f, indent=4)
        messagebox.showinfo("پایان", f"تست‌ها کامل شد. بهترین کانفیگ در {best_config_path} ذخیره شد.")
        
    else:
        messagebox.showwarning("پایان", "هیچکدام از ترکیب‌های Fragment موفق به برقراری اتصال نشدند.")

    # ذخیره نتایج در CSV
    output_file = "fragment_test_results.csv"
    df.to_csv(output_file, index=False)
    messagebox.showinfo("پایان", f"نتایج کامل تست‌ها در فایل {output_file} ذخیره شد.")


# --- GUI Interface ---
class FragmentTesterApp:
    def __init__(self, master):
        self.master = master
        master.title("Xray Fragment Tester (Linux Clone)")
        
        self.params = {}

        # --- تنظیمات VLESS ---
        frame_vless = ttk.LabelFrame(master, text="VLESS Connection Settings")
        frame_vless.pack(padx=10, pady=5, fill="x")
        
        self.entries_vless = {
            'vless_addr': tk.StringVar(value="google.com"),
            'vless_port': tk.StringVar(value="443"),
            'vless_uuid': tk.StringVar(value="UUID"),
            'vless_domain': tk.StringVar(value="google.com"),
        }
        
        self.create_entries(frame_vless, self.entries_vless, ["Server Address", "Port", "UUID", "SNI Domain"])

        # --- تنظیمات تست و کانفیگ ---
        frame_test = ttk.LabelFrame(master, text="Test & Config Parameters")
        frame_test.pack(padx=10, pady=5, fill="x")
        
        self.entries_test = {
            'socks_port': tk.StringVar(value="10808"),
            'http_port': tk.StringVar(value="10809"),
            'dns_server': tk.StringVar(value="https://cloudflare-dns.com/dns-query"),
            'dns_outbound_tag': tk.StringVar(value="dns-out"),
            'frag_outbound_tag': tk.StringVar(value="fakeproxy-out"),
            'test_url': tk.StringVar(value="https://www.google.com"),
            'frag_lengths_str': tk.StringVar(value=DEFAULT_FRAG_LENGTHS),
            'frag_intervals_str': tk.StringVar(value=DEFAULT_FRAG_INTERVALS),
        }
        
        self.create_entries(frame_test, self.entries_test, 
                            ["SOCKS Port", "HTTP Port", "DNS Server URL", "DNS Outbound Tag", 
                             "Fragment Outbound Tag", "Test URL", "Fragment Lengths (Comma Separated)", 
                             "Fragment Intervals (Comma Separated)"])

        # --- دکمه شروع ---
        ttk.Button(master, text="Start Testing", command=self.collect_and_start).pack(pady=10)

    def create_entries(self, frame, entry_vars, labels):
        for i, label_text in enumerate(labels):
            row = i % 2
            col = i // 2
            
            ttk.Label(frame, text=label_text + ":").grid(row=row, column=col*2, sticky="w", padx=5, pady=2)
            
            entry = ttk.Entry(frame, textvariable=entry_vars[list(entry_vars.keys())[i]], width=40)
            entry.grid(row=row, column=col*2 + 1, sticky="ew", padx=5, pady=2)
            frame.grid_columnconfigure(col*2 + 1, weight=1)

    def collect_and_start(self):
        if not os.path.exists(XRAY_PATH):
            messagebox.showerror("خطا", f"Xray Core not found at: {XRAY_PATH}")
            return
            
        # جمع‌آوری پارامترها
        params = {}
        for key, var in self.entries_vless.items():
            params[key] = var.get()
        for key, var in self.entries_test.items():
            params[key] = var.get()

        # اعتبارسنجی اولیه
        if not all([params['vless_addr'], params['vless_uuid'], params['test_url']]):
            messagebox.showwarning("ورودی ناقص", "لطفاً آدرس سرور، UUID و URL تست را وارد کنید.")
            return
            
        # بستن پنجره GUI و شروع تست در پس‌زمینه
        self.master.destroy()
        
        # اجرای منطق تست در تابع اصلی
        start_testing(params)


if __name__ == "__main__":
    root = tk.Tk()
    app = FragmentTesterApp(root)
    root.mainloop()

