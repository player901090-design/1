document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    // 1. Пробуем получить user_id из URL параметра ?user_id=
    const urlParams = new URLSearchParams(window.location.search);
    let userId = urlParams.get('user_id');
    
    // 2. Если нет в URL, пробуем из Telegram Web App
    if (!userId && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        userId = tg.initDataUnsafe.user.id;
    }
    
    // 3. Резервный метод: из query_id
    if (!userId && tg.initDataUnsafe && tg.initDataUnsafe.query_id) {
        const parts = tg.initDataUnsafe.query_id.split('_');
        if (parts.length > 0 && !isNaN(parts[0])) {
            userId = parseInt(parts[0]);
        }
    }
    
    // 4. Если всё ещё нет, пробуем расшифровать initData
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
    
    // Если user_id не найден, показываем ошибку
    if (!userId) {
        document.getElementById('inventory-list').innerHTML = '<p class="empty-message">User ID not found. Open via Telegram bot.</p>';
        return;
    }
    
    // Отладочная информация (можно удалить позже)
    console.log('User ID:', userId);
    
    try {
        // Запрос к API
        const apiUrl = `/api/inventory?user_id=${userId}`;
        console.log('Fetching:', apiUrl);
        
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('API response:', data);
        
        if (data.error) {
            document.getElementById('inventory-list').innerHTML = `<p class="empty-message">Error: ${data.error}</p>`;
            return;
        }
        
        const inventory = data.inventory || [];
        if (inventory.length === 0) {
            document.getElementById('inventory-list').innerHTML = '<p class="empty-message">Your inventory is empty.</p>';
            return;
        }
        
        // Генерация квадратных карточек NFT (макс 3 в ряд)
        let html = '';
        inventory.forEach(item => {
            // Обрезаем длинное название
            const displayName = item.id.length > 20 ? item.id.substring(0, 17) + '...' : item.id;
            
            html += `
            <div class="nft-card">
                <div class="nft-badge">NFT</div>
                <a class="nft-name" href="${item.link}" target="_blank" title="${item.id}">${displayName}</a>
                <button class="withdraw-btn" data-nft="${item.id}">Withdraw</button>
            </div>
            `;
        });
        document.getElementById('inventory-list').innerHTML = html;
        
        // Обработчики кнопок Withdraw
        document.querySelectorAll('.withdraw-btn').forEach(button => {
            button.addEventListener('click', function() {
                const nftId = this.getAttribute('data-nft');
                alert(`Withdraw function for ${nftId} would be implemented here.`);
            });
        });
    } catch (error) {
        console.error('Fetch error:', error);
        document.getElementById('inventory-list').innerHTML = `<p class="empty-message">Failed to load inventory: ${error.message}. Please try again later.</p>`;
    }
});
