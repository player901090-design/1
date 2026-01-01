document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    let userId = null;
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        userId = tg.initDataUnsafe.user.id;
    }
    
    if (!userId && tg.initDataUnsafe && tg.initDataUnsafe.query_id) {
        userId = parseInt(tg.initDataUnsafe.query_id.split('_')[0]);
    }
    
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
