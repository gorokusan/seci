/**
 * コメント機能
 */

const CommentManager = {
    currentNodeId: null,
    comments: [],

    // コメントを初期化
    initComments(nodeId) {
        this.currentNodeId = nodeId;
        this.loadComments();

        // コメント追加ボタン
        const addBtn = document.getElementById('commentSubmitBtn');
        if (addBtn) {
            addBtn.addEventListener('click', async () => {
                await this.addComment();
            });
        }
    },

    // コメント一覧取得
    async loadComments() {
        if (!this.currentNodeId) return;

        try {
            const response = await window.SECIMapper.apiRequest(`/nodes/${this.currentNodeId}/comments`);
            
            if (response.success) {
                this.comments = response.comments || [];
                this.renderComments();
		
		const countText = String(this.comments.length);

		const badge = document.getElementById('commentCount');
		if (badge) badge.textContent = countText;

		const detail = document.getElementById('commentCountDetail');
		if (detail) detail.textContent = countText;
                
                // コメント数更新
                document.getElementById('commentCount').textContent = this.comments.length;
            }
        } catch (error) {
            console.error('コメント取得エラー:', error);
        }
    },

    // コメント追加
    async addComment(parentCommentId = null) {
        const input = document.getElementById('commentInput');
        const commentText = input.value.trim();

        if (!commentText) {
            window.SECIMapper.showNotification('コメントを入力してください', 'error');
            return;
        }

        try {
            const response = await window.SECIMapper.apiRequest(`/nodes/${this.currentNodeId}/comments`, {
                method: 'POST',
                body: JSON.stringify({
                    comment_text: commentText,
                    parent_comment_id: parentCommentId
                })
            });

            if (response.success) {
                window.SECIMapper.showNotification('コメントを追加しました');
                input.value = '';
                await this.loadComments();
            }
        } catch (error) {
            console.error('コメント追加エラー:', error);
        }
    },

    // コメント削除
    async deleteComment(commentId) {
        if (!confirm('このコメントを削除してもよろしいですか？')) return;

        try {
            const response = await window.SECIMapper.apiRequest(`/comments/${commentId}`, {
                method: 'DELETE'
            });

            if (response.success) {
                window.SECIMapper.showNotification('コメントを削除しました');
                await this.loadComments();
            }
        } catch (error) {
            console.error('コメント削除エラー:', error);
        }
    },

    // コメント表示
    renderComments() {
        const container = document.getElementById('commentList');
	
	if(!container) {
		console.warn('commentList 要素が見つかりません');
		return;
	}
        
        if (this.comments.length === 0) {
            container.innerHTML = '<p class="no-comments">まだコメントがありません</p>';
            return;
        }

        container.innerHTML = '';

        this.comments.forEach(comment => {
            const commentEl = this.createCommentElement(comment);
            container.appendChild(commentEl);
        });
    },

    // コメント要素作成
    createCommentElement(comment) {
        const div = document.createElement('div');
        div.className = 'comment-item';
        
        const timeAgo = this.getTimeAgo(comment.created_at);
        
        div.innerHTML = `
            <div class="comment-header">
                <span class="comment-author">匿名ユーザー</span>
                <span class="comment-time">${timeAgo}</span>
            </div>
            <div class="comment-text">${this.escapeHtml(comment.comment_text)}</div>
            <div class="comment-actions">
                <button class="comment-action-btn reply-btn" data-comment-id="${comment.id}">返信</button>
                <button class="comment-action-btn delete-btn" data-comment-id="${comment.id}">削除</button>
            </div>
        `;

        // 返信がある場合
        if (comment.replies && comment.replies.length > 0) {
            const repliesDiv = document.createElement('div');
            repliesDiv.className = 'comment-replies';
            
            comment.replies.forEach(reply => {
                const replyEl = this.createCommentElement(reply);
                replyEl.classList.add('comment-reply');
                repliesDiv.appendChild(replyEl);
            });
            
            div.appendChild(repliesDiv);
        }

        // イベントリスナー
        const deleteBtn = div.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', () => {
            this.deleteComment(comment.id);
        });

        return div;
    },

    // HTML エスケープ
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // 相対時間表示
    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // 秒

        if (diff < 60) return 'たった今';
        if (diff < 3600) return `${Math.floor(diff / 60)}分前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}時間前`;
        if (diff < 2592000) return `${Math.floor(diff / 86400)}日前`;
        
        return window.SECIMapper.formatDate(dateString);
    }
};

window.CommentManager = CommentManager;
