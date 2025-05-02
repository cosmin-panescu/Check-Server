import requests
import time
import pandas as pd
import concurrent.futures
import os
from urllib3.exceptions import InsecureRequestWarning
from email_alert import email_alert
import json

# dezactivare avertizari SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class SiteMonitor:
    def __init__(self, input_file=None, check_interval=5, timeout=10, email_notification=True, email_to=None):
        self.sites = []
        self.check_interval = check_interval
        self.timeout = timeout
        self.email_notification = email_notification
        
        if email_to is None:
            # preluare email din configurare
            config = load_config()
            self.email_to = config.get("email_to", "1panescu.cosmin@gmail.com")
        else:
            self.email_to = email_to
        
        if input_file:
            self.load_sites_from_file(input_file)
    
    def load_sites_from_file(self, input_file):
        try:
            if input_file.endswith('.csv'):
                df = pd.read_csv(input_file)
                
                # verificare coloane disponibile in fisier
                if 'domain' in df.columns or 'Domain' in df.columns:
                    domain_col = 'domain' if 'domain' in df.columns else 'Domain'
                    domains = df[domain_col].tolist()
                    self.sites = [{'domain': domain, 'ip': None} for domain in domains]
                elif 'ip' in df.columns or 'IP' in df.columns:
                    ip_col = 'ip' if 'ip' in df.columns else 'IP'
                    ips = df[ip_col].tolist()
                    self.sites = [{'domain': None, 'ip': ip} for ip in ips]
                elif 'site' in df.columns or 'Site' in df.columns:
                    site_col = 'site' if 'site' in df.columns else 'Site'
                    sites = df[site_col].tolist()
                    self.sites = [{'domain': site, 'ip': None} for site in sites]
                else:
                    first_col = df.columns[0]
                    values = df[first_col].tolist()
                    self.sites = [{'domain': value, 'ip': None} for value in values]
            
            elif input_file.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(input_file)
                
                if 'domain' in df.columns or 'Domain' in df.columns:
                    domain_col = 'domain' if 'domain' in df.columns else 'Domain'
                    domains = df[domain_col].tolist()
                    self.sites = [{'domain': domain, 'ip': None} for domain in domains]
                elif 'ip' in df.columns or 'IP' in df.columns:
                    ip_col = 'ip' if 'ip' in df.columns else 'IP'
                    ips = df[ip_col].tolist()
                    self.sites = [{'domain': None, 'ip': ip} for ip in ips]
                elif 'site' in df.columns or 'Site' in df.columns:
                    site_col = 'site' if 'site' in df.columns else 'Site'
                    sites = df[site_col].tolist()
                    self.sites = [{'domain': site, 'ip': None} for site in sites]
                else:
                    first_col = df.columns[0]
                    values = df[first_col].tolist()
                    self.sites = [{'domain': value, 'ip': None} for value in values]
                    
            elif input_file.endswith('.txt'):
                with open(input_file, 'r') as file:
                    domains = [line.strip() for line in file if line.strip()]
                self.sites = [{'domain': domain, 'ip': None} for domain in domains]
            
            else:
                raise ValueError("Formatul fisierului nu este suportat. Foloseste CSV, Excel sau TXT.")
                
            print(f"S-au incarcat {len(self.sites)} site-uri din fisierul {input_file}")
        except Exception as e:
            print(f"Eroare la incarcarea fisierului: {e}")
            raise
    
    def check_site(self, site):
        url = site['domain']
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=self.timeout, verify=False)
            response_time = time.time() - start_time
            
            if response.status_code < 400:
                return {
                    'site': site['domain'] or site['ip'],
                    'status': 'UP',
                    'response_time': round(response_time, 2),
                    'status_code': response.status_code
                }
            else:
                return {
                    'site': site['domain'] or site['ip'],
                    'status': 'DOWN',
                    'response_time': round(response_time, 2),
                    'status_code': response.status_code,
                    'error': f"HTTP Error: {response.status_code}"
                }
        except requests.exceptions.ConnectionError:
            return {
                'site': site['domain'] or site['ip'],
                'status': 'DOWN',
                'error': "Eroare de conexiune"
            }
        except requests.exceptions.Timeout:
            return {
                'site': site['domain'] or site['ip'],
                'status': 'DOWN',
                'error': "Timeout"
            }
        except Exception as e:
            return {
                'site': site['domain'] or site['ip'],
                'status': 'DOWN',
                'error': str(e)
            }
    
    def check_all_sites(self):
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_site = {executor.submit(self.check_site, site): site for site in self.sites}
            for future in concurrent.futures.as_completed(future_to_site):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    site = future_to_site[future]
                    print(f"Eroare la verificarea site-ului {site['domain'] or site['ip']}: {e}")
        
        return results
    
    def display_status(self, results, email_notification=None):
        if email_notification is None:
            email_notification = self.email_notification
        
        down_sites = [r for r in results if r['status'] == 'DOWN']
        
        if down_sites:
            print("\n--- SITE-URI INDISPONIBILE ---")
            down_sites_text = ""
            for site in down_sites:
                site_info = f"❌ {site['site']}: {site.get('error', 'Eroare necunoscuta')}"
                print(site_info)
                down_sites_text += site_info + "\n"
            
            # alerta prin email
            if email_notification and down_sites_text:
                subject = f"ALERTA: {len(down_sites)} site-uri indisponibile"
                body = f"Urmatoarele site-uri sunt indisponibile:\n\n{down_sites_text}\n"
                body += f"\nStatusul verificarii: {len(results) - len(down_sites)} site-uri online, {len(down_sites)} site-uri offline"
                
                try:
                    email_alert(subject, body, self.email_to)
                    print(f"✉️  Email trimis la {self.email_to}")
                except Exception as e:
                    print(f"❌ Eroare la trimiterea email-ului: {e}")

    def start_monitoring(self):
        print(f"Monitorizarea a inceput pentru {len(self.sites)} site-uri")
        print(f"Verificare la fiecare {self.check_interval} secunde")
        if self.email_notification:
            print(f"Alertele prin email sunt ACTIVATE si vor fi trimise la: {self.email_to}")
        else:
            print("Alertele prin email sunt DEZACTIVATE")
        print("Apasa Ctrl+C pentru a opri monitorizarea")
        print("-" * 50)
        
        # evidenta pentru site-urile offline anterior
        previous_down_sites = set()
        
        try:
            while True:
                results = self.check_all_sites()
                
                # determinare site-uri offline curente
                current_down_sites = set(r['site'] for r in results if r['status'] == 'DOWN')

                # determinare site-uri noi care au picat                
                new_down_sites = current_down_sites - previous_down_sites
                
                # filtrare doar site-uri noi care au picat
                if new_down_sites:
                    new_down_results = [r for r in results if r['status'] == 'DOWN' and r['site'] in new_down_sites]
                    self.display_status(new_down_results, self.email_notification)
                else:
                    # afisare status curent pt. toate site-urile
                    self.display_status(results, False)
                
                # actualizare lista site-uri offline
                previous_down_sites = current_down_sites
                
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\nMonitorizarea a fost oprita")

