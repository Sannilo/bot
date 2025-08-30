// Основной JavaScript для Telegram Web App
document.addEventListener('DOMContentLoaded', function() {
    initTelegramWebApp();
    initAnimations();
    initButtonEffects();
    initTheme();
});

// Инициализация Telegram Web App
function initTelegramWebApp() {
    if (window.Telegram && window.Telegram.WebApp) {
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        // Настройка цветовой схемы
        if (tg.colorScheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        }
        
        // Обработка кнопки "Назад"
        tg.BackButton.onClick(() => {
            window.history.back();
        });
    }
}

// Инициализация анимаций
function initAnimations() {
    const elements = document.querySelectorAll('.subscription-card, .btn, .nav-btn');
    
    elements.forEach((element, index) => {
        element.style.animationDelay = `${index * 0.1}s`;
    });
}

// Эффекты для кнопок
function initButtonEffects() {
    const buttons = document.querySelectorAll('.btn, .nav-btn, .header-btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            createRippleEffect(e, this);
            
            // Анимация нажатия
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

// Создание ripple эффекта
function createRippleEffect(event, button) {
    const ripple = document.createElement('span');
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.className = 'ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    button.appendChild(ripple);
    
    setTimeout(() => ripple.remove(), 600);
}

// Управление темой
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    showMessage('Тема изменена');
}

// Показ сообщений
function showMessage(text, type = 'info') {
    const message = document.createElement('div');
    message.className = `message message-${type}`;
    message.textContent = text;
    message.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--card-bg);
        color: var(--text-color);
        padding: 12px 24px;
        border-radius: 8px;
        border: 1px solid var(--border-color);
        z-index: 1000;
        animation: messageSlide 3s ease-out forwards;
        box-shadow: var(--shadow);
    `;
    
    document.body.appendChild(message);
    setTimeout(() => message.remove(), 3000);
}

// Поддержка
function showSupport() {
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.openTelegramLink('https://t.me/support_bot');
    } else {
        showMessage('Откройте приложение в Telegram для связи с поддержкой');
    }
}

// Политика конфиденциальности
function showPrivacy() {
    showMessage('Политика конфиденциальности');
}

// Копирование в буфер обмена
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showMessage('Скопировано в буфер обмена', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showMessage('Скопировано в буфер обмена', 'success');
    } catch (err) {
        showMessage('Ошибка копирования', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Дополнительные CSS анимации
const additionalStyles = `
    @keyframes messageSlide {
        0% {
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
        }
        10%, 90% {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
        100% {
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
        }
    }
    
    [data-theme="light"] {
        --bg-color: #f2f2f7;
        --card-bg: #fff;
        --text-color: #000;
        --text-secondary: #6d6d70;
        --border-color: #e5e5ea;
    }
    
    .message-success {
        border-left: 4px solid var(--secondary-color);
    }
    
    .message-error {
        border-left: 4px solid var(--danger-color);
    }
    
    .message-info {
        border-left: 4px solid var(--primary-color);
    }
`;

// Добавление дополнительных стилей
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);