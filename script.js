document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    const urlParams = new URLSearchParams(window.location.search);
    let userId = urlParams.get('user_id');
    
    if (!userId && tg.initDataUnsafe?.user?.id) {
        userId = tg.initDataUnsafe.user.id;
    }
    
    if (!userId) {
        document.getElementById('inventory-list').innerHTML = '<p class="empty-message">Open via Telegram bot to view inventory.</p>';
        return;
    }
    
    try {
        const response = await fetch(`/api/inventory?user_id=${userId}`);
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        
        const data = await response.json();
        if (data.error) {
            document.getElementById('inventory-list').innerHTML = `<p class="empty-message">${data.error}</p>`;
            return;
        }
        
        const inventory = data.inventory || [];
        if (inventory.length === 0) {
            document.getElementById('inventory-list').innerHTML = '<p class="empty-message">No NFTs yet.</p>';
            return;
        }
        
        let html = '';
        inventory.forEach(item => {
            const shortName = item.id.length > 20 ? item.id.substring(0, 18) + '...' : item.id;
            
            html += `
            <div class="nft-card">
                <div class="nft-badge">NFT</div>
                <div class="nft-content">
                    <div class="nft-icon-container">
                        <img class="nft-icon" src="${item.icon || 'https://cdn-icons-png.flaticon.com/512/5968/5968804.png'}" alt="${item.id}" onerror="this.src='https://cdn-icons-png.flaticon.com/512/5968/5968804.png'">
                    </div>
                    <a class="nft-name" href="${item.link}" target="_blank" title="${item.id}">${shortName}</a>
                    <button class="withdraw-btn" data-nft="${item.id}">Withdraw</button>
                </div>
            </div>
            `;
        });
        
        document.getElementById('inventory-list').innerHTML = html;
        
        document.querySelectorAll('.withdraw-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const nftId = this.getAttribute('data-nft');
                tg.showPopup({
                    title: 'Withdraw',
                    message: `Withdraw ${nftId}?`,
                    buttons: [
                        {id: 'yes', type: 'default', text: 'Confirm'},
                        {type: 'cancel'}
                    ]
                }, (btnId) => {
                    if (btnId === 'yes') {
                        tg.showAlert(`Withdrawal request sent for ${nftId}`);
                    }
                });
            });
        });
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('inventory-list').innerHTML = '<p class="empty-message">Failed to load. Try again later.</p>';
    }
});
