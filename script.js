document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    const userId = tg.initDataUnsafe?.user?.id || tg.initDataUnsafe?.query_id?.split('_')[0];
    
    if (!userId) {
        document.getElementById('inventory-list').innerHTML = '<p>User ID not found. Open via Telegram.</p>';
        return;
    }
    
    try {
        const response = await fetch(`/api/inventory?user_id=${userId}`);
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('inventory-list').innerHTML = `<p>Error: ${data.error}</p>`;
            return;
        }
        
        const inventory = data.inventory;
        if (inventory.length === 0) {
            document.getElementById('inventory-list').innerHTML = '<p>Your inventory is empty.</p>';
            return;
        }
        
        let html = '';
        inventory.forEach(item => {
            html += `
            <div class="nft-item">
                <a class="nft-name" href="${item.link}" target="_blank">${item.id}</a>
            </div>
            `;
        });
        document.getElementById('inventory-list').innerHTML = html;
    } catch (error) {
        document.getElementById('inventory-list').innerHTML = `<p>Failed to load inventory: ${error.message}</p>`;
    }
});