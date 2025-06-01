#!/usr/bin/env python
"""
Скрипт для очистки всех блокировок и активных процессов бота.
Запускайте этот скрипт перед запуском бота, если возникают ошибки конфликта TelegramAPI.
"""

import os
import sys
import tempfile
import socket
import time
import signal
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [CLEANUP] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cleanup.log")
    ]
)
logger = logging.getLogger("cleanup")

def cleanup_lock_file():
    """Удаляет файл блокировки, если он существует."""
    lock_file = os.path.join(tempfile.gettempdir(), 'ona_bot.lock')
    
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            logger.info(f"Файл блокировки {lock_file} успешно удален")
            print(f"✅ Файл блокировки {lock_file} успешно удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла блокировки: {e}")
            print(f"❌ Ошибка при удалении файла блокировки: {e}")
    else:
        logger.info(f"Файл блокировки {lock_file} не найден")
        print(f"ℹ️ Файл блокировки {lock_file} не найден")

def cleanup_socket():
    """Освобождает порт сокета, если он занят."""
    try:
        # Проверяем, занят ли порт 50000
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.bind(('localhost', 50000))
        test_socket.close()
        logger.info("Порт 50000 свободен")
        print("ℹ️ Порт 50000 свободен")
    except socket.error:
        logger.warning("Порт 50000 занят, попытка освободить...")
        print("⚠️ Порт 50000 занят, попытка освободить...")
        
        # На Windows найти и завершить процесс, который использует порт 50000
        if sys.platform == 'win32':
            try:
                import subprocess
                # Находим PID процесса, который использует порт 50000
                result = subprocess.run(
                    ['netstat', '-ano', '|', 'findstr', ':50000'],
                    capture_output=True, 
                    text=True, 
                    shell=True
                )
                output = result.stdout.strip()
                
                if output:
                    lines = output.split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                pid = int(pid)
                                logger.info(f"Найден процесс с PID {pid}, который использует порт 50000")
                                print(f"🔍 Найден процесс с PID {pid}, который использует порт 50000")
                                
                                # Завершаем процесс
                                os.kill(pid, signal.SIGTERM)
                                time.sleep(1)  # Даем время на завершение
                                
                                # Проверяем, завершился ли процесс
                                try:
                                    os.kill(pid, 0)  # Проверка существования процесса
                                    logger.warning(f"Процесс {pid} все еще запущен, принудительное завершение")
                                    print(f"⚠️ Процесс {pid} все еще запущен, принудительное завершение")
                                    os.kill(pid, signal.SIGKILL)
                                except OSError:
                                    logger.info(f"Процесс {pid} успешно завершен")
                                    print(f"✅ Процесс {pid} успешно завершен")
                            except ValueError:
                                logger.error(f"Не удалось преобразовать PID {pid} в число")
                                print(f"❌ Не удалось преобразовать PID {pid} в число")
                            except OSError as e:
                                logger.error(f"Ошибка при завершении процесса {pid}: {e}")
                                print(f"❌ Ошибка при завершении процесса {pid}: {e}")
                else:
                    logger.info("Не удалось найти процесс, использующий порт 50000")
                    print("ℹ️ Не удалось найти процесс, использующий порт 50000")
            except Exception as e:
                logger.error(f"Ошибка при поиске и завершении процесса: {e}")
                print(f"❌ Ошибка при поиске и завершении процесса: {e}")

def cleanup_bot_processes():
    """Находит и завершает все процессы Python, которые могут быть связаны с ботом."""
    try:
        import psutil
        bot_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.info
                # Проверяем, является ли это процессом Python и относится ли он к боту
                if proc_info['name'] and 'python' in proc_info['name'].lower():
                    cmdline = ' '.join(proc_info['cmdline'] or [])
                    if 'main.py' in cmdline or 'restart_bot.py' in cmdline:
                        if proc.pid != os.getpid():  # Не завершаем текущий процесс
                            bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Завершаем найденные процессы
        for proc in bot_processes:
            try:
                proc_name = ' '.join(proc.cmdline())
                logger.info(f"Завершение процесса бота: {proc.pid} ({proc_name})")
                print(f"🔄 Завершение процесса бота: {proc.pid} ({proc_name})")
                
                proc.terminate()
                time.sleep(1)  # Даем время на завершение
                
                # Проверяем, завершился ли процесс
                if proc.is_running():
                    logger.warning(f"Процесс {proc.pid} все еще запущен, принудительное завершение")
                    print(f"⚠️ Процесс {proc.pid} все еще запущен, принудительное завершение")
                    proc.kill()
                else:
                    logger.info(f"Процесс {proc.pid} успешно завершен")
                    print(f"✅ Процесс {proc.pid} успешно завершен")
            except Exception as e:
                logger.error(f"Ошибка при завершении процесса {proc.pid}: {e}")
                print(f"❌ Ошибка при завершении процесса {proc.pid}: {e}")
        
        if not bot_processes:
            logger.info("Активные процессы бота не найдены")
            print("ℹ️ Активные процессы бота не найдены")
    except ImportError:
        logger.warning("Библиотека psutil не установлена, невозможно найти процессы бота")
        print("⚠️ Библиотека psutil не установлена, невозможно найти процессы бота")
    except Exception as e:
        logger.error(f"Ошибка при поиске и завершении процессов бота: {e}")
        print(f"❌ Ошибка при поиске и завершении процессов бота: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("ОЧИСТКА БОТА ONA - УСТРАНЕНИЕ КОНФЛИКТОВ")
    print("=" * 50)
    
    # Запускаем очистку всех блокировок и процессов
    cleanup_lock_file()
    cleanup_socket()
    cleanup_bot_processes()
    
    print("\n" + "=" * 50)
    print("ОЧИСТКА ЗАВЕРШЕНА")
    print("Теперь вы можете запустить бота с помощью команды:")
    print("python restart_bot.py")
    print("=" * 50) 