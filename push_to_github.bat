@echo off
echo Начинаем процесс отправки в репозиторий GitHub...

:: Проверяем, установлен ли Git
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git не установлен! Пожалуйста, установите Git с https://git-scm.com/downloads
    pause
    exit /b 1
)

:: Инициализируем репозиторий, если он еще не инициализирован
if not exist .git (
    echo Инициализация Git репозитория...
    git init
    if %ERRORLEVEL% NEQ 0 (
        echo Ошибка при инициализации репозитория!
        pause
        exit /b 1
    )
)

:: Настройка удаленного репозитория
echo Настройка удаленного репозитория...
git remote remove origin 2>nul
git remote add origin https://github.com/d0yz3g/Ona2.0.git
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка при добавлении удаленного репозитория!
    pause
    exit /b 1
)

:: Добавляем все файлы в индекс
echo Добавление файлов в индекс...
git add .
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка при добавлении файлов!
    pause
    exit /b 1
)

:: Создаем коммит
echo Создание коммита...
git commit -m "Обновление бота Ona2.0"
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка при создании коммита!
    pause
    exit /b 1
)

:: Отправляем изменения в GitHub
echo Отправка изменений в GitHub...
git push -u origin main --force
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка при отправке изменений!
    echo Возможно, вам нужно авторизоваться. Выполните следующие команды вручную:
    echo git config --global user.name "Ваше имя"
    echo git config --global user.email "ваш.email@example.com"
    echo Затем попробуйте запустить этот скрипт снова.
    pause
    exit /b 1
)

echo Успешно отправлено в репозиторий GitHub!
pause 