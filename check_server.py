import requests
import time
import pandas as pd
import concurrent.futures
import os
from urllib3.exceptions import InsecureRequestWarning
from email_alert import email_alert
import json
from datetime import datetime

# dezactivare avertizari SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# coduri culori ANSI
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GRAY = '\033[90m'
    BRIGHT_GREEN = '\033[32m'
    BRIGHT_RED = '\033[31m'
    BRIGHT_YELLOW = '\033[33m'
    BRIGHT_BLUE = '\033[34m'

# header
def print_header(text, color=Colors.CYAN):
    width = 60
    border = "═" * width
    print(f"\n{color}{Colors.BOLD}╔{border}╗{Colors.END}")
    print(f"{color}{Colors.BOLD}║{text.center(width)}║{Colors.END}")
    print(f"{color}{Colors.BOLD}╚{border}╝{Colors.END}")

# chenar pentru text
def print_box(text, color=Colors.WHITE):
    lines = text.split('\n')
    max_width = max(len(line) for line in lines) + 4
    
    print(f"{color}┌{'─' * (max_width - 2)}┐{Colors.END}")
    for line in lines:
        print(f"{color}│ {line.ljust(max_width - 4)} │{Colors.END}")
    print(f"{color}└{'─' * (max_width - 2)}┘{Colors.END}")

def print_status_line(site, status, response_time=None, error=None, status_code=None):
    # linie status 
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if status == 'UP':
        status_icon = f"{Colors.BRIGHT_GREEN}●{Colors.END}"
        status_text = f"{Colors.BRIGHT_GREEN}{Colors.BOLD}UP{Colors.END}"
        site_text = f"{Colors.WHITE}{site}{Colors.END}"
        
        if response_time:
            time_color = Colors.GREEN if response_time < 1 else Colors.YELLOW if response_time < 3 else Colors.RED
            response_text = f"{time_color}{response_time}s{Colors.END}"
        else:
            response_text = ""
            
        if status_code:
            code_text = f"{Colors.GRAY}({status_code}){Colors.END}"
        else:
            code_text = ""
            
        print(f"{Colors.GRAY}[{timestamp}]{Colors.END} {status_icon} {site_text.ljust(35)} {status_text} {response_text} {code_text}")
    else:
        status_icon = f"{Colors.BRIGHT_RED}●{Colors.END}"
        status_text = f"{Colors.BRIGHT_RED}{Colors.BOLD}DOWN{Colors.END}"
        site_text = f"{Colors.WHITE}{site}{Colors.END}"
        error_text = f"{Colors.RED}{error or 'Eroare necunoscuta'}{Colors.END}"
        
        print(f"{Colors.GRAY}[{timestamp}]{Colors.END} {status_icon} {site_text.ljust(35)} {status_text} - {error_text}")

# separator linie
def print_separator(char="─", length=80, color=Colors.GRAY):
    print(f"{color}{char * length}{Colors.END}")

