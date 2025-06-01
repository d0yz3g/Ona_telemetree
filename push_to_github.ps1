# PowerShell скрипт для отправки файлов в репозиторий GitHub

Write-Host "Начинаем процесс отправки в репозиторий GitHub..." -ForegroundColor Green

# Проверяем, установлен ли Git
try {
    $gitVersion = git --version
    Write-Host "Git установлен: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "Git не установлен! Пожалуйста, установите Git с https://git-scm.com/downloads" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Инициализируем репозиторий, если он еще не инициализирован
if (-not (Test-Path .git)) {
    Write-Host "Инициализация Git репозитория..." -ForegroundColor Yellow
    try {
        git init
        Write-Host "Репозиторий инициализирован" -ForegroundColor Green
    } catch {
        Write-Host "Ошибка при инициализации репозитория: $_" -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
}

# Настройка удаленного репозитория
Write-Host "Настройка удаленного репозитория..." -ForegroundColor Yellow
try {
    git remote remove origin 2>$null
    git remote add origin https://github.com/d0yz3g/Ona2.0.git
    Write-Host "Удаленный репозиторий настроен" -ForegroundColor Green
} catch {
    Write-Host "Ошибка при добавлении удаленного репозитория: $_" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Добавляем файлы .gitignore и .env.example, если необходимо
if (-not (Test-Path .env.example)) {
    Write-Host "Создание .env.example..." -ForegroundColor Yellow
    Copy-Item -Path "sample.env" -Destination ".env.example"
}

# Добавляем все файлы в индекс
Write-Host "Добавление файлов в индекс..." -ForegroundColor Yellow
try {
    git add .
    Write-Host "Файлы добавлены в индекс" -ForegroundColor Green
} catch {
    Write-Host "Ошибка при добавлении файлов: $_" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Создаем коммит
Write-Host "Создание коммита..." -ForegroundColor Yellow
try {
    git commit -m "Обновление бота Ona2.0"
    Write-Host "Коммит создан" -ForegroundColor Green
} catch {
    Write-Host "Ошибка при создании коммита: $_" -ForegroundColor Red
    Write-Host "Возможно, вам нужно настроить имя и email для Git:" -ForegroundColor Yellow
    Write-Host "git config --global user.name 'Ваше имя'" -ForegroundColor Cyan
    Write-Host "git config --global user.email 'ваш.email@example.com'" -ForegroundColor Cyan
    
    $configName = Read-Host "Введите ваше имя для Git"
    $configEmail = Read-Host "Введите ваш email для Git"
    
    if ($configName -and $configEmail) {
        git config --global user.name $configName
        git config --global user.email $configEmail
        git commit -m "Обновление бота Ona2.0"
    } else {
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
}

# Отправляем изменения в GitHub
Write-Host "Отправка изменений в GitHub..." -ForegroundColor Yellow
try {
    git push -u origin master --force
    Write-Host "Успешно отправлено в репозиторий GitHub!" -ForegroundColor Green
} catch {
    Write-Host "Ошибка при отправке изменений: $_" -ForegroundColor Red
    Write-Host "Вам нужно авторизоваться в GitHub." -ForegroundColor Yellow
    Write-Host "При запросе введите свои учетные данные GitHub." -ForegroundColor Yellow
    
    # Повторная попытка с запросом учетных данных
    try {
        git push -u origin master --force
        Write-Host "Успешно отправлено в репозиторий GitHub!" -ForegroundColor Green
    } catch {
        Write-Host "Не удалось выполнить push. Ошибка: $_" -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
}

Read-Host "Нажмите Enter для выхода" 