document.addEventListener('DOMContentLoaded', function() {
    const nftContainer = document.getElementById('nft-container');
    const emptyMessage = document.getElementById('empty-message');

    // Simulated data - in a real app, this would come from a server API
    // For demo, we get NFT from URL parameter ?nft=PlushPepe-1
    const urlParams = new URLSearchParams(window.location.search);
    const nftParam = urlParams.get('nft');

    let nfts = [];

    // If there's an NFT in URL, add it to the list
    if (nftParam) {
        // Extract name and number (e.g., PlushPepe-1 -> PlushPepe #1)
        const match = nftParam.match(/^([a-zA-Z0-9]+)-(\d+)$/);
        let displayName = nftParam;
        if (match) {
            displayName = `${match[1]} #${match[2]}`;
        }
        nfts.push({
            id: nftParam,
            displayName: displayName,
            icon: 'fas fa-gem' // default icon
        });
    }

    // If no NFTs, show empty message
    if (nfts.length === 0) {
        emptyMessage.style.display = 'block';
        nftContainer.style.display = 'none';
    } else {
        emptyMessage.style.display = 'none';
        nfts.forEach(nft => {
            const nftCard = document.createElement('div');
            nftCard.className = 'nft-card';
            nftCard.innerHTML = `
                <div class="nft-icon">
                    <i class="${nft.icon}"></i>
                </div>
                <div class="nft-name">${nft.id}</div>
                <div class="nft-id">${nft.displayName}</div>
                <button class="take-btn">Take</button>
            `;
            nftContainer.appendChild(nftCard);
        });

        // Add event listener to Take buttons
        document.querySelectorAll('.take-btn').forEach(button => {
            button.addEventListener('click', function() {
                alert('NFT claimed!');
            });
        });
    }
});