/**
 * タグ機能
 */

const TagManager = {
    allTags: [],
    selectedTags: [],
    currentNodeTags: [],

    //タグ候補の更新
    updateTagSuggestions() {
	    const input = document.getElementById('nodeTagInput');
	    const query = input
	    	? input.value.toLowerCase().replace('#', '')
	    	: '';

	    this.showTagSuggestions(query);
    },
 
    // タグ一覧取得
    async loadAllTags() {
        try {
            const response = await window.SECIMapper.apiRequest('/tags');
            this.allTags = response.tags || [];
            this.updateTagSuggestions();
            this.updateTagFilterList();
        } catch (error) {
            console.error('タグ取得エラー:', error);
        }
    },

    // タグ作成
    async createTag(name, color = '#6C757D') {
        try {
            const response = await window.SECIMapper.apiRequest('/tags', {
                method: 'POST',
                body: JSON.stringify({ name, color })
            });
            
            if (response.success) {
                this.allTags.push(response.tag);
                this.updateTagSuggestions();
                this.updateTagFilterList();
                return response.tag;
            }
        } catch (error) {
            console.error('タグ作成エラー:', error);
        }
    },

    // タグをノードに追加
    async addTagToNode(nodeId, tagId) {
        try {
            const response = await window.SECIMapper.apiRequest(`/nodes/${nodeId}/tags`, {
                method: 'POST',
                body: JSON.stringify({ tag_id: tagId })
            });
            return response.success;
        } catch (error) {
            console.error('タグ追加エラー:', error);
            return false;
        }
    },

    // タグをノードから削除
    async removeTagFromNode(nodeId, tagId) {
        try {
            const response = await window.SECIMapper.apiRequest(`/nodes/${nodeId}/tags/${tagId}`, {
                method: 'DELETE'
            });
            return response.success;
        } catch (error) {
            console.error('タグ削除エラー:', error);
            return false;
        }
    },

    // タグ入力の初期化
    initTagInput() {
        const input = document.getElementById('nodeTagInput');
        const tagsList = document.getElementById('nodeTagsList');

        input.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const tagName = input.value.trim().replace('#', '');
                
                if (tagName) {
                    await this.addSelectedTag(tagName);
                    input.value = '';
                }
            }
        });

        input.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().replace('#', '');
            this.showTagSuggestions(query);
        });
    },

    // 選択されたタグを追加
    async addSelectedTag(tagName) {
        // 既に選択されているかチェック
        if (this.selectedTags.some(t => t.name === tagName)) {
            return;
        }

        // 既存タグから検索
        let tag = this.allTags.find(t => t.name === tagName);

        // 存在しなければ作成
        if (!tag) {
            tag = await this.createTag(tagName);
        }

        if (tag) {
            this.selectedTags.push(tag);
            this.renderSelectedTags();
        }
    },

    // 選択されたタグを表示
    renderSelectedTags() {
        const container = document.getElementById('nodeTagsList');
        container.innerHTML = '';

        this.selectedTags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag-item';
            tagEl.style.backgroundColor = tag.color;
            tagEl.innerHTML = `
                #${tag.name}
                <button type="button" class="tag-remove" data-tag-id="${tag.id}">×</button>
            `;
            container.appendChild(tagEl);
        });

        // 削除ボタンのイベント
        container.querySelectorAll('.tag-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tagId = e.target.dataset.tagId;
                this.selectedTags = this.selectedTags.filter(t => t.id !== tagId);
                this.renderSelectedTags();
            });
        });
    },

    // タグ候補表示
    showTagSuggestions(query) {
        const container = document.getElementById('tagSuggestions');
        
        if (!query) {
            container.innerHTML = '';
            return;
        }

        const suggestions = this.allTags.filter(tag => 
            tag.name.toLowerCase().includes(query) &&
            !this.selectedTags.some(t => t.id === tag.id)
        ).slice(0, 5);

        container.innerHTML = '';

        suggestions.forEach(tag => {
            const item = document.createElement('div');
            item.className = 'tag-suggestion-item';
            item.style.borderLeftColor = tag.color;
            item.textContent = `#${tag.name}`;
            item.addEventListener('click', () => {
                this.selectedTags.push(tag);
                this.renderSelectedTags();
                document.getElementById('nodeTagInput').value = '';
                container.innerHTML = '';
            });
            container.appendChild(item);
        });
    },

    //タグ候補の更新
    updateTagSuggestions() {
	    const input = document.getElementById('nodeTagInput');
	    const query = input
	    	? input.value.toLowerCase().replace('#', '')
	    	: '';

	    this.showTagSuggestions(query);
    },
    

    // ノードのタグを表示
    displayNodeTags(tags, container) {
        container.innerHTML = '';
        
        if (!tags || tags.length === 0) {
            container.innerHTML = '<span class="no-tags">タグなし</span>';
            return;
        }

        tags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag-badge';
            tagEl.style.backgroundColor = tag.color;
            tagEl.textContent = `#${tag.name}`;
            container.appendChild(tagEl);
        });
    },

    // タグフィルターリスト表示
    updateTagFilterList() {
        const container = document.getElementById('tagFilterList');

	if(!container) {
		return;
	}

	container.innerHTML = '';	

        if (this.allTags.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">タグがありません</p>';
            return;
        }

        this.allTags.forEach(tag => {
            const tagEl = document.createElement('button');
            tagEl.className = 'tag-filter-item';
	    tagEl.textContent = `#${tag.name}`;
            tagEl.style.borderColor = tag.color;
            tagEl.addEventListener('click', () => {
                this.toggleTagFilter(tag);
            });
            container.appendChild(tagEl);
        });

        // フィルターイベント
        container.querySelectorAll('.tag-filter-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.applyTagFilter();
            });
        });
    },

    // タグフィルター適用
    applyTagFilter() {
        const checkedTags = Array.from(document.querySelectorAll('.tag-filter-checkbox:checked'))
            .map(cb => cb.value);

        // TODO: マッピングビューにフィルターを適用
        console.log('フィルター適用:', checkedTags);
    },

    // 選択状態をリセット
    reset() {
        this.selectedTags = [];
        this.renderSelectedTags();
    }
};

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    TagManager.loadAllTags();
    TagManager.initTagInput();
});

window.TagManager = TagManager;
