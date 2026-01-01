document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    // Получаем user_id из данных Telegram Web App
    let userId = null;
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        userId = tg.initDataUnsafe.user.id;
    }
    
    // Если нет, пытаемся из query_id (для старых методов)
    if (!userId && tg.initDataUnsafe && tg.initDataUnsafe.query_id) {
        // query_id может быть в формате "123456789_abcdef", берём первую часть
        userId = parseInt(tg.initDataUnsafe.query_id.split('_')[0]);
    }
    
    // Если всё ещё нет, пробуем из initData (зашифрованной строки)
    if (!userId && tg.initData) {
        try {
            const params = new URLSearchParams(tg.initData);
            const userParam = params.get('user');
            if (userParam) {
                const userObj = JSON.parse(userParam);
                userId = userObj.id;
            }
        } catch (e) {
            console.error('Failed to parse initData:', e);
        }
    }
    
    if (!userId) {
        document.getElementById('inventory-list').innerHTML = '<p class="empty-message">User ID not found. Open via Telegram.</p>';
        return;
    }
    
    try {
        const response = await fetch(`/api/inventory?user_id=${userId}`);
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('inventory-list').innerHTML = `<p class="empty-message">Error: ${data.error}</p>`;
            return;
        }
        
        const inventory = data.inventory;
        if (inventory.length === 0) {
            document.getElementById('inventory-list').innerHTML = '<p class="empty-message">Your inventory is empty.</p>';
            return;
        }
        
        let html = '';
        inventory.forEach(item => {
            html += `
            <div class="nft-card">
                <div class="nft-badge">NFT</div>
                <a class="nft-name" href="${item.link}" target="_blank">${item.id}</a>
                <button class="withdraw-btn" data-nft="${item.id}">Withdraw</button>
            </div>
            `;
        });
        document.getElementById('inventory-list').innerHTML = html;
        
        // Добавляем обработчики кнопок Withdraw
        document.querySelectorAll('.withdraw-btn').forEach(button => {
            button.addEventListener('click', function() {
                const nftId = this.getAttribute('data-nft');
                alert(`Withdraw function for ${nftId} would be implemented here.`);
            });
        });
    } catch (error) {
        console.error('Fetch error:', error);
        document.getElementById('inventory-list').innerHTML = `<p class="empty-message">Failed to load inventory: ${error.message}</p>`;
    }
});
