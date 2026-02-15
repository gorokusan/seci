/**
 * SECI Knowledge Mapper - Analytics Dashboard
 * 分析とメトリクス表示
 */

//const { apiRequest, CATEGORY_INFO, showNotification } = window.SECIMapper;

let analyticsData = null;

// 分析データ取得
async function loadAnalytics() {
    try {
        const response = await apiRequest('/analytics/summary');
        analyticsData = response.analytics;
        updateDashboard();
    } catch (error) {
        console.error('分析データ取得エラー:', error);
        showNotification('分析データの取得に失敗しました', 'error');
    }
}

// ダッシュボード更新
function updateDashboard() {
    if (!analyticsData) return;
    
    // サマリー更新
    document.getElementById('totalNodes').textContent = analyticsData.total_nodes;
    document.getElementById('totalConnections').textContent = analyticsData.total_connections;
    document.getElementById('completionScore').textContent = analyticsData.completion_score + '%';
    document.getElementById('balanceScore').textContent = analyticsData.balance_score + '%';
    
    // カテゴリ分布更新
    updateCategoryDistribution();
    
    // フロー品質更新
    updateFlowQuality();
    
    // 完成度円グラフ更新
    updateCompletionCircle();
    
    // 提案とインサイト更新
    updateSuggestions();
    updateInsights();
    
    // SECIサイクル更新
    updateSECICycle();
}

// カテゴリ分布グラフ
function updateCategoryDistribution() {
    const distribution = analyticsData.category_distribution;
    const container = document.getElementById('distributionChart');
    const legend = document.getElementById('distributionLegend');
    
    container.innerHTML = '';
    legend.innerHTML = '';
    
    // 簡易バーチャート
    const maxCount = Math.max(...Object.values(distribution).map(d => d.count), 1);
    
    Object.entries(distribution).forEach(([category, data]) => {
        const bar = document.createElement('div');
        bar.style.cssText = `
            height: 40px;
            background: ${data.color};
            width: ${(data.count / maxCount) * 100}%;
            margin: 10px 0;
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            color: white;
            font-weight: 500;
        `;
        bar.textContent = `${data.name}: ${data.count}個 (${data.percentage}%)`;
        container.appendChild(bar);
        
        // 凡例
        const legendItem = document.createElement('div');
        legendItem.style.cssText = `
            display: flex;
            align-items: center;
            margin: 5px 0;
        `;
        legendItem.innerHTML = `
            <span style="width: 20px; height: 20px; background: ${data.color}; 
                        display: inline-block; margin-right: 10px; border-radius: 50%;"></span>
            <span>${data.name}</span>
        `;
        legend.appendChild(legendItem);
    });
}

// フロー品質更新
function updateFlowQuality() {
    const flowQuality = analyticsData.flow_quality;
    
    document.getElementById('flowScore').textContent = flowQuality.score + '%';
    document.getElementById('idealFlows').textContent = flowQuality.ideal_flows;
    document.getElementById('totalFlows').textContent = flowQuality.total_flows;
}

// 完成度円グラフ
function updateCompletionCircle() {
    const score = analyticsData.completion_score;
    const circumference = 2 * Math.PI * 80; // r=80
    const offset = circumference - (score / 100) * circumference;
    
    const circle = document.getElementById('completionCircle');
    circle.style.strokeDashoffset = offset;
    
    document.getElementById('completionText').textContent = score + '%';
    
    // 内訳更新（簡略版）
    const totalNodes = analyticsData.total_nodes;
    document.getElementById('nodeScore').textContent = 
        `${Math.min(totalNodes, 20)}/30`;
    document.getElementById('balanceSubScore').textContent = 
        `${Math.round(analyticsData.balance_score * 0.3)}/30`;
    document.getElementById('flowSubScore').textContent = 
        `${Math.round(analyticsData.flow_quality.score * 0.25)}/25`;
    
    // 接続密度計算
    let densityScore = 0;
    if (totalNodes > 1) {
        const maxConnections = totalNodes * (totalNodes - 1) / 2;
        const density = (analyticsData.total_connections / maxConnections) * 100;
        densityScore = Math.min(15, Math.round(density * 0.15));
    }
    document.getElementById('densityScore').textContent = `${densityScore}/15`;
}

// 提案リスト更新
function updateSuggestions() {
    const suggestions = analyticsData.suggestions;
    const container = document.getElementById('suggestionsList');
    
    if (!suggestions || suggestions.length === 0) {
        container.innerHTML = '<p>現在提案はありません</p>';
        return;
    }
    
    container.innerHTML = '';
    
    suggestions.forEach(suggestion => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        
        const priorityColor = {
            'high': 'var(--color-danger)',
            'medium': 'var(--color-warning)',
            'low': 'var(--color-info)'
        }[suggestion.priority] || 'var(--color-secondary)';
        
        item.innerHTML = `
            <div class="suggestion-header">
                <h4>${suggestion.title}</h4>
                <span class="priority-badge" style="background: ${priorityColor}">
                    ${suggestion.priority === 'high' ? '高' : suggestion.priority === 'medium' ? '中' : '低'}
                </span>
            </div>
            <p>${suggestion.description}</p>
        `;
        
        container.appendChild(item);
    });
}

// インサイトリスト更新
function updateInsights() {
    const insights = analyticsData.insights;
    const container = document.getElementById('insightsList');
    
    if (!insights || insights.length === 0) {
        container.innerHTML = '<p>インサイトはまだありません</p>';
        return;
    }
    
    container.innerHTML = '';
    
    insights.forEach(insight => {
        const item = document.createElement('div');
        item.className = 'insight-item';
        
        const icon = {
            'success': '✅',
            'warning': '⚠️',
            'info': 'ℹ️'
        }[insight.type] || 'ℹ️';
        
        item.innerHTML = `
            <span class="insight-icon">${icon}</span>
            <span>${insight.message}</span>
        `;
        
        container.appendChild(item);
    });
}

// SECIサイクル更新
function updateSECICycle() {
    const distribution = analyticsData.category_distribution;
    
    ['socialization', 'externalization', 'combination', 'internalization'].forEach(category => {
        const count = distribution[category]?.count || 0;
        const elementId = category + 'Count';
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = count;
        }
    });
}

// 更新ボタン
document.getElementById('refreshAnalytics').addEventListener('click', () => {
    loadAnalytics();
    showNotification('分析データを更新しました');
});

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    loadAnalytics();
    
    // 定期更新（30秒ごと）
    setInterval(loadAnalytics, 30000);
});
