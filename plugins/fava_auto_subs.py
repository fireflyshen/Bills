import os
import json
import datetime
import re
from fava.ext import FavaExtensionBase

class AutoSubsExtension(FavaExtensionBase):
    report_title = "Auto Subscriptions"

    def after_load_file(self):
        try:
            base_dir = os.path.dirname(self.ledger.beancount_file_path)
            config_path = os.path.join(base_dir, 'plugins', 'auto_subscriptions.json')

            if not os.path.exists(config_path):
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                subs = json.load(f)

            today = datetime.date.today()
            
            existing_fingerprints = set()
            for entry in self.ledger.all_entries:
                if type(entry).__name__ == "Transaction":
                    payee = getattr(entry, 'payee', None)
                    if payee and hasattr(entry, 'postings'):
                        for posting in entry.postings:
                            if posting.units and posting.units.number is not None:
                                amount_str = str(posting.units.number).lstrip('-')
                                existing_fingerprints.add(
                                    (entry.date.year, entry.date.month, payee, posting.account, amount_str)
                                )
                
            files_to_write = {}
            index_updates = set()
            
            for sub in subs:
                start_date_str = sub.get("start_date", "2026-01-01")
                try:
                    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                    
                day_of_month = sub.get("day_of_month", 1)
                y = start_date.year
                m = start_date.month
                
                while (y < today.year) or (y == today.year and m <= today.month):
                    try:
                        d = datetime.date(y, m, day_of_month)
                    except ValueError:
                        if m == 12:
                            d = datetime.date(y+1, 1, 1) - datetime.timedelta(days=1)
                        else:
                            d = datetime.date(y, m+1, 1) - datetime.timedelta(days=1)
                            
                    if start_date <= d <= today:
                        payee = sub.get("payee", "")
                        expense_account = sub.get("expense_account", "")
                        amount_str = str(sub.get("amount", "")).lstrip('-')
                        
                        if (y, m, payee, expense_account, amount_str) not in existing_fingerprints:
                            date_str = d.strftime("%Y-%m-%d")
                            narration = sub.get("narration", "")
                            
                            entry_str = f'\n{date_str} * "{payee}" "{narration}"\n'
                            entry_str += f'    {expense_account} {sub["amount"]} {sub["currency"]}\n'
                            entry_str += f'    {sub["asset_account"]} -{sub["amount"]} {sub["currency"]}\n'
                            
                            month_file_name = f"{y}-{m:02d}.bean"
                            target_path = os.path.join(base_dir, 'journal', str(y), month_file_name)
                            
                            if target_path not in files_to_write:
                                files_to_write[target_path] = []
                            files_to_write[target_path].append(entry_str)
                            index_updates.add((str(y), month_file_name))
                            
                            existing_fingerprints.add((y, m, payee, expense_account, amount_str))
                            
                    m += 1
                    if m > 12:
                        m = 1
                        y += 1
                        
            for file_path, lines in files_to_write.items():
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                mode = 'a' if os.path.exists(file_path) else 'w'
                with open(file_path, mode, encoding='utf-8') as f:
                    f.write("\n" + "\n".join(lines) + "\n")
                    
            for y_str, month_file in index_updates:
                index_path = os.path.join(base_dir, 'journal', y_str, 'index.bean')
                if os.path.exists(index_path):
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index_content = f.read()
                    
                    pattern = r';\s*include\s+"' + re.escape(month_file) + r'"'
                    if re.search(pattern, index_content):
                        new_content = re.sub(pattern, f'include "{month_file}"', index_content)
                        with open(index_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                    elif f'include "{month_file}"' not in index_content:
                        with open(index_path, 'a', encoding='utf-8') as f:
                            f.write(f'\ninclude "{month_file}"\n')
                else:
                    os.makedirs(os.path.dirname(index_path), exist_ok=True)
                    with open(index_path, 'w', encoding='utf-8') as f:
                        f.write(f'include "{month_file}"\n')
                        
                    main_index_path = os.path.join(base_dir, 'journal', 'index.bean')
                    if os.path.exists(main_index_path):
                        with open(main_index_path, 'r', encoding='utf-8') as f:
                            main_content = f.read()
                        if f'include "./{y_str}/index.bean"' not in main_content and f'include "{y_str}/index.bean"' not in main_content:
                            with open(main_index_path, 'a', encoding='utf-8') as f:
                                f.write(f'\ninclude "./{y_str}/index.bean"\n')
                            
        except Exception as e:
            print(f"AutoSubsExtension Error: {e}")