def get_available_files():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(current_dir)
    csv_files = [f for f in files if f.endswith('.csv')]
    excel_files = [f for f in files if f.endswith(('.xlsx', '.xls'))]
    txt_files = [f for f in files if f.endswith('.txt')]
    
    return csv_files, excel_files, txt_files

def load_config(file_name="default_config.json"):
    default_config = {
        "input_file": "site.txt",
        "check_interval": 5,
        "timeout": 10,
        "email_notification": True,
        "email_to": "1panescu.cosmin@gmail.com"
    }
    
    try:
        with open(file_name, "r") as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print(f"ℹ️ Nu a fost gasit fisierul {file_name}. Se vor folosi valorile implicite")
        return default_config
    except json.JSONDecodeError:
        print(f"⚠️ Eroare la citirea fisierului {file_name}. Se vor folosi valorile implicite")
        return default_config
    except Exception as e:
        print(f"⚠️ Eroare: {e}. Se vor folosi valorile implicite")
        return default_config

def save_config(config_data, file_name="default_config.json"):
    try:
        with open(file_name, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
        print(f"✅ Configurarile au fost salvate în {file_name}")
        return True
    except Exception as e:
        print(f"❌ Eroare la salvarea configurarilor: {e}")
        return False

if __name__ == "__main__":
    print("\n=== MONITOR SITE-URI ===")
    
    # configurarile existente
    config = load_config()
    
    print("\nDoresti sa folosesti configurarile default? (da/nu, implicit: da):")
    use_default = input("> ").lower() != "nu"
    
    if use_default:
        # configurari default din fisier   
        file_name = config["input_file"]
        check_interval = config["check_interval"]
        timeout = config["timeout"]
        email_notification = config["email_notification"]
        email_to = config["email_to"]
        
        print(f"\nSe folosesc configurarile default:")
        print(f"Fisier de input: {file_name}")
        print(f"Interval de verificare: {check_interval} secunde")
        print(f"Timeout: {timeout} secunde")
        print(f"Notificari email: {'Da' if email_notification else 'Nu'}")
        print(f"Email catre: {email_to}")
        
    else:
        # obtinere fisiere disponibile
        csv_files, excel_files, txt_files = get_available_files()
        
        print("\nFisiere disponibile in folderul curent:")
        
        if csv_files:
            print("\nFisiere CSV:")
            for i, file in enumerate(csv_files, 1):
                print(f"{i}. {file}")
        
        if excel_files:
            print("\nFisiere Excel:")
            for i, file in enumerate(excel_files, 1):
                print(f"{i}. {file}")
        
        if txt_files:
            print("\nFisiere Text:")
            for i, file in enumerate(txt_files, 1):
                print(f"{i}. {file}")
        
        if not (csv_files or excel_files or txt_files):
            print("Nu au fost gasite fisiere CSV, Excel sau TXT in directorul curent.")
            exit(1)
        
        print(f"\nIntrodu numele fisierului (inclusiv extensia. (implicit: {config['input_file']}):")
        file_input = input("> ")
        file_name = file_input.strip() if file_input.strip() else config["input_file"]
        
        print(f"Introdu intervalul de verificare in secunde (implicit: {config['check_interval']} secunde):")
        interval_input = input("> ")
        check_interval = int(interval_input) if interval_input.strip() else config["check_interval"]
        
        print(f"Introdu timeout-ul pentru cereri in secunde (implicit: {config['timeout']} secunde):")
        timeout_input = input("> ")
        timeout = int(timeout_input) if timeout_input.strip() else config["timeout"]
        
        print(f"Doresti notificari pe email cand un site cade? (da/nu, implicit: {'da' if config['email_notification'] else 'nu'}):")
        email_input = input("> ").lower()
        if email_input:
            email_notification = email_input != "nu"
        else:
            email_notification = config["email_notification"]
        
        email_to = config["email_to"]
        if email_notification:
            print(f"Introdu adresa de email pentru notificari (implicit: {email_to}):")
            email_to_input = input("> ")
            if email_to_input.strip():
                email_to = email_to_input
        
        print("Doresti salvarea acestor configurari ca default pentru viitor? (da/nu, implicit: nu):")
        save_config_input = input("> ").lower() == "da"
        
        if save_config_input:
            new_config = {
                "input_file": file_name,
                "check_interval": check_interval,
                "timeout": timeout,
                "email_notification": email_notification,
                "email_to": email_to
            }
            save_config(new_config)
    
    # verificare existenta fisier
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)
    
    if not os.path.exists(file_path):
        print(f"Eroare: Fisierul '{file_name}' nu exista in directorul curent.")
        exit(1)
    
    monitor = SiteMonitor(
        input_file=file_path, 
        check_interval=check_interval, 
        timeout=timeout,
        email_notification=email_notification,
        email_to=email_to
    )
    
    # verificare existenta site-uri
    if not monitor.sites:
        print("Eroare: Nu au fost gasite site-uri in fisierul specificat")
        exit(1)
    
    monitor.start_monitoring()
