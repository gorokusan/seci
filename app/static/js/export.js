/**
 * SECI Knowledge Mapper - Export Functionality
 * データエクスポート機能
 */

//const { apiRequest, showNotification, openModal, closeModal } = window.SECIMapper;

// エクスポートボタンイベント
document.getElementById('exportBtn')?.addEventListener('click', () => {
    openModal('exportModal');
});

// エクスポートキャンセル
document.getElementById('exportCancel')?.addEventListener('click', () => {
    closeModal('exportModal');
});

// エクスポート実行
document.querySelectorAll('.export-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        const format = e.target.dataset.format;
        await exportData(format);
    });
});

// データエクスポート
async function exportData(format) {
    try {
        if (format === 'json') {
            const response = await apiRequest(`/export?format=json`);
            const dataStr = JSON.stringify(response.data, null, 2);
            downloadFile(dataStr, 'seci_knowledge_map.json', 'application/json');
            showNotification('JSONファイルをダウンロードしました');
        } 
        else if (format === 'csv') {
            const response = await fetch('/api/export?format=csv', {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('エクスポートに失敗しました');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'seci_nodes.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('CSVファイルをダウンロードしました');
        }
        
        closeModal('exportModal');
    } catch (error) {
        console.error('エクスポートエラー:', error);
        showNotification('エクスポートに失敗しました', 'error');
    }
}

// ファイルダウンロード
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// エクスポート
window.SECIMapper.exportData = exportData;
