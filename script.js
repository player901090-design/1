document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const nftParam = urlParams.get('nft'); // Например: PlushPepe-1

    const nftImage = document.getElementById('nft-image');
    const nftName = document.getElementById('nft-name');
    const nftDisplayName = document.getElementById('nft-display-name');

    // Если NFT передан в параметре
    if (nftParam) {
        // Форматируем имя для отображения (PlushPepe-1 -> Plush Pepe #1)
        let displayName = nftParam;
        const match = nftParam.match(/^([a-zA-Z]+)([A-Z][a-z]+)?-(\d+)$/);
        if (match) {
            const firstWord = match[1];
            const secondWord = match[2] || '';
            const number = match[3];
            displayName = `${firstWord} ${secondWord} #${number}`.trim();
        }

        // Устанавливаем имя
        nftName.textContent = displayName;
        nftDisplayName.textContent = displayName;

        // Пытаемся получить превью NFT через Telegram API
        // Для демо используем placeholder, в реальности нужен токен бота и вызов getAttachmen
        // Так как мы не можем делать прямые запросы к Telegram API из фронтенда без прокси,
        // здесь будет заглушка. В реальном приложении нужен бэкенд.
        
        // Заглушка: используем случайное изображение NFT
        const placeholderImages = [
            'https://via.placeholder.com/400/8a2be2/ffffff?text=NFT+Image',
            'https://via.placeholder.com/400/4a00e0/ffffff?text=Plush+Pepe',
            'https://via.placeholder.com/400/302b63/ffffff?text=ForGifts+NFT'
        ];
        const randomImage = placeholderImages[Math.floor(Math.random() * placeholderImages.length)];
        nftImage.src = randomImage;
        nftImage.alt = `${nftParam} NFT`;

        // В реальном приложении здесь должен быть запрос к вашему бэкенду,
        // который через Bot Token вызовет getAttachment и вернет URL превью.
    } else {
        // Если NFT не передан, показываем демо
        nftName.textContent = 'Lush Bouquet #27064';
        nftDisplayName.textContent = 'Plush Pepe #1';
        nftImage.src = 'https://via.placeholder.com/400/8a2be2/ffffff?text=NFT+Image';
    }

    // Обработка кнопок Withdraw
    document.querySelectorAll('.withdraw-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            alert('Withdraw function is not implemented yet.');
        });
    });
});