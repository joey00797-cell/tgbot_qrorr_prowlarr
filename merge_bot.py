import os

# Настройки для вашего сервера
PROJECT_DIR = "app_v2" 
OUTPUT_FILE = "all_bot_code.txt"

EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '.venv', 'env', '.idea', '.vscode'}
EXCLUDE_FILES = {'.env', 'merge_bot.py', 'all_bot_code.txt', '.gitignore'}
ALLOWED_EXTENSIONS = {'.py', '.json', '.ini', '.yaml', '.yml', '.txt', '.md'}

def merge_project():
    if not os.path.exists(PROJECT_DIR):
        print(f"Ошибка: Папка '{PROJECT_DIR}' не найдена!")
        return

    print(f"Начинаю сборку кода из папки {PROJECT_DIR}...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write("=== АРХИТЕКТУРА И ИСХОДНЫЙ КОД ТЕЛЕГРАМ-БОТА ===\n")
        outfile.write(f"Корневая папка проекта: {PROJECT_DIR}\n\n")
        
        # Строим карту подпапок
        outfile.write("СТРУКТУРА ДИРЕКТОРИЙ И ФАЙЛОВ:\n")
        for root, dirs, files in os.walk(PROJECT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            level = root.replace(PROJECT_DIR, '').count(os.sep)
            indent = ' ' * 4 * level
            outfile.write(f"{indent}[DIR] {os.path.basename(root)}/\n")
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                if f not in EXCLUDE_FILES and os.path.splitext(f)[1] in ALLOWED_EXTENSIONS:
                    outfile.write(f"{sub_indent}- {f}\n")
        
        outfile.write("\n" + "="*50 + "\n\n")

        # Читаем содержимое файлов
        files_counter = 0
        for root, dirs, files in os.walk(PROJECT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                file_ext = os.path.splitext(file)[1]
                if file in EXCLUDE_FILES or file_ext not in ALLOWED_EXTENSIONS:
                    continue
                    
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, PROJECT_DIR)
                
                outfile.write(f"// FILE_START: {relative_path}\n")
                outfile.write(f"// ==========================================\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                    files_counter += 1
                except Exception as e:
                    outfile.write(f"# [Ошибка чтения файла: {e}]\n")
                outfile.write(f"\n// ==========================================\n")
                outfile.write(f"// FILE_END: {relative_path}\n\n")

    print(f"Готово! Объединено файлов: {files_counter} в файл {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_project()

