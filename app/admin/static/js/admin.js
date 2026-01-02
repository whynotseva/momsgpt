/* MomsVPN Admin - JavaScript */

// Confirm dialogs
document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
        if (!confirm(this.dataset.confirm)) {
            e.preventDefault();
        }
    });
});

// Auto-hide alerts after 5 seconds
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
});

// Format numbers
function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

// Format bytes to GB
function formatBytes(bytes) {
    const gb = bytes / (1024 * 1024 * 1024);
    return gb.toFixed(2) + ' ГБ';
}

// Timestamp to date
function formatTimestamp(ts) {
    if (!ts) return '♾️ Бессрочно';
    const date = new Date(ts * 1000);
    return date.toLocaleDateString('ru-RU');
}

console.log('🤎 MomsVPN Admin loaded');
