// 获取 DOM 元素
const analyzeBtn = document.getElementById('analyzeBtn');
const chatInput = document.getElementById('chatInput');
const chatDate = document.getElementById('chatDate');
const loading = document.getElementById('loading');
const resultSection = document.getElementById('resultSection');
const moodResult = document.getElementById('moodResult');
const historyList = document.getElementById('historyList');

// 设置默认日期为今天
chatDate.valueAsDate = new Date();

// 点击分析按钮
analyzeBtn.addEventListener('click', async () => {
    const text = chatInput.value.trim();
    const date = chatDate.value;
    if (!text) {
        alert("请先粘贴聊天记录哦！");
        return;
    }

    // 显示加载动画，隐藏旧结果
    loading.classList.remove('hidden');
    resultSection.classList.add('hidden');
    analyzeBtn.disabled = true;

    try {
        // 发送 POST 请求给 Vercel 后端（包含 date 参数）
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, date: date })
        });
        const data = await response.json();

        // 处理错误
        if (data.error) {
            throw new Error(data.error);
        }

        // 展示结果
        moodResult.innerText = data.data.result.mood;
        resultSection.classList.remove('hidden');

        // 清空输入框并刷新历史
        chatInput.value = '';
        fetchHistory();
    } catch (error) {
        alert("分析出错了：" + error.message);
    } finally {
        loading.classList.add('hidden');
        analyzeBtn.disabled = false;
    }
});

// 获取历史记录
async function fetchHistory() {
    try {
        const response = await fetch('/api/analyze');
        const data = await response.json();
        // 渲染历史列表
        historyList.innerHTML = '';
        const history = data.history.reverse(); // 倒序显示（最新在上）
        if (history.length === 0) {
            historyList.innerHTML = '<p style="text-align:center; color:#ff69b4;">还没有分析记录哦~</p>';
            return;
        }
        history.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <div>
                    <div class="history-date">📅 ${item.date}</div>
                    <div style="font-size:0.9rem; color:#666; margin-top:5px;">${item.preview}</div>
                </div>
                <div class="history-mood">${item.result.mood}</div>
            `;
            historyList.appendChild(div);
        });
    } catch (error) {
        console.error("获取历史失败", error);
    }
}

// 页面加载时获取一次历史
fetchHistory();