# rezumat status final
def print_summary(total_sites, up_sites, down_sites):
    print(f"\n{Colors.BOLD}📊 REZUMAT:{Colors.END}")
    print(f"┌─────────────────────────────────┐")
    print(f"│ Total site-uri: {Colors.CYAN}{Colors.BOLD}{str(total_sites).rjust(15)}{Colors.END} │")
    print(f"│ Site-uri online: {Colors.GREEN}{Colors.BOLD}{str(up_sites).rjust(14)}{Colors.END} │")
    print(f"│ Site-uri offline: {Colors.RED}{Colors.BOLD}{str(down_sites).rjust(13)}{Colors.END} │")
    print(f"└─────────────────────────────────┘")

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
                
            print(f"{Colors.GREEN}✅ S-au incarcat {Colors.BOLD}{len(self.sites)}{Colors.END}{Colors.GREEN} site-uri din fisierul {Colors.CYAN}{input_file}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}❌ Eroare la incarcarea fisierului: {Colors.BOLD}{e}{Colors.END}")
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
        
        print(f"{Colors.YELLOW}🔄 Verificare în curs...{Colors.END}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_site = {executor.submit(self.check_site, site): site for site in self.sites}
            for future in concurrent.futures.as_completed(future_to_site):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    site = future_to_site[future]
                    print(f"{Colors.RED}❌ Eroare la verificarea site-ului {site['domain'] or site['ip']}: {e}{Colors.END}")
        
        return results
    
    def display_status(self, results, email_notification=None, alert_sites=None):
        if email_notification is None:
            email_notification = self.email_notification
        
        down_sites = [r for r in results if r['status'] == 'DOWN']
        up_sites = [r for r in results if r['status'] == 'UP']
        
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print_header("🌐 MONITOR SITE-URI - STATUS LIVE", Colors.CYAN)

        # afisare site-uri offline
        if down_sites:
            print(f"\n{Colors.BRIGHT_RED}{Colors.BOLD}🔴 SITE-URI OFFLINE ({len(down_sites)}){Colors.END}")
            print_separator("─", 80, Colors.RED)
            
            sites_to_display = [r for r in down_sites if alert_sites is None or r['site'] in alert_sites]
            down_sites_text = ""
            
            for site in sites_to_display:
                print_status_line(
                    site['site'], 
                    site['status'], 
                    site.get('response_time'), 
                    site.get('error'), 
                    site.get('status_code')
                )
                down_sites_text += f"❌ {site['site']}: {site.get('error', 'Eroare necunoscuta')}\n"
            
            # alerta prin email
            if email_notification and down_sites_text:
                subject = f"Notificare: {len(sites_to_display)} site-uri indisponibile"
                body = f"Urmatoarele site-uri sunt indisponibile:\n\n{down_sites_text}\n"
                
                body += f"\nStatusul verificarii: {len(results) - len(down_sites)} site-uri online, {len(down_sites)} site-uri offline"
                
                try:
                    email_alert(subject, body, self.email_to)
                    print(f"\n{Colors.CYAN}✉️  Email trimis la {Colors.BOLD}{self.email_to}{Colors.END}")
                except Exception as e:
                    print(f"\n{Colors.RED}❌ Eroare la trimiterea email-ului: {Colors.BOLD}{e}{Colors.END}")
        else:
            print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}🎉 TOATE SITE-URILE SUNT ONLINE!{Colors.END}")
            print_separator("─", 80, Colors.GREEN)
        
        # rezumat
        print_summary(len(results), len(up_sites), len(down_sites))
        
        # rezumat configuratie
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"\n{Colors.GRAY}⏰ Ultima verificare: {current_time}")
        print(f"🔄 Urmatoarea verificare în {self.check_interval} secunde")
        print(f"⚙️  Timeout: {self.timeout}s | Email: {'Activ' if self.email_notification else 'Inactiv'}")
        print(f"💡 Apasă Ctrl+C pentru a opri monitorizarea{Colors.END}")

    def start_monitoring(self):
        print_header("🚀 PORNIRE MONITOR", Colors.MAGENTA)
        
        config_text = f"📊 Site-uri monitorizate: {len(self.sites)}\n"
        config_text += f"⏱️  Interval verificare: {self.check_interval} secunde\n"
        config_text += f"⏰ Timeout cereri: {self.timeout} secunde\n"
        
        if self.email_notification:
            config_text += f"📧 Alerte email: ACTIVATE\n"
            config_text += f"📬 Destinatar: {self.email_to}"
        else:
            config_text += f"📧 Alerte email: DEZACTIVATE"
        
        print_box(config_text, Colors.YELLOW)
        
        print(f"\n{Colors.BRIGHT_GREEN}🎯 Monitorizarea a inceput!{Colors.END}")
        print_separator("═", 80, Colors.CYAN)
        
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
                    self.display_status(results, self.email_notification, alert_sites=new_down_sites)
                else:
                    # afisare status curent pt. toate site-urile
                    self.display_status(results, False)
                
                # actualizare lista site-uri offline
                previous_down_sites = current_down_sites
                
                # countdown pana la urmatoarea verificare
                for i in range(self.check_interval, 0, -1):
                    print(f"\r{Colors.GRAY}⏳ Urmatoarea verificare în: {Colors.BOLD}{i:2d}{Colors.END}{Colors.GRAY} secunde...{Colors.END}", end='', flush=True)
                    time.sleep(1)
                print()  # Linie nouă după countdown
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⏹️ Monitorizarea a fost oprita de utilizator{Colors.END}")
            print_header("👋 LA REVEDERE!", Colors.MAGENTA)

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
        print(f"{Colors.BLUE}ℹ️ Nu a fost gasit fisierul {file_name}. Se vor folosi valorile implicite{Colors.END}")
        return default_config
    except json.JSONDecodeError:
        print(f"{Colors.YELLOW}⚠️ Eroare la citirea fisierului {file_name}. Se vor folosi valorile implicite{Colors.END}")
        return default_config
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️ Eroare: {e}. Se vor folosi valorile implicite{Colors.END}")
        return default_config

