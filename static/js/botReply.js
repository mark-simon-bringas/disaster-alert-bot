const sidebarRight = document.getElementById('sidebar-right');
const chatMain = document.getElementById('chat-main');

function toggleRightSidebar() {
    if (sidebarRight.classList.contains('d-lg-block')) {
        sidebarRight.classList.remove('d-lg-block');
    } else {
        sidebarRight.classList.add('d-lg-block');
    }
    adjustMainColumn();
}

function adjustMainColumn() {
    chatMain.className = 'chat-main col-12'; 
    if (sidebarRight.classList.contains('d-lg-block')) {
        chatMain.classList.add('col-lg-6');
    } else {
        chatMain.classList.add('col-lg-9');
    }
}

const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const loadingDots = document.getElementById('loading-dots');

function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function getCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    const minutesStr = minutes < 10 ? '0' + minutes : minutes;
    return `${hours}:${minutesStr} ${ampm}`;
}

function formatBotMessage(text) {
    let formatted = text;
    
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.match(/^\d+\.\s/)) {
            if (!inList) {
                result.push('<ol>');
                inList = 'ol';
            }
            const content = line.replace(/^\d+\.\s/, '');
            result.push(`<li>${content}</li>`);
        } else if (line.match(/^[\-\*]\s/)) {
            if (!inList) {
                result.push('<ul>');
                inList = 'ul';
            }
            const content = line.replace(/^[\-\*]\s/, '');
            result.push(`<li>${content}</li>`);
        } else {
            if (inList) {
                result.push(inList === 'ol' ? '</ol>' : '</ul>');
                inList = false;
            }
            
            if (line === '') {
                result.push('</p><p>');
            } else {
                result.push(line + '<br>');
            }
        }
    }
    
    if (inList) {
        result.push(inList === 'ol' ? '</ol>' : '</ul>');
    }
    
    formatted = '<p>' + result.join('') + '</p>';
    
    formatted = formatted.replace(/<br><\/p>/g, '</p>');
    formatted = formatted.replace(/<p><\/p>/g, '');
    formatted = formatted.replace(/<p><br>/g, '<p>');
    
    return formatted;
}

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    const bubbleDiv = document.createElement('div');
    bubbleDiv.classList.add('bubble', sender);
    
    if (sender === 'bot') {
        bubbleDiv.innerHTML = formatBotMessage(text);
    } else {
        bubbleDiv.textContent = text;
    }
    
    const timeSpan = document.createElement('span');
    timeSpan.classList.add('msg-time');
    timeSpan.innerText = getCurrentTime();
    msgDiv.appendChild(bubbleDiv);
    msgDiv.appendChild(timeSpan);
    chatWindow.insertBefore(msgDiv, loadingDots);
    scrollToBottom();
}

async function botReply(userMessage) {
    loadingDots.style.display = 'flex';
    scrollToBottom();
    
    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: userMessage,
                location: getSelectedCity()
            })
        });
        
        const data = await response.json();
        
        loadingDots.style.display = 'none';
        
        if (data.answer) {
            addMessage(data.answer, "bot");
        } else {
            addMessage('Sorry, I encountered an error processing your request.', "bot");
        }
        
    } catch (error) {
        loadingDots.style.display = 'none';
        addMessage('Sorry, I could not connect to the server. Please try again.', "bot");
        console.error('Error:', error);
    }
}

function handleSend() {
    const text = userInput.value.trim();
    if (text) {
        addMessage(text, "user");
        userInput.value = '';
        botReply(text);
    }
}

sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

const desktopTrigger = document.getElementById('desktop-location-trigger');
const desktopMenu = document.getElementById('desktop-location-dropdown');

const mobileTrigger = document.getElementById('mobile-location-trigger');
const mobileMenu = document.getElementById('mobile-location-dropdown');

const profileTrigger = document.getElementById('mobile-profile-trigger');
const profileMenu = document.getElementById('mobile-profile-dropdown');

function toggleMenu(menu) {
    const isVisible = menu.style.display === 'block';
    desktopMenu.style.display = 'none';
    mobileMenu.style.display = 'none';
    profileMenu.style.display = 'none';
    
    if (!isVisible) {
        menu.style.display = 'block';
    }
}

window.addEventListener('click', (e) => {
    if (desktopTrigger && !desktopTrigger.contains(e.target) && !desktopMenu.contains(e.target)) {
        desktopMenu.style.display = 'none';
    }
    if (mobileTrigger && !mobileTrigger.contains(e.target) && !mobileMenu.contains(e.target)) {
        mobileMenu.style.display = 'none';
    }
    if (profileTrigger && !profileTrigger.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.style.display = 'none';
    }
});

if(desktopTrigger) desktopTrigger.addEventListener('click', () => toggleMenu(desktopMenu));
if(mobileTrigger) mobileTrigger.addEventListener('click', () => toggleMenu(mobileMenu));
if(profileTrigger) profileTrigger.addEventListener('click', () => toggleMenu(profileMenu));

function updateLocation(locationName) {
    document.getElementById('desktop-location-text').innerText = locationName;
    document.getElementById('mobile-location-text').innerText = locationName;
    const weatherText = document.getElementById('weather-location-text');
    if(weatherText) weatherText.innerText = locationName;
    desktopMenu.style.display = 'none';
    mobileMenu.style.display = 'none';
}

function detectLocation() {
    const originalTextDesktop = document.getElementById('desktop-location-text').innerText;
    document.getElementById('desktop-location-text').innerText = "Locating...";
    document.getElementById('mobile-location-text').innerText = "Locating...";

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showPosition, showError);
    } else {
        alert("Geolocation is not supported by this browser.");
        updateLocation(originalTextDesktop);
    }
}

function showPosition(position) {
    setTimeout(() => { updateLocation("Detected: Manila"); }, 1000);
}

function showError(error) {
    updateLocation("Metro Manila"); 
}