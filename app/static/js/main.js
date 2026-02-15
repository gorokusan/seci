/**
 * SECI Knowledge Mapper - Main JavaScript
 * 共通機能とユーティリティ
 */

// API Base URL
const API_BASE = '/api';

// Notification関数
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// プライバシー確認ダイアログ
function showPrivacyDialog(callback) {
    const dialog = document.getElementById('privacyDialog');
    const confirmBtn = document.getElementById('privacyConfirm');
    const cancelBtn = document.getElementById('privacyCancel');
    
    dialog.style.display = 'flex';
    
    const handleConfirm = () => {
        cleanup();
        callback(true);
    };
    
    const handleCancel = () => {
        cleanup();
        callback(false);
    };
    
    const cleanup = () => {
        dialog.style.display = 'none';
        confirmBtn.removeEventListener('click', handleConfirm);
        cancelBtn.removeEventListener('click', handleCancel);
    };
    
    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);
    
    // ESCキーでキャンセル
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            handleCancel();
            document.removeEventListener('keydown', escHandler);
        }
    });
}

// APIリクエスト関数
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'リクエストに失敗しました');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// カテゴリ情報
const CATEGORY_INFO = {
    socialization: {
        name: '共同化',
        nameEn: 'Socialization',
        color: '#4A90E2',
        description: '暗黙知の共有'
    },
    externalization: {
        name: '表出化',
        nameEn: 'Externalization',
        color: '#7ED321',
        description: '暗黙知の形式化'
    },
    combination: {
        name: '連結化',
        nameEn: 'Combination',
        color: '#F5A623',
        description: '形式知の統合'
    },
    internalization: {
        name: '内面化',
        nameEn: 'Internalization',
        color: '#BD10E0',
        description: '形式知の実践'
    }
};

// 日付フォーマット
function formatDate(dateString) {
    if (!dateString) return '---';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// デバウンス関数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ローディング表示
function showLoading(element) {
    element.innerHTML = '<div class="loading">読み込み中...</div>';
}

// モーダル制御
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// グローバルイベントリスナー
document.addEventListener('DOMContentLoaded', () => {
    // モーダル外クリックで閉じる
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
});

// エクスポート
window.SECIMapper = {
    showNotification,
    showPrivacyDialog,
    apiRequest,
    CATEGORY_INFO,
    formatDate,
    debounce,
    openModal,
    closeModal
};
