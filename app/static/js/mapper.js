/**
 * SECI Knowledge Mapper - Mapping Visualization
 * D3.jsを使用した知識マッピング機能
 */

//const { showNotification, showPrivacyDialog, apiRequest, CATEGORY_INFO, openModal, closeModal, formatDate } = window.SECIMapper;

let nodes = [];
let connections = [];
let svg, g, simulation;
let currentNode = null;
let transform = d3.zoomIdentity;

// D3.js初期化
function initializeD3() {
    const canvas = document.getElementById('mapCanvas');
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    
    svg = d3.select('#mapCanvas')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // ズーム機能
    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .on('zoom', (event) => {
            transform = event.transform;
            g.attr('transform', transform);
        });
    
    svg.call(zoom);
    
    g = svg.append('g');
    
    // 矢印マーカー定義
    svg.append('defs').selectAll('marker')
        .data(['end'])
        .enter().append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 25)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('class', 'link-arrow');
    
    // Force simulation
    simulation = d3.forceSimulation()
        .force('link', d3.forceLink().id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(50));
    
    // ズームコントロール
    document.getElementById('zoomIn').addEventListener('click', () => {
        svg.transition().call(zoom.scaleBy, 1.3);
    });
    
    document.getElementById('zoomOut').addEventListener('click', () => {
        svg.transition().call(zoom.scaleBy, 0.7);
    });
    
    document.getElementById('resetView').addEventListener('click', () => {
        svg.transition().call(zoom.transform, d3.zoomIdentity);
    });
}

// データロード
async function loadData() {
    try {
        const response = await apiRequest('/nodes');
        nodes = response.nodes || [];
        connections = response.connections || [];
        updateVisualization();
        updateStats();
    } catch (error) {
        console.error('データロードエラー:', error);
    }
}