def save_config(config_data, file_name="default_config.json"):
    try:
        with open(file_name, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
        print(f"{Colors.GREEN}✅ Configurarile au fost salvate în {Colors.BOLD}{file_name}{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}❌ Eroare la salvarea configurarilor: {Colors.BOLD}{e}{Colors.END}")
        return False

def print_file_list(title, files, color):
    if files:
        print(f"\n{color}{Colors.BOLD}📁 {title}:{Colors.END}")
        for i, file in enumerate(files, 1):
            print(f"   {color}{i}.{Colors.END} {Colors.WHITE}{file}{Colors.END}")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print_header("🌐 MONITOR SITE-URI", Colors.CYAN)
    
    # configurarile existente
    config = load_config()
    
    print(f"\n{Colors.YELLOW}🔧 Doresti sa folosesti configurarile default? {Colors.BOLD}(da/nu, implicit: da){Colors.END}")
    use_default = input(f"{Colors.CYAN}> {Colors.END}").lower() != "nu"
    
    if use_default:
        # configurari default din fisier   
        file_name = config["input_file"]
        check_interval = config["check_interval"]
        timeout = config["timeout"]
        email_notification = config["email_notification"]
        email_to = config["email_to"]
        
        print(f"\n{Colors.GREEN}✅ Se folosesc configurarile default:{Colors.END}")
        config_text = f"📄 Fisier de input: {file_name}\n"
        config_text += f"⏱️  Interval de verificare: {check_interval} secunde\n"
        config_text += f"⏰ Timeout: {timeout} secunde\n"
        config_text += f"📧 Notificari email: {'Da' if email_notification else 'Nu'}\n"
        config_text += f"📬 Email catre: {email_to}"
        
        print_box(config_text, Colors.GREEN)
        
    else:
        # obtinere fisiere disponibile
        csv_files, excel_files, txt_files = get_available_files()
        
        print_header("📁 FISIERE DISPONIBILE", Colors.BLUE)
        
        print_file_list("Fisiere CSV", csv_files, Colors.GREEN)
        print_file_list("Fisiere Excel", excel_files, Colors.YELLOW)
        print_file_list("Fisiere Text", txt_files, Colors.CYAN)
        
        if not (csv_files or excel_files or txt_files):
            print(f"{Colors.RED}❌ Nu au fost gasite fisiere CSV, Excel sau TXT in directorul curent.{Colors.END}")
            exit(1)
        
        print(f"\n{Colors.YELLOW}📄 Introdu numele fișierului (inclusiv extensia. implicit: {Colors.BOLD}{config['input_file']}{Colors.END}{Colors.YELLOW}):{Colors.END}")
        file_input = input(f"{Colors.CYAN}> {Colors.END}")
        file_name = file_input.strip() if file_input.strip() else config["input_file"]
        
        print(f"\n{Colors.YELLOW}⏱️  Introdu intervalul de verificare în secunde (implicit: {Colors.BOLD}{config['check_interval']}{Colors.END}{Colors.YELLOW} secunde):{Colors.END}")
        interval_input = input(f"{Colors.CYAN}> {Colors.END}")
        check_interval = int(interval_input) if interval_input.strip() else config["check_interval"]
        
        print(f"\n{Colors.YELLOW}⏰ Introdu timeout-ul pentru cereri în secunde (implicit: {Colors.BOLD}{config['timeout']}{Colors.END}{Colors.YELLOW} secunde):{Colors.END}")
        timeout_input = input(f"{Colors.CYAN}> {Colors.END}")
        timeout = int(timeout_input) if timeout_input.strip() else config["timeout"]
        
        print(f"\n{Colors.YELLOW}📧 Dorești notificări pe email când un site cade? (da/nu, implicit: {Colors.BOLD}{'da' if config['email_notification'] else 'nu'}{Colors.END}{Colors.YELLOW}):{Colors.END}")
        email_input = input(f"{Colors.CYAN}> {Colors.END}").lower()
        if email_input:
            email_notification = email_input != "nu"
        else:
            email_notification = config["email_notification"]
        
        email_to = config["email_to"]
        if email_notification:
            print(f"\n{Colors.YELLOW}📬 Introdu adresa de email pentru notificari (implicit: {Colors.BOLD}{email_to}{Colors.END}{Colors.YELLOW}):{Colors.END}")
            email_to_input = input(f"{Colors.CYAN}> {Colors.END}")
            if email_to_input.strip():
                email_to = email_to_input
        
        print(f"\n{Colors.YELLOW}💾 Doresti salvarea acestor configurari ca default pentru viitor? (da/nu, implicit: nu):{Colors.END}")
        save_config_input = input(f"{Colors.CYAN}> {Colors.END}").lower() == "da"
        
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
        print(f"{Colors.RED}❌ Eroare: Fisierul '{Colors.BOLD}{file_name}{Colors.END}{Colors.RED}' nu exista in directorul curent.{Colors.END}")
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
        print(f"{Colors.RED}❌ Eroare: Nu au fost gasite site-uri in fisierul specificat{Colors.END}")
        exit(1)
    
    # Pauză scurtă pentru a permite utilizatorului să vadă configurările
    print(f"\n{Colors.GRAY}🚀 Pornirea monitorizarii in 3 secunde...{Colors.END}")
    time.sleep(3)
    
    monitor.start_monitoring()