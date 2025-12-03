const { app, BrowserWindow, shell, globalShortcut, ipcMain } = require('electron');
const https = require('https');
const path = require('path');
const fs = require('fs');

let mainWindow;
let latestChromeVersion = '133.0.6943.35';  // Fallback default version

const settingsFilePath = path.join(app.getPath('userData'), 'settings.json');
const defaultURL = 'https://dofusdb.fr/fr/tools/treasure-hunt';
const betaURL = 'https://beta.dofusdb.fr/fr/tools/treasure-hunt';
const availableLanguages = ['fr', 'en', 'pt', 'es', 'de'];
const defaultLanguage = 'fr';

// Default configuration
const defaultConfig = {
    bounds: { x: 0, y: 0, width: 320, height: 700 },
    url: `https://dofusdb.fr/${defaultLanguage}/tools/treasure-hunt`,
    language: defaultLanguage,
    isFrame: true
};

// Load configuration from file
function loadConfig() {
    try {
        if (fs.existsSync(settingsFilePath)) {
            const data = fs.readFileSync(settingsFilePath, 'utf-8');
            const parsedConfig = JSON.parse(data);

            // Ensure default values if necessary
            parsedConfig.bounds = parsedConfig.bounds || defaultConfig.bounds;
            parsedConfig.url = parsedConfig.url || defaultConfig.url;
            parsedConfig.language = parsedConfig.language || defaultConfig.language;

            return parsedConfig;
        }
    } catch (err) {
        console.error('Failed to load configuration:', err);
    }
    return defaultConfig; // Return default config if error occurs
}

// Save configuration to file
function saveConfig(config) {
    try {
        fs.writeFileSync(settingsFilePath, JSON.stringify(config, null, 2));
    } catch (err) {
        console.error('Failed to save configuration:', err);
    }
}

const config = loadConfig();
let isFrame = config.isFrame !== undefined ? config.isFrame : true;

// Function to fetch the latest Chrome version
function fetchLatestChromeVersion() {
    return new Promise((resolve, reject) => {
        const url = 'https://versionhistory.googleapis.com/v1/chrome/platforms/win/channels/stable/versions';

        https.get(url, (res) => {
            let data = '';

            res.on('data', chunk => {
                data += chunk;
            });

            res.on('end', () => {
                try {
                    const parsedData = JSON.parse(data);
                    if (parsedData.versions && parsedData.versions.length > 0) {
                        resolve(parsedData.versions[0].version);
                    } else {
                        reject(new Error('No versions found in the response'));
                    }
                } catch (err) {
                    reject(err);
                }
            });
        }).on('error', err => {
            reject(err);
        });
    });
}

// Function to create a window with the frame setting and position
function createWindow(frame) {
    const lastWindowBounds = config.bounds;

    mainWindow = new BrowserWindow({
        width: lastWindowBounds.width,
        height: lastWindowBounds.height,
        x: lastWindowBounds.x,
        y: lastWindowBounds.y,
        frame: false,  // No border for transparent effect
        transparent: true,  // Make the window transparent
        alwaysOnTop: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        }
    });

    // Allow dragging on the body
    mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.executeJavaScript(`
            const { ipcRenderer } = require('electron');

            let isMouseDown = false;
            let offsetX = 0;
            let offsetY = 0;

            document.body.addEventListener('mousedown', (e) => {
                if (e.button === 0) {  // Left click
                    isMouseDown = true;
                    offsetX = e.clientX;
                    offsetY = e.clientY;
                }
            });

            document.body.addEventListener('mousemove', (e) => {
                if (isMouseDown) {
                    const deltaX = e.clientX - offsetX;
                    const deltaY = e.clientY - offsetY;
                    ipcRenderer.send('move-window', deltaX, deltaY);
                }
            });

            document.body.addEventListener('mouseup', () => {
                isMouseDown = false;
            });
        `);
    });

    mainWindow.setIgnoreMouseEvents(false); // Allow interaction
    mainWindow.setAlwaysOnTop(true, "screen-saver");

    mainWindow.loadURL(config.url);
    mainWindow.setMenu(null);

    // Clear cache and cookies before loading the page
    const session = mainWindow.webContents.session;
    session.clearCache();
    session.clearStorageData({ storages: ['cookies'] })
        .then(() => {
            console.log('Cache and cookies cleared successfully.');
        })
        .catch(err => {
            console.error('Failed to clear cache or cookies:', err);
        });

    mainWindow.webContents.setUserAgent(
        `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${latestChromeVersion} Safari/537.36`
    );

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// Function to move the window
ipcMain.on('move-window', (event, deltaX, deltaY) => {
    const currentBounds = mainWindow.getBounds();
    mainWindow.setBounds({
        x: currentBounds.x + deltaX,
        y: currentBounds.y + deltaY,
        width: currentBounds.width,
        height: currentBounds.height
    });
});

function toggleURL() {
    const baseURL = config.url.includes('beta') ? defaultURL : betaURL;
    config.url = baseURL.replace('/fr/', `/${config.language}/`);
    saveConfig(config);
    if (mainWindow) {
        mainWindow.loadURL(config.url);
    } else {
        createWindow(isFrame);
    }
}

function toggleLanguage() {
    const currentIndex = availableLanguages.indexOf(config.language);
    const nextIndex = (currentIndex + 1) % availableLanguages.length;
    config.language = availableLanguages[nextIndex];
    const baseURL = config.url.includes('beta') ? betaURL : defaultURL;
    config.url = baseURL.replace('/fr/', `/${config.language}/`);
    saveConfig(config);
    if (mainWindow) {
        mainWindow.loadURL(config.url);
    } else {
        createWindow(isFrame);
    }
}

app.whenReady().then(async () => {
    try {
        latestChromeVersion = await fetchLatestChromeVersion();
        console.log(`Latest Chrome version fetched: ${latestChromeVersion}`);
    } catch (error) {
        console.error('Failed to fetch the latest Chrome version:', error);
    }

    createWindow(isFrame);

    globalShortcut.register('Control+F2', () => {
        isFrame = !isFrame;
        config.isFrame = isFrame;
        saveConfig(config);
        BrowserWindow.getAllWindows().forEach(window => window.close());
        createWindow(isFrame);
    });

    globalShortcut.register('Control+F3', toggleLanguage);
    globalShortcut.register('Control+F4', toggleURL);
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow(isFrame);
    }
});