// ビジュアライゼーション更新
function updateVisualization() {
    if (!g) return;
    
    // リンク描画
    const link = g.selectAll('.link')
        .data(connections, d => d.id);
    
    link.exit().remove();
    
    const linkEnter = link.enter()
        .append('path')
        .attr('class', 'link')
        .attr('marker-end', 'url(#arrow)');
    
    const linkAll = linkEnter.merge(link);
    
    // ノード描画
    const node = g.selectAll('.node')
        .data(nodes, d => d.id);
    
    node.exit().remove();
    
    const nodeEnter = node.enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended))
        .on('click', (event, d) => {
            event.stopPropagation();
            showNodeDetail(d);
        });
    
    nodeEnter.append('circle')
        .attr('r', 20)
        .attr('fill', d => CATEGORY_INFO[d.category].color);
    
    nodeEnter.append('text')
        .attr('dy', 35)
        .attr('fill', '#333')
        .style('font-size', '12px')
        .style('font-weight', '500')
        .style('text-anchor', 'middle')
        .text(d => d.title.length > 15 ? d.title.substring(0, 15) + '...' : d.title);
    
    const nodeAll = nodeEnter.merge(node);
    nodeAll.select('circle')
        .attr('fill', d => CATEGORY_INFO[d.category].color);
    
    nodeAll.select('text')
        .text(d => d.title.length > 15 ? d.title.substring(0, 15) + '...' : d.title);
    
    // Simulation更新
    simulation.nodes(nodes);
    simulation.force('link').links(connections.map(c => ({
        source: c.source_id,
        target: c.target_id,
        id: c.id
    })));
    
    simulation.alpha(1).restart();
    
    simulation.on('tick', () => {
        linkAll.attr('d', d => {
            const source = nodes.find(n => n.id === d.source_id);
            const target = nodes.find(n => n.id === d.target_id);
            if (!source || !target) return '';
            return `M${source.x},${source.y} L${target.x},${target.y}`;
        });
        
        nodeAll.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

// ドラッグイベント
function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
    
    // 位置保存
    updateNodePosition(d.id, event.x, event.y);
}

// ノード位置更新
async function updateNodePosition(nodeId, x, y) {
    try {
        await apiRequest(`/nodes/${nodeId}`, {
            method: 'PUT',
            body: JSON.stringify({ position: { x, y } })
        });
    } catch (error) {
        console.error('位置更新エラー:', error);
    }
}

// 統計更新
async function updateStats() {
    document.getElementById('nodeCount').textContent = nodes.length;
    document.getElementById('connectionCount').textContent = connections.length;
    
    // 完成度スコア取得
    try {
        const response = await apiRequest('/analytics/summary');
        const score = response.analytics.completion_score || 0;
        document.getElementById('completionScore').textContent = score + '%';
        
        // プログレスバー更新
        const progressFill = document.getElementById('progressFill');
        if (progressFill) {
            progressFill.style.width = score + '%';
        }
    } catch (error) {
        console.error('スコア取得エラー:', error);
    }
}

// ノード追加モーダル
document.getElementById('addNodeBtn').addEventListener('click', () => {
    currentNode = null;
    document.getElementById('modalTitle').textContent = 'ノードを追加';
    document.getElementById('nodeForm').reset();
    openModal('nodeModal');
});

// ノードフォーム送信
document.getElementById('nodeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        title: document.getElementById('nodeTitle').value,
        category: document.getElementById('nodeCategory').value,
        description: document.getElementById('nodeDescription').value
    };
    
    showPrivacyDialog(async (confirmed) => {
        if (!confirmed) return;
        
        try {
            if (currentNode) {
                await apiRequest(`/nodes/${currentNode.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                showNotification('ノードを更新しました');
            } else {
                await apiRequest('/nodes', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                showNotification('ノードを追加しました');
            }
            
            closeModal('nodeModal');
            await loadData();
        } catch (error) {
            console.error('保存エラー:', error);
        }
    });
});

// モーダルキャンセル
document.getElementById('modalCancel').addEventListener('click', () => {
    closeModal('nodeModal');
});

// ノード詳細表示
async function showNodeDetail(node) {
    try {
        const response = await apiRequest(`/nodes/${node.id}`);
        const nodeData = response.node;
        
        document.getElementById('detailTitle').textContent = nodeData.title;
        
        const categoryBadge = document.getElementById('detailCategory');
        categoryBadge.textContent = CATEGORY_INFO[nodeData.category].name;
        categoryBadge.style.backgroundColor = CATEGORY_INFO[nodeData.category].color;
        categoryBadge.style.color = 'white';
        categoryBadge.style.padding = '5px 10px';
        categoryBadge.style.borderRadius = '4px';
        categoryBadge.style.display = 'inline-block';

	if (nodeData.tags) {
		window.TagManager.displayNodeTags(nodeData.tags, document.getElementById('detailTags'));
        }
        
        document.getElementById('detailDescription').textContent = 
            nodeData.description || '説明なし';
        document.getElementById('detailCreated').textContent = 
            formatDate(nodeData.created_at);
        document.getElementById('detailUpdated').textContent = 
            formatDate(nodeData.updated_at);
	
	if (nodeData.stats) {
	    document.getElementById('versionCount').textContent = nodeData.stats.versions || 0;
            document.getElementById('commentCount').textContent = nodeData.stats.comments || 0;
        }
        
        currentNode = nodeData;
	
	//リアクションを初期化
	window.ReactionManager.initReactions(node.id);

	//コメントを初期化
	window.CommentManager.initComments(node.id);

	//バージョン履歴を読み込み
	loadVersionHistory(node.id);

	//タブ切り替え
	initDetailTabs();

        openModal('nodeDetailModal');
    } catch (error) {
        console.error('詳細取得エラー:', error);
    }
}

// タブ切り替え初期化
function initDetailTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // すべてのタブを非アクティブに
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // 選択されたタブをアクティブに
            btn.classList.add('active');
            document.getElementById(tabName + 'Tab').classList.add('active');
        });
    });
}

// バージョン履歴を読み込み
async function loadVersionHistory(nodeId) {
    try {
        const response = await apiRequest(`/nodes/${nodeId}/versions`);
        
        if (response.success) {
            const versions = response.versions || [];
            const container = document.getElementById('versionsList');
            
            if (versions.length === 0) {
                container.innerHTML = '<p class="no-versions">バージョン履歴はありません</p>';
                return;
            }
            
            container.innerHTML = '';
            
            versions.forEach((version, index) => {
                const versionEl = document.createElement('div');
                versionEl.className = 'version-item';
                
                const badge = index === 0 ? '<span class="version-badge current">最新</span>' : '';
                
                versionEl.innerHTML = `
                    <div class="version-header">
                        <strong>バージョン ${version.version_number}</strong>
                        ${badge}
                        <span class="version-time">${formatDate(version.created_at)}</span>
                    </div>
                    <div class="version-details">
                        <p><strong>タイトル:</strong> ${version.title}</p>
                        <p><strong>カテゴリ:</strong> ${CATEGORY_INFO[version.category].name}</p>
                        ${version.change_description ? `<p><strong>変更内容:</strong> ${version.change_description}</p>` : ''}
                    </div>
                `;
                
                container.appendChild(versionEl);
            });
        }
    } catch (error) {
        console.error('バージョン履歴取得エラー:', error);
    }
}

// 詳細モーダルイベント
document.getElementById('detailClose').addEventListener('click', () => {
    closeModal('nodeDetailModal');
});

document.getElementById('editNodeBtn').addEventListener('click', () => {
    closeModal('nodeDetailModal');
    document.getElementById('modalTitle').textContent = 'ノードを編集';
    document.getElementById('nodeTitle').value = currentNode.title;
    document.getElementById('nodeCategory').value = currentNode.category;
    document.getElementById('nodeDescription').value = currentNode.description || '';
    openModal('nodeModal');
});

document.getElementById('deleteNodeBtn').addEventListener('click', async () => {
    if (!confirm('このノードを削除してもよろしいですか？')) return;
    
    try {
        await apiRequest(`/nodes/${currentNode.id}`, { method: 'DELETE' });
        showNotification('ノードを削除しました');
        closeModal('nodeDetailModal');
        await loadData();
    } catch (error) {
        console.error('削除エラー:', error);
    }
});

// 自動配置ボタン
document.getElementById('autoLayoutBtn').addEventListener('click', () => {
    if (simulation) {
        // ノードの固定を解除
        nodes.forEach(node => {
            node.fx = null;
            node.fy = null;
        });
        
        // シミュレーションを再開
        simulation.alpha(1).restart();
        
        showNotification('自動配置を実行しました');
    }
});

// エクスポートボタン
document.getElementById('exportBtn').addEventListener('click', () => {
    openModal('exportModal');
});

document.getElementById('exportCancel').addEventListener('click', () => {
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

// 検索機能
const searchInput = document.getElementById('searchInput');
if (searchInput) {
    searchInput.addEventListener('input', window.SECIMapper.debounce(async (e) => {
        const query = e.target.value;
        if (query.length < 2) {
            document.getElementById('searchResults').innerHTML = '';
            return;
        }
        
        try {
            const response = await apiRequest(`/search?q=${encodeURIComponent(query)}`);
            displaySearchResults(response.nodes);
        } catch (error) {
            console.error('検索エラー:', error);
        }
    }, 300));
}

// 検索結果表示
function displaySearchResults(results) {
    const container = document.getElementById('searchResults');
    
    if (!results || results.length === 0) {
        container.innerHTML = '<p style="padding: 10px; color: #666;">結果が見つかりません</p>';
        return;
    }
    
    container.innerHTML = '';
    results.forEach(node => {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 8px;
            margin: 4px 0;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        item.innerHTML = `
            <strong style="color: ${CATEGORY_INFO[node.category].color}">${node.title}</strong><br>
            <small style="color: #666;">${CATEGORY_INFO[node.category].name}</small>
        `;
        item.addEventListener('mouseenter', () => {
            item.style.background = '#f5f5f5';
        });
        item.addEventListener('mouseleave', () => {
            item.style.background = 'white';
        });
        item.addEventListener('click', () => {
            showNodeDetail(node);
        });
        container.appendChild(item);
    });
}

// カテゴリフィルター
document.querySelectorAll('.category-filter').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
        const value = e.target.value;
        
        if (value === 'all') {
            // すべて表示/非表示
            const checked = e.target.checked;
            document.querySelectorAll('.category-filter').forEach(cb => {
                if (cb.value !== 'all') {
                    cb.checked = checked;
                }
            });
            filterNodes();
        } else {
            // 個別カテゴリ
            filterNodes();
            
            // 「すべて」チェックボックスの状態を更新
            const allCheckbox = document.querySelector('.category-filter[value="all"]');
            const otherCheckboxes = Array.from(document.querySelectorAll('.category-filter'))
                .filter(cb => cb.value !== 'all');
            const allChecked = otherCheckboxes.every(cb => cb.checked);
            allCheckbox.checked = allChecked;
        }
    });
});

// ノードフィルター
function filterNodes() {
    const checkedCategories = Array.from(document.querySelectorAll('.category-filter:checked'))
        .map(cb => cb.value)
        .filter(v => v !== 'all');
    
    g.selectAll('.node')
        .style('opacity', d => {
            return checkedCategories.includes(d.category) ? 1 : 0.2;
        })
        .style('pointer-events', d => {
            return checkedCategories.includes(d.category) ? 'all' : 'none';
        });
    
    g.selectAll('.link')
        .style('opacity', d => {
            const source = nodes.find(n => n.id === d.source_id);
            const target = nodes.find(n => n.id === d.target_id);
            const sourceVisible = source && checkedCategories.includes(source.category);
            const targetVisible = target && checkedCategories.includes(target.category);
            return (sourceVisible && targetVisible) ? 0.6 : 0.1;
        });
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    initializeD3();
    loadData();
    
    // 定期的にデータを更新（30秒ごと）
    setInterval(() => {
        updateStats();
    }, 30000);
});
