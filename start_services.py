import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import threading
import random
import re
import time

# ANSI color codes for terminal output
COLORS = {
    'HEADER': '\033[95m',  # Purple
    'BLUE': '\033[94m',    # Blue
    'GREEN': '\033[92m',   # Green
    'YELLOW': '\033[93m',  # Yellow
    'RED': '\033[91m',     # Red
    'CYAN': '\033[96m',    # Cyan
    'MAGENTA': '\033[95m', # Magenta
    'WHITE': '\033[97m',   # White
    'BRIGHT_CYAN': '\033[1;96m',  # Bright Cyan
    'ENDC': '\033[0m',     # Reset
    'BOLD': '\033[1m'      # Bold
}

# Assign specific colors to services
SERVICE_COLORS = {
    'API Gateway': COLORS['CYAN'],
    'Frontend': COLORS['GREEN'],
    'Auth Service': COLORS['YELLOW'],
    'Doc Management Service': COLORS['BLUE'],
    'Search Service': COLORS['MAGENTA'],
    'Share Service': COLORS['BRIGHT_CYAN'],
    'System': COLORS['HEADER']  # For system messages
}

def log(message: str, level: str = 'INFO', service: str = None) -> None:
    """Print formatted log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    service_prefix = f"[{service}] " if service else ""
    
    # Get service color or default to white
    service_color = SERVICE_COLORS.get(service, COLORS['WHITE'])
    
    level_color = {
        'INFO': COLORS['BLUE'],
        'ERROR': COLORS['RED'],
        'WARNING': COLORS['YELLOW'],
        'SUCCESS': COLORS['GREEN']
    }.get(level, COLORS['BLUE'])
    
    print(f"{COLORS['BOLD']}{timestamp}{COLORS['ENDC']} "
          f"{level_color}{level:8}{COLORS['ENDC']} "
          f"{service_color}{service_prefix}{COLORS['ENDC']}"
          f"{message}")

def get_venv_python():
    """Get the correct python executable from virtual environment"""
    return sys.executable

def get_venv_npm():
    """Get the correct npm executable from virtual environment"""
    if sys.platform == "win32":
        return str(Path("venv") / "Scripts" / "npm.cmd")
    return "npm"

def redact_sensitive_info(message: str) -> str:
    """Redact sensitive information and color code HTTP status codes"""
    # First redact sensitive information
    patterns = [
        (r'SECRET_KEY:.*?[=\s]([^\s]+)', r'SECRET_KEY: [REDACTED]'),
        (r'DB_URL:.*?[=\s]([^\s]+)', r'DB_URL: [REDACTED]'),
        (r'postgresql:\/\/[^:\s]+:[^@\s]+@[^\s]+', r'postgresql://[REDACTED]'),
        (r'Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*', r'Bearer [REDACTED]')
    ]
    
    # Apply redaction patterns
    redacted_message = message
    for pattern, replacement in patterns:
        redacted_message = re.sub(pattern, replacement, redacted_message)
    
    # Color code HTTP status codes
    status_patterns = [
        # 2xx Success (Green)
        (r'\b(200|201|202|203|204|205|206)\b', f"{COLORS['GREEN']}\\1{COLORS['ENDC']}"),
        # 3xx Redirection (Cyan)
        (r'\b(300|301|302|303|304|305|307|308)\b', f"{COLORS['CYAN']}\\1{COLORS['ENDC']}"),
        # 4xx Client Errors (Yellow)
        (r'\b(400|401|402|403|404|405|406|407|408|409|410|411|412|413|414|415|416|417|418|429)\b', 
         f"{COLORS['YELLOW']}\\1{COLORS['ENDC']}"),
        # 5xx Server Errors (Red)
        (r'\b(500|501|502|503|504|505|506|507|508|509|510|511)\b', f"{COLORS['RED']}\\1{COLORS['ENDC']}")
    ]
    
    # Apply status code coloring
    colored_message = redacted_message
    for pattern, replacement in status_patterns:
        colored_message = re.sub(pattern, replacement, colored_message)
    
    return colored_message

class ServiceStatus:
    def __init__(self):
        self.services = {}
        self.lock = threading.Lock()

    def update(self, name: str, status: str, pid: int = None, port: int = None):
        with self.lock:
            self.services[name] = {
                'status': status,
                'pid': pid,
                'port': port,
                'last_update': datetime.now()
            }

    def get_status(self):
        with self.lock:
            return self.services.copy()

    def print_status(self):
        with self.lock:
            print(f"\n{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")
            print(f"{COLORS['BOLD']}Current Service Status:{COLORS['ENDC']}")
            print(f"{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")
            
            for name, info in self.services.items():
                service_color = SERVICE_COLORS.get(name, COLORS['WHITE'])
                status_color = {
                    'STARTING': COLORS['YELLOW'],
                    'RUNNING': COLORS['GREEN'],
                    'FAILED': COLORS['RED'],
                    'TERMINATED': COLORS['MAGENTA']
                }.get(info['status'], COLORS['WHITE'])
                
                print(f"  {service_color}{name:<25}{COLORS['ENDC']} - "
                      f"{status_color}{info['status']:<12}{COLORS['ENDC']} "
                      f"PID: {info['pid'] or 'N/A':<8} "
                      f"Port: {info['port'] or 'N/A':<6}")
            
            print(f"{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}\n")

def stream_output(process, name, status_tracker):
    """Stream the output of a process to the console and update status"""
    try:
        for line in iter(process.stdout.readline, ''):
            log(redact_sensitive_info(line.strip()), "INFO", name)
            # Check for successful startup messages
            if "Running on http://" in line:
                port = re.search(r":(\d+)", line)
                if port:
                    status_tracker.update(name, "RUNNING", process.pid, int(port.group(1)))
                    status_tracker.print_status()
        
        for line in iter(process.stderr.readline, ''):
            log(redact_sensitive_info(line.strip()), "ERROR", name)
            
    except Exception as e:
        log(f"Output stream error: {str(e)}", "ERROR", name)
        status_tracker.update(name, "FAILED")
        status_tracker.print_status()

def start_services():
    status_tracker = ServiceStatus()
    base_dir = Path(__file__).parent

    # Service configurations with ports
    services = [
        {
            "name": "API Gateway",
            "dir": base_dir,
            "command": [get_venv_python(), "main.py"],
            "env": os.environ.copy(),
            "port": 5000
        },
        {
            "name": "Frontend",
            "dir": base_dir / "frontend",
            "command": [get_venv_npm(), "run", "dev"],
            "env": os.environ.copy()
        },
        {
            "name": "Auth Service",
            "dir": base_dir / "services" / "auth_service",
            "command": [get_venv_python(), "run.py"],
            "env": os.environ.copy()
        },
        {
            "name": "Doc Management Service",
            "dir": base_dir / "services" / "doc_mgmt_service",
            "command": [get_venv_python(), "run.py"],
            "env": os.environ.copy()
        },
        {
            "name": "Search Service",
            "dir": base_dir / "services" / "search_service",
            "command": [get_venv_python(), "run.py"],
            "env": os.environ.copy()
        },
        {
            "name": "Share Service",
            "dir": base_dir / "services" / "share_service",
            "command": [get_venv_python(), "run.py"],
            "env": os.environ.copy()
        }
    ]

    processes = []
    startup_timeout = 30  # seconds

    # Start all services
    for service in services:
        status_tracker.update(service["name"], "STARTING")
        status_tracker.print_status()
        
        try:
            process = subprocess.Popen(
                service["command"],
                cwd=service["dir"],
                env=service["env"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            processes.append((service["name"], process))
            threading.Thread(
                target=stream_output, 
                args=(process, service["name"], status_tracker)
            ).start()
            
        except Exception as e:
            log(f"Failed to start {service['name']}: {str(e)}", "ERROR", "System")
            status_tracker.update(service["name"], "FAILED")
            status_tracker.print_status()
            
            # Terminate all running services if any fails to start
            log("Initiating shutdown due to startup failure", "ERROR", "System")
            for name, proc in processes:
                try:
                    status_tracker.update(name, "TERMINATING")
                    proc.terminate()
                    proc.wait(timeout=5)
                    status_tracker.update(name, "TERMINATED")
                except Exception as term_e:
                    log(f"Error terminating {name}: {str(term_e)}", "ERROR", "System")
                    status_tracker.update(name, "FAILED")
            
            status_tracker.print_status()
            return

    # Monitor processes
    try:
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    status_tracker.update(name, "FAILED")
                    status_tracker.print_status()
                    log(f"{name} has terminated unexpectedly!", "ERROR", "System")
                    return
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")
        log("\nGracefully shutting down services...", "WARNING", "System")
        print(f"{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}\n")

        # Terminate all processes
        terminated_services = []
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
                terminated_services.append(name)
                log(f"Successfully terminated {name}", "SUCCESS", "System")
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if graceful shutdown takes too long
                log(f"Force killed {name}", "WARNING", "System")
            except Exception as e:
                log(f"Error terminating {name}: {str(e)}", "ERROR", "System")

        # Print final termination summary
        print(f"\n{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")
        print(f"{COLORS['BOLD']}Service Termination Summary:{COLORS['ENDC']}")
        print(f"{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")
        
        for service in services:
            name = service['name']
            service_color = SERVICE_COLORS.get(name, COLORS['WHITE'])
            status = "TERMINATED" if name in terminated_services else "FORCE KILLED"
            status_color = COLORS['GREEN'] if status == "TERMINATED" else COLORS['RED']
            
            print(f"  {service_color}{name:<25}{COLORS['ENDC']} - "
                  f"{status_color}{status}{COLORS['ENDC']}")
        
        print(f"\n{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")
        log("All services have been shut down", "SUCCESS", "System")
        print(f"{COLORS['HEADER']}{'='*80}{COLORS['ENDC']}")

if __name__ == "__main__":
    start_services()