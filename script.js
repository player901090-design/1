document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    const userId = tg.initDataUnsafe?.user?.id || tg.initDataUnsafe?.query_id?.split('_')[0];
    
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
                // В будущем здесь можно добавить логику вывода NFT
            });
        });
    } catch (error) {
        document.getElementById('inventory-list').innerHTML = `<p class="empty-message">Failed to load inventory: ${error.message}</p>`;
    }
});
