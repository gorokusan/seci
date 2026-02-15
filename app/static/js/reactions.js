/**
 * リアクション機能（いいね・スター・ブックマーク）
 */

const ReactionManager = {
    currentNodeId: null,
    userReactions: [],

    // リアクションを初期化
    initReactions(nodeId) {
        this.currentNodeId = nodeId;
        this.loadReactions();

        // リアクションボタンのイベント
        ['likeBtn', 'starBtn', 'bookmarkBtn'].forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.addEventListener('click', async (e) => {
                    const type = btn.dataset.type;
                    await this.toggleReaction(type);
                });
            }
        });
    },

    // リアクション取得
    async loadReactions() {
        if (!this.currentNodeId) return;

        try {
            const response = await window.SECIMapper.apiRequest(`/nodes/${this.currentNodeId}/reactions`);
            
            if (response.success) {
                this.updateReactionUI(response.counts, response.user_reactions);
                this.userReactions = response.user_reactions;
            }
        } catch (error) {
            console.error('リアクション取得エラー:', error);
        }
    },

    // リアクションをトグル
    async toggleReaction(type) {
        if (!this.currentNodeId) return;

        try {
            const response = await window.SECIMapper.apiRequest(`/nodes/${this.currentNodeId}/reactions`, {
                method: 'POST',
                body: JSON.stringify({ type })
            });

            if (response.success) {
                const action = response.action;
                
                if (action === 'added') {
                    window.SECIMapper.showNotification(`${this.getReactionLabel(type)}を追加しました`);
                } else {
                    window.SECIMapper.showNotification(`${this.getReactionLabel(type)}を解除しました`);
                }

                // 再読み込み
                await this.loadReactions();
                
                // ブックマークの場合、サイドバーも更新
                if (type === 'bookmark') {
                    await this.loadBookmarks();
                }
            }
        } catch (error) {
            console.error('リアクションエラー:', error);
        }
    },

    // リアクションUI更新
    updateReactionUI(counts, userReactions) {
        // カウント更新
        document.getElementById('likeCount').textContent = counts.likes || 0;
        document.getElementById('starCount').textContent = counts.stars || 0;
        document.getElementById('bookmarkCount').textContent = counts.bookmarks || 0;

        // ボタンの状態更新
        ['like', 'star', 'bookmark'].forEach(type => {
            const btn = document.getElementById(type + 'Btn');
            if (btn) {
                if (userReactions.includes(type)) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }
        });
    },

    // リアクションラベル取得
    getReactionLabel(type) {
        const labels = {
            'like': 'いいね',
            'star': 'スター',
            'bookmark': 'ブックマーク'
        };
        return labels[type] || type;
    },

    // ブックマーク一覧を読み込み
    async loadBookmarks() {
        try {
            // 全ノードを取得してブックマークされているものをフィルター
            const response = await window.SECIMapper.apiRequest('/nodes');
            const nodes = response.nodes || [];
            
            // ブックマークされているノードのIDを取得する必要があるため、
            // 各ノードのリアクション情報も取得する（実装簡略化のため省略可）
            
            const container = document.getElementById('bookmarkList');
            container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">ブックマーク機能は開発中</p>';
            
        } catch (error) {
            console.error('ブックマーク取得エラー:', error);
        }
    }
};

window.ReactionManager = ReactionManager;
