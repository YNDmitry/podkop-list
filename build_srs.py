#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
import ssl
import tempfile

# Constants
REPO_URL = "https://github.com/v2fly/domain-list-community.git"
REPO_PATH = "/tmp/domain-list-community"
DATA_PATH = os.path.join(REPO_PATH, "data")
DEFAULT_CONFIG = 'sources.txt'
DEFAULT_SRS_DIR = 'SRS'
DEFAULT_VERSION = 3


def load_sources(config_file=DEFAULT_CONFIG):
    if not os.path.exists(config_file):
        return []

    sources = []
    with open(config_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('|')
                url = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else os.path.basename(url)
                sources.append({'url': url, 'name': name})
    return sources


def get_all_data_files() -> list[dict]:
    try:
        if os.path.exists(REPO_PATH):
            subprocess.run(["git", "-C", REPO_PATH, "pull"], 
                         capture_output=True, timeout=60, text=True)
        else:
            result = subprocess.run(["git", "clone", REPO_URL, REPO_PATH], 
                         capture_output=True, timeout=120, text=True)
            if result.returncode != 0:
                return []
        
        if not os.path.exists(DATA_PATH):
            return []
        
        sources = [{'url': os.path.join(DATA_PATH, f), 'name': f} 
                   for f in sorted(os.listdir(DATA_PATH)) 
                   if os.path.isfile(os.path.join(DATA_PATH, f))]
        return sources
    except Exception as e:
        print(f"Ошибка при загрузке файлов: {e}")
        return []


def _get_file_content(url: str) -> str:
    """Загружает содержимое файла или URL"""
    if os.path.isfile(url):
        with open(url, 'r', encoding='utf-8') as f:
            return f.read()
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    response = urllib.request.urlopen(url, timeout=15, context=ssl_context)
    return response.read().decode('utf-8')

def download_domains(url: str) -> tuple[list[str], list[str], list[str], list[str]]:
    domains, full_domains, regex_patterns, includes = [], [], [], []
    
    try:
        content = _get_file_content(url)
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Удаляем комментарии
            line = line.split(' @')[0].split('#')[0].strip()
            if not line:
                continue
            
            if line.startswith('regexp:'):
                regex_patterns.append(line[7:])
            elif line.startswith('include:'):
                includes.append(line[8:])
            elif line.startswith('full:'):
                full_domains.append(line[5:])
            elif line:
                domains.append(line)
        
        return domains, full_domains, regex_patterns, includes
    except Exception as e:
        print(f"    Ошибка: {e}")
        return [], [], [], []


def resolve_includes(includes: list[str], data_dir: str | None = None, processed=None) -> tuple[list[str], list[str], list[str]]:
    processed = processed or set()
    data_dir = data_dir or DATA_PATH
    all_domains, all_full, all_regex = [], [], []
    
    for inc in includes:
        if inc in processed:
            continue
        processed.add(inc)
        
        domains, full_domains, regex_patterns, sub_includes = download_domains(os.path.join(data_dir, inc))
        all_domains.extend(domains)
        all_full.extend(full_domains)
        all_regex.extend(regex_patterns)
        
        if sub_includes:
            sub_d, sub_f, sub_r = resolve_includes(sub_includes, data_dir, processed)
            all_domains.extend(sub_d)
            all_full.extend(sub_f)
            all_regex.extend(sub_r)
    
    return all_domains, all_full, all_regex


def compile_srs(data, name, srs_dir=DEFAULT_SRS_DIR):
    os.makedirs(srs_dir, exist_ok=True)
    srs_path = os.path.join(srs_dir, f"{name}.srs")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(data, tmp, indent=2)
        json_path = tmp.name

    try:
        subprocess.run(
            ["sing-box", "rule-set", "compile", json_path, "-o", srs_path],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    finally:
        if os.path.exists(json_path):
            os.remove(json_path)


def build_srs_from_domains(domains, full_domains, regex_patterns, name):
    if not any([domains, full_domains, regex_patterns]):
        return False
    
    rules = []
    if domains:
        rules.append({"domain_suffix": sorted(set(domains))})
    if full_domains:
        rules.append({"domain": sorted(set(full_domains))})
    if regex_patterns:
        rules.append({"domain_regex": sorted(set(regex_patterns))})
    
    return compile_srs({"version": DEFAULT_VERSION, "rules": rules}, name)


def main():
    print("SRS Builder\n")
    
    sources = get_all_data_files()
    if not sources:
        print("Ошибка: не удалось загрузить файлы из GitHub")
        return 1
    
    custom_sources = load_sources()
    sources.extend(custom_sources)
    print(f"Найдено {len(sources)} источников\n")
    
    success_count = failed_count = 0
    
    for source in sources:
        print(f"Обработка: {source['name']}")
        
        domains, full_domains, regex_patterns, includes = download_domains(source['url'])
        if includes:
            inc_d, inc_f, inc_r = resolve_includes(includes)
            domains.extend(inc_d)
            full_domains.extend(inc_f)
            regex_patterns.extend(inc_r)
        
        if build_srs_from_domains(domains, full_domains, regex_patterns, source['name']):
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\nРезультат: ✓ {success_count}, ✗ {failed_count}")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
