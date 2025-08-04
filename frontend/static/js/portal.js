// Global variables
let currentSection = 'providers';
let editingProvider = null;
let editingApiKey = null;
let currentUser = null;
let providerViewMode = 'list'; // 'list' or 'card'
let modelEditMode = false;

// Theme management
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        document.documentElement.classList.add('dark');
        updateThemeIcon('dark');
    } else {
        document.documentElement.classList.remove('dark');
        updateThemeIcon('light');
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark ? 'dark' : 'light');
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun mr-1' : 'fas fa-moon mr-1';
    }
}

// API Base URL
const API_BASE = '';

// Authentication check
function checkAuth() {
    const token = localStorage.getItem('portal_token');
    if (!token) {
        window.location.href = '/portal/login';
        return false;
    }
    return true;
}

// Add authorization header to fetch requests
async function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('portal_token');
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };
    
    const response = await fetch(url, { ...options, headers });
    
    // If unauthorized, redirect to login
    if (response.status === 401) {
        localStorage.removeItem('portal_token');
        window.location.href = '/portal/login';
        return response;
    }
    
    return response;
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) return;
    initTheme();
    loadData();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Database type change
    document.getElementById('database-type').addEventListener('change', function() {
        const supabaseFields = document.getElementById('supabase-fields');
        if (this.value === 'supabase') {
            supabaseFields.classList.remove('hidden');
        } else {
            supabaseFields.classList.add('hidden');
        }
    });

    // Form submissions
    document.getElementById('provider-form').addEventListener('submit', handleProviderSubmit);
    document.getElementById('api-key-form').addEventListener('submit', handleApiKeySubmit);
    
    // Provider type change for auto-populating URLs
    document.getElementById('provider-type').addEventListener('change', handleProviderTypeChange);

    // Close modals on outside click
    window.addEventListener('click', function(event) {
        const providerModal = document.getElementById('provider-modal');
        const apiKeyModal = document.getElementById('api-key-modal');
        
        if (event.target === providerModal) {
            hideProviderModal();
        }
        if (event.target === apiKeyModal) {
            hideApiKeyModal();
        }
    });
}

// Navigation
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });
    
    // Show selected section
    document.getElementById(`${sectionName}-section`).classList.remove('hidden');
    
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('border-indigo-500', 'text-gray-900');
        link.classList.add('border-transparent', 'text-gray-500');
    });
    
    document.querySelectorAll('.mobile-nav-link').forEach(link => {
        link.classList.remove('bg-indigo-50', 'border-indigo-500', 'text-indigo-700');
        link.classList.add('border-transparent', 'text-gray-500');
    });
    
    // Active navigation item
    const activeLink = document.querySelector(`button[onclick="showSection('${sectionName}')"]`);
    if (activeLink) {
        activeLink.classList.remove('border-transparent', 'text-gray-500');
        activeLink.classList.add('border-indigo-500', 'text-gray-900');
    }
    
    currentSection = sectionName;
}

// Load data from API
async function loadData() {
    try {
        await Promise.all([
            loadUserInfo(),
            loadProviders(),
            loadApiKeys(),
            loadSettings(),
            loadProviderSelect(),
            loadStrategies()
        ]);
        updateStatus('Connected', 'success');
    } catch (error) {
        console.error('Error loading data:', error);
        updateStatus('Connection Error', 'error');
    }
}

// Load user info
async function loadUserInfo() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/user-info`);
        if (!response.ok) throw new Error('Failed to load user info');
        
        currentUser = await response.json();
        updateUIForUserRole();
    } catch (error) {
        console.error('Error loading user info:', error);
        showError('Failed to load user information');
    }
}

// Update UI based on user role
function updateUIForUserRole() {
    if (!currentUser) return;
    
    const isAdmin = currentUser.is_admin;
    
    // Show/hide admin-only elements
    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(element => {
        element.style.display = isAdmin ? '' : 'none';
    });
    
    // Show/hide read-only elements
    const readOnlyElements = document.querySelectorAll('.read-only-only');
    readOnlyElements.forEach(element => {
        element.style.display = isAdmin ? 'none' : '';
    });
    
    // Hide settings navigation for non-admin users
    if (!isAdmin) {
        // If currently on settings page, redirect to providers
        if (currentSection === 'settings') {
            showSection('providers');
        }
    }
    
    // Update user info display
    const userInfoElement = document.getElementById('user-info');
    if (userInfoElement) {
        userInfoElement.innerHTML = `
            <span class="text-sm text-gray-500 dark:text-gray-300">
                ${currentUser.username} 
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${isAdmin ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}">
                    ${isAdmin ? 'Admin' : 'Read-Only'}
                </span>
            </span>
        `;
    }
}

// Load providers
async function loadProviders() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers`);
        if (!response.ok) throw new Error('Failed to load providers');
        
        const providers = await response.json();
        renderProviders(providers);
    } catch (error) {
        console.error('Error loading providers:', error);
        showError('Failed to load providers');
    }
}

// Load API keys
async function loadApiKeys() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/api-keys`);
        if (!response.ok) throw new Error('Failed to load API keys');
        
        const apiKeys = await response.json();
        renderApiKeys(apiKeys);
    } catch (error) {
        console.error('Error loading API keys:', error);
        showError('Failed to load API keys');
    }
}

// Load settings
async function loadSettings() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/settings`);
        if (!response.ok) throw new Error('Failed to load settings');
        
        const settings = await response.json();
        
        document.getElementById('database-type').value = settings.database_type;
        document.getElementById('database-url').value = settings.database_url;
        document.getElementById('supabase-url').value = settings.supabase_url || '';
        
        // Show/hide supabase fields based on database type
        const supabaseFields = document.getElementById('supabase-fields');
        if (settings.database_type === 'supabase') {
            supabaseFields.classList.remove('hidden');
        } else {
            supabaseFields.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        // Fallback to defaults
        document.getElementById('database-type').value = 'sqlite';
        document.getElementById('database-url').value = 'sqlite:///./portbroker.db';
    }
}

// Render providers
function renderProviders(providers) {
    const container = document.getElementById('providers-list');
    
    if (providers.length === 0) {
        container.innerHTML = `
            <div class="p-8 text-center text-gray-500">
                <i class="fas fa-server text-4xl mb-4"></i>
                <p class="text-lg font-medium">No providers configured</p>
                <p class="text-sm">Click "Add Provider" to get started.</p>
            </div>
        `;
        return;
    }
    
    if (providerViewMode === 'card') {
        renderProviderCards(providers);
    } else {
        renderProviderList(providers);
    }
}

// Render providers as cards
function renderProviderCards(providers) {
    const container = document.getElementById('providers-list');
    container.className = 'p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6';
    
    container.innerHTML = providers.map(provider => `
        <div class="bg-white dark:bg-gray-700 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-600 hover:shadow-lg transition-shadow">
            <div class="flex items-start justify-between mb-4">
                <div class="flex items-center space-x-3">
                    <div class="w-12 h-12 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center">
                        <i class="fas fa-server text-indigo-600 dark:text-indigo-300"></i>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${provider.name}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${provider.provider_type}</p>
                    </div>
                </div>
                <div class="flex items-center space-x-1">
                    ${provider.is_active ? 
                        '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Active</span>' :
                        '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Inactive</span>'
                    }
                </div>
            </div>
            
            <div class="space-y-3">
                <div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Base URL</p>
                    <p class="text-sm text-gray-900 dark:text-white truncate">${provider.base_url}</p>
                </div>
                
                <div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Models</p>
                    <div class="flex flex-wrap gap-1 mt-1">
                        ${(provider.model_list || []).slice(0, 3).map(model => 
                            `<span class="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">${model}</span>`
                        ).join('')}
                        ${(provider.model_list || []).length > 3 ? 
                            `<span class="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 rounded">+${(provider.model_list || []).length - 3} more</span>` : ''
                        }
                    </div>
                </div>
                
                <div class="flex items-center justify-between pt-2">
                    ${provider.priority && provider.priority !== 'undefined' ? `<span class="text-xs text-gray-500 dark:text-gray-400">Priority: ${provider.priority}</span>` : '<span></span>'}
                    <div class="flex items-center space-x-2">
                        <button onclick="viewProvider(${provider.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 rounded-full hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors" title="View details">
                            <i class="fas fa-eye text-sm"></i>
                        </button>
                        ${currentUser.is_admin ? `
                            <button onclick="editProvider(${provider.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 rounded-full hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors" title="Edit">
                                <i class="fas fa-edit text-sm"></i>
                            </button>
                            <button onclick="toggleProviderStatus(${provider.id}, ${!provider.is_active})" class="p-2 text-${provider.is_active ? 'yellow' : 'green'}-600 hover:text-${provider.is_active ? 'yellow' : 'green'}-900 dark:text-${provider.is_active ? 'yellow' : 'green'}-400 rounded-full hover:bg-${provider.is_active ? 'yellow' : 'green'}-50 dark:hover:bg-${provider.is_active ? 'yellow' : 'green'}-900/20 transition-colors" title="${provider.is_active ? 'Deactivate' : 'Activate'}">
                                <i class="fas fa-${provider.is_active ? 'pause' : 'play'} text-sm"></i>
                            </button>
                            <button onclick="deleteProvider(${provider.id})" class="p-2 text-red-600 hover:text-red-900 dark:text-red-400 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Delete">
                                <i class="fas fa-trash text-sm"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Render providers as list
function renderProviderList(providers) {
    const container = document.getElementById('providers-list');
    container.className = 'divide-y divide-gray-200 dark:divide-gray-700';
    
    container.innerHTML = providers.map(provider => `
        <div class="p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="w-12 h-12 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center">
                        <i class="fas fa-server text-indigo-600 dark:text-indigo-300"></i>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${provider.name}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${provider.provider_type} • ${provider.base_url}</p>
                        <div class="flex items-center space-x-3 mt-2">
                            ${provider.is_active ? 
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Active</span>' :
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Inactive</span>'
                            }
                            ${provider.priority && provider.priority !== 'undefined' ? `<span class="text-xs text-gray-500 dark:text-gray-400">Priority: ${provider.priority}</span>` : '<span></span>'}
                            <span class="text-xs text-gray-500 dark:text-gray-400">${(provider.model_list || []).length} models</span>
                        </div>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="viewProvider(${provider.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${currentUser.is_admin ? `
                        <button onclick="editProvider(${provider.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="toggleProviderStatus(${provider.id}, ${!provider.is_active})" class="p-2 text-${provider.is_active ? 'yellow' : 'green'}-600 hover:text-${provider.is_active ? 'yellow' : 'green'}-900 dark:text-${provider.is_active ? 'yellow' : 'green'}-400 rounded-lg hover:bg-${provider.is_active ? 'yellow' : 'green'}-50 dark:hover:bg-${provider.is_active ? 'yellow' : 'green'}-900/20 transition-colors">
                            <i class="fas fa-${provider.is_active ? 'pause' : 'play'}"></i>
                        </button>
                        <button onclick="deleteProvider(${provider.id})" class="p-2 text-red-600 hover:text-red-900 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// Render API keys
function renderApiKeys(apiKeys) {
    const container = document.getElementById('api-keys-list');
    
    if (apiKeys.length === 0) {
        container.innerHTML = `
            <div class="p-8 text-center text-gray-500">
                <i class="fas fa-key text-4xl mb-4"></i>
                <p class="text-lg font-medium">No API keys configured</p>
                <p class="text-sm">Click "Add API Key" to get started.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = apiKeys.map(apiKey => `
        <div class="p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-b border-gray-200 dark:border-gray-700 last:border-b-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                        <i class="fas fa-key text-green-600 dark:text-green-300"></i>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${apiKey.key_name}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${apiKey.description || 'No description'}</p>
                        <div class="flex items-center space-x-3 mt-2">
                            ${apiKey.is_active ? 
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Active</span>' :
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Inactive</span>'
                            }
                            ${apiKey.is_admin ? 
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">Admin</span>' : ''
                            }
                            ${apiKey.expires_at ? 
                                `<span class="text-xs text-gray-500 dark:text-gray-400">Expires: ${new Date(apiKey.expires_at).toLocaleDateString()}</span>` : ''
                            }
                        </div>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="copyApiKey('${apiKey.api_key}')" class="p-2 text-blue-600 hover:text-blue-900 dark:text-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors" title="Copy API Key">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button onclick="viewApiKey(${apiKey.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors" title="View details">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${currentUser.is_admin ? `
                        <button onclick="editApiKey(${apiKey.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="toggleApiKeyStatus(${apiKey.id}, ${!apiKey.is_active})" class="p-2 text-${apiKey.is_active ? 'yellow' : 'green'}-600 hover:text-${apiKey.is_active ? 'yellow' : 'green'}-900 dark:text-${apiKey.is_active ? 'yellow' : 'green'}-400 rounded-lg hover:bg-${apiKey.is_active ? 'yellow' : 'green'}-50 dark:hover:bg-${apiKey.is_active ? 'yellow' : 'green'}-900/20 transition-colors" title="${apiKey.is_active ? 'Deactivate' : 'Activate'}">
                            <i class="fas fa-${apiKey.is_active ? 'pause' : 'play'}"></i>
                        </button>
                        <button onclick="deleteApiKey(${apiKey.id})" class="p-2 text-red-600 hover:text-red-900 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// Provider modal functions
function showProviderModal() {
    editingProvider = null;
    modelEditMode = false;
    document.getElementById('provider-form').reset();
    
    // Reset provider type tracking for base URL field
    const baseUrlField = document.getElementById('provider-base-url');
    baseUrlField.dataset.providerType = '';
    
    // Reset UI elements
    const modelsDisplay = document.getElementById('models-display');
    const modelsTextarea = document.getElementById('provider-model-list');
    const modelsTags = document.getElementById('models-tags');
    const headersContainer = document.getElementById('headers-container');
    
    modelsTextarea.classList.add('hidden');
    modelsTags.classList.remove('hidden');
    modelsTags.innerHTML = '';
    modelsTextarea.value = '[]';
    
    // Reset headers to single row
    headersContainer.innerHTML = `
        <div class="flex space-x-2">
            <input type="text" placeholder="Header name" class="header-name flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
            <input type="text" placeholder="Header value" class="header-value flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
            <button type="button" onclick="addHeaderRow()" class="px-3 py-2 text-sm font-medium text-green-600 bg-green-50 dark:bg-green-900/20 rounded-md hover:bg-green-100 dark:hover:bg-green-900/30">
                <i class="fas fa-plus"></i>
            </button>
        </div>
    `;
    
    // Load strategies for the dropdown
    loadStrategies();
    
    // Show provider select when creating new provider
    const providerSelectContainer = document.getElementById('provider-select-container');
    const modelsHelpText = document.getElementById('models-help-text');
    providerSelectContainer.classList.remove('hidden');
    modelsHelpText.textContent = 'Click "Load Models" to fetch from existing provider or "Edit" to manually add models.';
    
    document.getElementById('provider-modal').classList.remove('hidden');
}

function hideProviderModal() {
    document.getElementById('provider-modal').classList.add('hidden');
    document.getElementById('provider-form').reset();
    editingProvider = null;
}

// API Key modal functions
function showApiKeyModal() {
    editingApiKey = null;
    document.getElementById('api-key-form').reset();
    document.getElementById('api-key-modal').classList.remove('hidden');
}

function hideApiKeyModal() {
    document.getElementById('api-key-modal').classList.add('hidden');
    document.getElementById('api-key-form').reset();
    editingApiKey = null;
}

// Handle provider form submission
async function handleProviderSubmit(event) {
    event.preventDefault();
    
    // Update headers from rows before submission
    updateHeadersFromRows();
    
    // Update model list from tags if not in edit mode
    if (!modelEditMode) {
        updateModelListFromTags();
    }
    
    // Parse model list
    const modelListText = document.getElementById('provider-model-list').value;
    let modelList = [];
    if (modelListText.trim()) {
        try {
            modelList = JSON.parse(modelListText);
            if (!Array.isArray(modelList)) {
                throw new Error('Model list must be an array');
            }
        } catch (error) {
            showError('Invalid model list format. Please use the tag interface or valid JSON.');
            return;
        }
    }
    
    const formData = {
        name: document.getElementById('provider-name').value,
        provider_type: document.getElementById('provider-type').value,
        base_url: document.getElementById('provider-base-url').value,
        api_key: document.getElementById('provider-api-key').value,
        model_list: modelList,
        // Strategy ID removed - strategies now reference providers
        is_active: true,
        headers: {}
    };
    
    // Parse headers if provided
    const headersText = document.getElementById('provider-headers').value;
    if (headersText.trim()) {
        try {
            formData.headers = JSON.parse(headersText);
        } catch (error) {
            showError('Invalid headers format. Please use the input fields or valid JSON.');
            return;
        }
    }
    
    try {
        const url = editingProvider ? `${API_BASE}/portal/providers/${editingProvider}` : `${API_BASE}/portal/providers`;
        const method = editingProvider ? 'PUT' : 'POST';
        
        const response = await authenticatedFetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) throw new Error('Failed to save provider');
        
        hideProviderModal();
        await loadProviders();
        showSuccess('Provider saved successfully');
    } catch (error) {
        console.error('Error saving provider:', error);
        showError('Failed to save provider');
    }
}

// Handle API key form submission
async function handleApiKeySubmit(event) {
    event.preventDefault();
    
    const formData = {
        key_name: document.getElementById('api-key-name').value,
        description: document.getElementById('api-key-description').value,
        is_active: true
    };
    
    // Add expires_in_days if provided
    const expiresInDays = document.getElementById('api-key-expires-in-days').value;
    if (expiresInDays && parseInt(expiresInDays) > 0) {
        formData.expires_in_days = parseInt(expiresInDays);
    }
    
    // Add admin flag if checked (only shown to admin users)
    const isAdminCheckbox = document.getElementById('api-key-is-admin');
    if (isAdminCheckbox && isAdminCheckbox.checked) {
        formData.is_admin = true;
    }
    
    try {
        const url = editingApiKey ? `${API_BASE}/portal/api-keys/${editingApiKey}` : `${API_BASE}/portal/api-keys`;
        const method = editingApiKey ? 'PUT' : 'POST';
        
        const response = await authenticatedFetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) throw new Error('Failed to save API key');
        
        const result = await response.json();
        
        hideApiKeyModal();
        await loadApiKeys();
        
        // Show the generated API key
        if (result.api_key && !editingApiKey) {
            const message = `API key saved successfully!\n\nGenerated API Key: ${result.api_key}\n\nPlease save this key securely as it won't be shown again.`;
            alert(message);
        } else {
            showSuccess('API key saved successfully');
        }
    } catch (error) {
        console.error('Error saving API key:', error);
        showError('Failed to save API key');
    }
}

// View provider
async function viewProvider(id) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers/${id}`);
        if (!response.ok) throw new Error('Failed to load provider');
        
        const provider = await response.json();
        
        // Create a modal to view provider details
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-600 dark:bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border dark:border-gray-600 w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white dark:bg-gray-800">
                <div class="mt-3">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Provider Details</h3>
                        <div class="flex items-center space-x-2">
                            ${provider.is_active ? 
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Active</span>' :
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Inactive</span>'
                            }
                            ${provider.priority && provider.priority !== 'undefined' ? `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">Priority ${provider.priority}</span>` : ''}
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
                                <p class="text-sm text-gray-900 dark:text-white font-medium">${provider.name}</p>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Type</label>
                                <p class="text-sm text-gray-900 dark:text-white font-medium">${provider.provider_type}</p>
                            </div>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Base URL</label>
                            <p class="text-sm text-gray-900 dark:text-white break-all bg-gray-50 dark:bg-gray-700 p-2 rounded">${provider.base_url}</p>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Available Models</label>
                            <div class="flex flex-wrap gap-2">
                                ${(provider.model_list || []).map(model => 
                                    `<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                        ${model}
                                    </span>`
                                ).join('')}
                                ${(provider.model_list || []).length === 0 ? 
                                    '<span class="text-sm text-gray-500 dark:text-gray-400 italic">No models configured</span>' : ''
                                }
                            </div>
                        </div>
                        
                        ${provider.headers && Object.keys(provider.headers).length > 0 ? `
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Custom Headers</label>
                            <div class="bg-gray-50 dark:bg-gray-700 p-2 rounded">
                                ${Object.entries(provider.headers).map(([key, value]) => 
                                    `<div class="text-sm text-gray-900 dark:text-white"><span class="font-medium">${key}:</span> ${value}</div>`
                                ).join('')}
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Created</label>
                                <p class="text-sm text-gray-900 dark:text-white">${new Date(provider.created_at).toLocaleString()}</p>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Last Updated</label>
                                <p class="text-sm text-gray-900 dark:text-white">${new Date(provider.updated_at).toLocaleString()}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex justify-end mt-6">
                        <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close modal on outside click
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.remove();
            }
        });
    } catch (error) {
        console.error('Error loading provider:', error);
        showError('Failed to load provider');
    }
}

// Edit provider
async function editProvider(id) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers/${id}`);
        if (!response.ok) throw new Error('Failed to load provider');
        
        const provider = await response.json();
        editingProvider = id;
        modelEditMode = false;
        
        // Fill form
        document.getElementById('provider-name').value = provider.name;
        document.getElementById('provider-type').value = provider.provider_type;
        document.getElementById('provider-base-url').value = provider.base_url;
        document.getElementById('provider-api-key').value = provider.api_key;
        
        // Set provider type tracking for base URL field
        const baseUrlField = document.getElementById('provider-base-url');
        baseUrlField.dataset.providerType = provider.provider_type;
        // Strategy selection removed - strategies now reference providers
        
        // Set up models - automatically load from provider
        const modelsTextarea = document.getElementById('provider-model-list');
        const modelsTags = document.getElementById('models-tags');
        
        // Load models from the provider being edited
        try {
            const modelsResponse = await authenticatedFetch(`${API_BASE}/portal/providers/${id}/models`);
            if (modelsResponse.ok) {
                const data = await modelsResponse.json();
                modelsTextarea.value = JSON.stringify(data.models || [], null, 2);
                updateModelTags(data.models || []);
            } else {
                // Fallback to provider.model_list
                modelsTextarea.value = JSON.stringify(provider.model_list || [], null, 2);
                updateModelTags(provider.model_list || []);
            }
        } catch (error) {
            console.warn('Could not load models from provider, using stored models:', error);
            
            // Show debug console for model loading issues
            showDebugConsole('Provider Model Load Warning', {
                error: error.message,
                providerId: id,
                providerName: provider.name,
                timestamp: new Date().toISOString(),
                endpoint: `${API_BASE}/portal/providers/${id}/models`,
                fallback: 'Using stored models from provider.model_list'
            });
            
            modelsTextarea.value = JSON.stringify(provider.model_list || [], null, 2);
            updateModelTags(provider.model_list || []);
        }
        
        modelsTextarea.classList.add('hidden');
        modelsTags.classList.remove('hidden');
        
        // Set up headers
        const headersContainer = document.getElementById('headers-container');
        const headers = provider.headers || {};
        
        if (Object.keys(headers).length > 0) {
            headersContainer.innerHTML = Object.entries(headers).map(([key, value]) => `
                <div class="flex space-x-2">
                    <input type="text" placeholder="Header name" value="${key}" class="header-name flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
                    <input type="text" placeholder="Header value" value="${value}" class="header-value flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
                    <button type="button" onclick="removeHeaderRow(this)" class="px-3 py-2 text-sm font-medium text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30">
                        <i class="fas fa-minus"></i>
                    </button>
                </div>
            `).join('') + `
                <div class="flex space-x-2">
                    <input type="text" placeholder="Header name" class="header-name flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
                    <input type="text" placeholder="Header value" class="header-value flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
                    <button type="button" onclick="addHeaderRow()" class="px-3 py-2 text-sm font-medium text-green-600 bg-green-50 dark:bg-green-900/20 rounded-md hover:bg-green-100 dark:hover:bg-green-900/30">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
            `;
        } else {
            headersContainer.innerHTML = `
                <div class="flex space-x-2">
                    <input type="text" placeholder="Header name" class="header-name flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
                    <input type="text" placeholder="Header value" class="header-value flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
                    <button type="button" onclick="addHeaderRow()" class="px-3 py-2 text-sm font-medium text-green-600 bg-green-50 dark:bg-green-900/20 rounded-md hover:bg-green-100 dark:hover:bg-green-900/30">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
            `;
        }
        
        // Hide provider select when editing, show when creating new
        const providerSelectContainer = document.getElementById('provider-select-container');
        const modelsHelpText = document.getElementById('models-help-text');
        if (editingProvider) {
            providerSelectContainer.classList.add('hidden');
            modelsHelpText.textContent = 'Click "Load Models" to fetch from this provider or "Edit" to manually add models.';
        } else {
            providerSelectContainer.classList.remove('hidden');
            modelsHelpText.textContent = 'Click "Load Models" to fetch from existing provider or "Edit" to manually add models.';
        }
        
        document.getElementById('provider-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading provider:', error);
        showError('Failed to load provider');
    }
}

// View API key
async function viewApiKey(id) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/api-keys/${id}`);
        if (!response.ok) throw new Error('Failed to load API key');
        
        const apiKey = await response.json();
        
        // Create a modal to view API key details
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-600 dark:bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border dark:border-gray-600 w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white dark:bg-gray-800">
                <div class="mt-3">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">API Key Details</h3>
                        <div class="flex items-center space-x-2">
                            ${apiKey.is_active ? 
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Active</span>' :
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Inactive</span>'
                            }
                            ${apiKey.is_admin ? 
                                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">Admin</span>' : ''
                            }
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Key Name</label>
                                <p class="text-sm text-gray-900 dark:text-white font-medium">${apiKey.key_name}</p>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">API Key</label>
                                <div class="flex items-center space-x-2">
                                    <p class="text-sm text-gray-900 dark:text-white font-mono bg-gray-50 dark:bg-gray-700 p-2 rounded flex-1 truncate">${apiKey.api_key}</p>
                                    <button onclick="copyApiKey('${apiKey.api_key}')" class="p-2 text-blue-600 hover:text-blue-900 dark:text-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors" title="Copy API Key">
                                        <i class="fas fa-copy"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                            <p class="text-sm text-gray-900 dark:text-white">${apiKey.description || 'No description'}</p>
                        </div>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Created</label>
                                <p class="text-sm text-gray-900 dark:text-white">${new Date(apiKey.created_at).toLocaleString()}</p>
                            </div>
                            ${apiKey.expires_at ? `
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Expires</label>
                                <p class="text-sm text-gray-900 dark:text-white">${new Date(apiKey.expires_at).toLocaleString()}</p>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    
                    <div class="flex justify-end mt-6">
                        <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close modal on outside click
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.remove();
            }
        });
    } catch (error) {
        console.error('Error loading API key:', error);
        showError('Failed to load API key');
    }
}

// Edit API key
async function editApiKey(id) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/api-keys/${id}`);
        if (!response.ok) throw new Error('Failed to load API key');
        
        const apiKey = await response.json();
        editingApiKey = id;
        
        // Fill form
        document.getElementById('api-key-name').value = apiKey.key_name;
        document.getElementById('api-key-description').value = apiKey.description || '';
        
        // Note: The API key value is not returned for security reasons
        // Users can only edit metadata, not the actual key value
        
        document.getElementById('api-key-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading API key:', error);
        showError('Failed to load API key');
    }
}

// Toggle provider view mode
function toggleProviderView() {
    providerViewMode = providerViewMode === 'list' ? 'card' : 'list';
    
    const viewIcon = document.getElementById('view-icon');
    const viewText = document.getElementById('view-text');
    
    if (providerViewMode === 'card') {
        viewIcon.className = 'fas fa-list mr-2';
        viewText.textContent = 'List View';
    } else {
        viewIcon.className = 'fas fa-th-large mr-2';
        viewText.textContent = 'Card View';
    }
    
    // Reload providers to update view
    loadProviders();
}

// Toggle model input mode
function toggleModelInput() {
    modelEditMode = !modelEditMode;
    
    const modelsDisplay = document.getElementById('models-display');
    const modelsTextarea = document.getElementById('provider-model-list');
    const modelsTags = document.getElementById('models-tags');
    
    if (modelEditMode) {
        // Show textarea, hide tags
        modelsTextarea.classList.remove('hidden');
        modelsTags.classList.add('hidden');
        
        // Update textarea with current models
        const currentModels = Array.from(modelsTags.children).map(tag => 
            tag.textContent.replace('×', '').trim()
        );
        modelsTextarea.value = JSON.stringify(currentModels, null, 2);
    } else {
        // Show tags, hide textarea
        modelsTextarea.classList.add('hidden');
        modelsTags.classList.remove('hidden');
        
        // Update tags from textarea
        try {
            const models = JSON.parse(modelsTextarea.value);
            if (Array.isArray(models)) {
                updateModelTags(models);
            }
        } catch (error) {
            console.error('Invalid JSON in model list');
        }
    }
}

// Update model tags display
function updateModelTags(models) {
    const modelsTags = document.getElementById('models-tags');
    modelsTags.innerHTML = models.map(model => `
        <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            ${model}
            <button type="button" onclick="removeModelTag(this)" class="ml-2 text-blue-600 hover:text-blue-800 dark:text-blue-400">
                ×
            </button>
        </span>
    `).join('');
}

// Remove model tag
function removeModelTag(button) {
    button.parentElement.remove();
    updateModelListFromTags();
}

// Update model list from tags
function updateModelListFromTags() {
    const modelsTags = document.getElementById('models-tags');
    const models = Array.from(modelsTags.children).map(tag => 
        tag.textContent.replace('×', '').trim()
    );
    
    const modelsTextarea = document.getElementById('provider-model-list');
    modelsTextarea.value = JSON.stringify(models, null, 2);
}

// Add header row
function addHeaderRow() {
    const container = document.getElementById('headers-container');
    const newRow = document.createElement('div');
    newRow.className = 'flex space-x-2';
    newRow.innerHTML = `
        <input type="text" placeholder="Header name" class="header-name flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
        <input type="text" placeholder="Header value" class="header-value flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
        <button type="button" onclick="removeHeaderRow(this)" class="px-3 py-2 text-sm font-medium text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30">
            <i class="fas fa-minus"></i>
        </button>
    `;
    container.appendChild(newRow);
}

// Remove header row
function removeHeaderRow(button) {
    button.parentElement.remove();
    updateHeadersFromRows();
}

// Update headers from rows
function updateHeadersFromRows() {
    const headerRows = document.querySelectorAll('#headers-container > div');
    const headers = {};
    
    headerRows.forEach(row => {
        const name = row.querySelector('.header-name').value.trim();
        const value = row.querySelector('.header-value').value.trim();
        if (name && value) {
            headers[name] = value;
        }
    });
    
    const headersTextarea = document.getElementById('provider-headers');
    headersTextarea.value = JSON.stringify(headers, null, 2);
}

// Toggle provider status
async function toggleProviderStatus(id, newStatus) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_active: newStatus })
        });
        
        if (!response.ok) throw new Error('Failed to update provider');
        
        await loadProviders();
        showSuccess(`Provider ${newStatus ? 'activated' : 'deactivated'}`);
    } catch (error) {
        console.error('Error updating provider:', error);
        showError('Failed to update provider');
    }
}

// Toggle API key status
async function toggleApiKeyStatus(id, newStatus) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/api-keys/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_active: newStatus })
        });
        
        if (!response.ok) throw new Error('Failed to update API key');
        
        await loadApiKeys();
        showSuccess(`API key ${newStatus ? 'activated' : 'deactivated'}`);
    } catch (error) {
        console.error('Error updating API key:', error);
        showError('Failed to update API key');
    }
}

// Delete provider
async function deleteProvider(id) {
    if (!confirm('Are you sure you want to delete this provider?')) return;
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete provider');
        
        await loadProviders();
        showSuccess('Provider deleted successfully');
    } catch (error) {
        console.error('Error deleting provider:', error);
        showError('Failed to delete provider');
    }
}

// Delete API key
async function deleteApiKey(id) {
    if (!confirm('Are you sure you want to delete this API key?')) return;
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/api-keys/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete API key');
        
        await loadApiKeys();
        showSuccess('API key deleted successfully');
    } catch (error) {
        console.error('Error deleting API key:', error);
        showError('Failed to delete API key');
    }
}

// Save settings
async function saveSettings() {
    const settings = {
        database_type: document.getElementById('database-type').value,
        database_url: document.getElementById('database-url').value,
        supabase_url: document.getElementById('supabase-url').value,
        supabase_key: document.getElementById('supabase-key').value
    };
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) throw new Error('Failed to save settings');
        
        showSuccess('Settings saved successfully');
    } catch (error) {
        console.error('Error saving settings:', error);
        showError('Failed to save settings');
    }
}

// Utility functions
function updateStatus(message, type) {
    const indicator = document.getElementById('status-indicator');
    const colors = {
        success: 'bg-green-100 text-green-800',
        error: 'bg-red-100 text-red-800',
        warning: 'bg-yellow-100 text-yellow-800'
    };
    
    indicator.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[type] || colors.success}`;
    indicator.innerHTML = `<i class="fas fa-circle text-${type === 'success' ? 'green' : type === 'error' ? 'red' : 'yellow'}-400 mr-1"></i>${message}`;
}

function showSuccess(message) {
    // Simple alert for now, could be replaced with toast notifications
    alert(message);
}

function showError(message) {
    // Simple alert for now, could be replaced with toast notifications
    alert('Error: ' + message);
}

// Handle provider type change to auto-populate default URLs
function handleProviderTypeChange() {
    const providerType = document.getElementById('provider-type').value;
    const baseUrlField = document.getElementById('provider-base-url');
    
    // Default URLs for each provider type
    const defaultUrls = {
        'openai': 'https://api.openai.com/v1',
        'azure': 'https://your-resource.openai.azure.com/openai/deployments/your-deployment',
        'anthropic': 'https://api.anthropic.com',
        'gemini': 'https://generativelanguage.googleapis.com/v1beta',
        'mistral': 'https://api.mistral.ai/v1',
        'perplexity': 'https://api.perplexity.ai',
        'ollama': 'http://localhost:11434',
        'groq': 'https://api.groq.com/openai/v1',
        'openrouter': 'https://openrouter.ai/api/v1',
        'custom': ''
    };
    
    // Only update if field is empty or user is creating new provider
    if (providerType && (!baseUrlField.value || baseUrlField.value === defaultUrls[baseUrlField.dataset.providerType || ''])) {
        baseUrlField.value = defaultUrls[providerType] || '';
        // Store the provider type for future reference
        baseUrlField.dataset.providerType = providerType;
    }
}

// Load provider select dropdown
async function loadProviderSelect() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers`);
        if (!response.ok) throw new Error('Failed to load providers');
        
        const providers = await response.json();
        const select = document.getElementById('provider-select');
        
        // Clear existing options except the first one
        select.innerHTML = '<option value="">Select provider</option>';
        
        // Add provider options
        providers.forEach(provider => {
            const option = document.createElement('option');
            option.value = provider.id;
            option.textContent = provider.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading provider select:', error);
    }
}

// Load models from selected provider
async function loadProviderModels() {
    let providerId;
    let providerName;
    
    // If we're editing a provider, use that provider automatically
    if (editingProvider) {
        providerId = editingProvider;
        providerName = document.getElementById('provider-name').value;
    } else {
        // Otherwise use the selected provider from dropdown
        providerId = document.getElementById('provider-select').value;
        if (!providerId) {
            showError('Please select a provider first');
            return;
        }
    }
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/providers/${providerId}/models`);
        if (!response.ok) throw new Error('Failed to load provider models');
        
        const data = await response.json();
        const modelListTextarea = document.getElementById('provider-model-list');
        
        // Format models as JSON array
        modelListTextarea.value = JSON.stringify(data.models, null, 2);
        
        // Update tags display
        updateModelTags(data.models);
        
        // Exit edit mode
        modelEditMode = false;
        const modelsDisplay = document.getElementById('models-display');
        const modelsTextarea = document.getElementById('provider-model-list');
        const modelsTags = document.getElementById('models-tags');
        
        modelsTextarea.classList.add('hidden');
        modelsTags.classList.remove('hidden');
        
        showSuccess(`Loaded ${data.models.length} models from ${providerName || data.provider_name}`);
    } catch (error) {
        console.error('Error loading provider models:', error);
        
        // Show debug console with error details
        showDebugConsole('Provider Model Fetch Error', {
            error: error.message,
            providerId: providerId,
            providerName: providerName || 'Unknown',
            timestamp: new Date().toISOString(),
            endpoint: `${API_BASE}/portal/providers/${providerId}/models`
        });
        
        showError('Failed to load provider models - See debug console for details');
    }
}

// Copy API key to clipboard
function copyApiKey(apiKey) {
    navigator.clipboard.writeText(apiKey).then(function() {
        showSuccess('API key copied to clipboard!');
    }).catch(function(err) {
        console.error('Failed to copy API key: ', err);
        showError('Failed to copy API key');
    });
}

// Debug console for showing detailed error information
function showDebugConsole(title, debugData) {
    // Create debug console element if it doesn't exist
    let debugConsole = document.getElementById('debug-console');
    if (!debugConsole) {
        debugConsole = document.createElement('div');
        debugConsole.id = 'debug-console';
        debugConsole.className = 'fixed bottom-4 right-4 w-96 max-h-96 bg-gray-900 text-white p-4 rounded-lg shadow-lg z-50 overflow-hidden';
        document.body.appendChild(debugConsole);
    }
    
    // Format debug data
    const debugContent = `
        <div class="flex justify-between items-start mb-2">
            <h4 class="text-red-400 font-semibold">${title}</h4>
            <button onclick="document.getElementById('debug-console').remove()" class="text-gray-400 hover:text-white">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="text-xs font-mono bg-gray-800 p-2 rounded overflow-auto max-h-64">
            <div class="text-gray-300">Timestamp: ${debugData.timestamp}</div>
            <div class="text-red-400">Error: ${debugData.error}</div>
            <div class="text-blue-400">Provider ID: ${debugData.providerId}</div>
            <div class="text-green-400">Endpoint: ${debugData.endpoint}</div>
        </div>
        <div class="mt-2 flex space-x-2">
            <button onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(debugData)}, null, 2))" class="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded">
                Copy Debug Info
            </button>
            <button onclick="document.getElementById('debug-console').remove()" class="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded">
                Close
            </button>
        </div>
    `;
    
    debugConsole.innerHTML = debugContent;
}

// Strategy management functions
function showStrategyModal(strategyType = null) {
    editingStrategy = null;
    document.getElementById('strategy-form').reset();
    
    // Set strategy type if provided
    if (strategyType) {
        document.getElementById('strategy-type').value = strategyType;
        // Trigger the type change handler to show/hide appropriate fields
        handleStrategyTypeChange();
    }
    
    document.getElementById('strategy-modal').classList.remove('hidden');
}

function hideStrategyModal() {
    document.getElementById('strategy-modal').classList.add('hidden');
    document.getElementById('strategy-form').reset();
    delete document.getElementById('strategy-form').dataset.editingId;
    document.querySelector('#strategy-modal h3').textContent = 'Add Strategy';
    
    // Clear all stored strategy data
    clearStrategyModalData();
}

// Provider priority functionality removed - fallback is now based on order list

// Handle strategy form submission
async function handleStrategySubmit(event) {
    event.preventDefault();
    
    const strategyType = document.getElementById('strategy-type').value;
    // Provider priority is now based on fallback order, not separate configuration
    const selectedProviders = [];
    
    const formData = {
        name: document.getElementById('strategy-name').value,
        description: document.getElementById('strategy-description').value,
        strategy_type: strategyType,
        fallback_enabled: document.getElementById('strategy-fallback').value === 'true',
        provider_priority: selectedProviders,
        is_active: true
    };
    
    // Handle different model configurations based on strategy type
    if (strategyType === 'anthropic') {
        formData.high_tier_models = getTierModels('high');
        formData.medium_tier_models = getTierModels('medium');
        formData.low_tier_models = getTierModels('low');
    } else if (strategyType === 'openai') {
        // For OpenAI, use simple model list
        formData.models = getOpenAIModels();
        formData.high_tier_models = [];
        formData.medium_tier_models = [];
        formData.low_tier_models = [];
    } else {
        formData.high_tier_models = [];
        formData.medium_tier_models = [];
        formData.low_tier_models = [];
        formData.models = [];
    }
    
    const form = document.getElementById('strategy-form');
    const editingId = form.dataset.editingId;
    
    try {
        let response;
        if (editingId) {
            // Update existing strategy
            response = await authenticatedFetch(`${API_BASE}/portal/strategies/${editingId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
        } else {
            // Create new strategy
            response = await authenticatedFetch(`${API_BASE}/portal/strategies`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
        }
        
        if (!response.ok) throw new Error('Failed to save strategy');
        
        hideStrategyModal();
        await loadStrategies();
        showSuccess('Strategy saved successfully');
        
        // Clear any stored strategy data
        clearStrategyModalData();
    } catch (error) {
        console.error('Error saving strategy:', error);
        showError('Failed to save strategy');
    }
}

// Handle strategy type change
function handleStrategyTypeChange() {
    const strategyType = document.getElementById('strategy-type').value;
    const anthropicContainer = document.getElementById('anthropic-models-container');
    const openaiContainer = document.getElementById('openai-models-container');
    
    if (strategyType === 'anthropic') {
        // Show tier-based model inputs for Anthropic
        anthropicContainer.classList.remove('hidden');
        openaiContainer.classList.add('hidden');
        loadStrategyModels('anthropic');
    } else if (strategyType === 'openai') {
        // Show simple model list for OpenAI
        anthropicContainer.classList.add('hidden');
        openaiContainer.classList.remove('hidden');
        loadStrategyModels('openai');
    } else {
        // Hide both if no type selected
        anthropicContainer.classList.add('hidden');
        openaiContainer.classList.add('hidden');
    }
}

// Load strategy models from API
async function loadStrategyModels(strategyType) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/strategy-models?strategy_type=${strategyType}`);
        if (!response.ok) return;
        
        const data = await response.json();
        // Store models globally for tier dropdown management
        window.currentStrategyModels = data.models;
        updateStrategyModelDropdowns(data.models, strategyType);
    } catch (error) {
        console.error('Error loading strategy models:', error);
    }
}

// Update strategy model dropdowns with available models
function updateStrategyModelDropdowns(models, strategyType) {
    if (strategyType === 'anthropic') {
        // Update Anthropic tier dropdowns
        updateModelDropdown('strategy-high-models-select', models);
        updateModelDropdown('strategy-medium-models-select', models);
        updateModelDropdown('strategy-low-models-select', models);
        
        // Update tier dropdowns to remove duplicates
        updateTierDropdowns();
    } else if (strategyType === 'openai') {
        // Update OpenAI model dropdown
        updateModelDropdown('strategy-openai-models-select', models);
        
        // Update OpenAI dropdown to remove selected models
        updateOpenAIModelDropdown();
    }
}

// Update a single model dropdown
function updateModelDropdown(dropdownId, models) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    
    // Keep current selection
    const currentValue = dropdown.value;
    
    // Clear existing options
    dropdown.innerHTML = '';
    
    // Add models as options
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.model_name;
        option.textContent = model.display_name;
        dropdown.appendChild(option);
    });
    
    // Restore selection if it still exists
    if (currentValue) {
        dropdown.value = currentValue;
    }
}

// Add selected model to Anthropic tier list
function addModelToTier(tier, dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const modelName = dropdown.value;
    const modelText = dropdown.options[dropdown.selectedIndex].text;
    
    if (!modelName) return;
    
    // Check if model already exists in ANY tier
    if (isModelInAnyTier(modelName)) {
        return; // Model already exists in another tier
    }
    
    // Get the list container for this tier
    const listContainer = document.getElementById(`strategy-${tier}-models-list`);
    
    // Create model tag
    const modelTag = document.createElement('div');
    modelTag.className = 'model-tag flex items-center justify-between bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200 px-3 py-1 rounded-md text-sm';
    modelTag.dataset.modelName = modelName;
    modelTag.innerHTML = `
        <span>${modelText}</span>
        <button type="button" onclick="removeModelFromTier('${tier}', '${modelName}')" class="ml-2 text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-200">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    listContainer.appendChild(modelTag);
    
    // Reset dropdown
    dropdown.value = '';
    
    // Update dropdowns to remove the selected model from all tier dropdowns
    updateTierDropdowns();
}

// Remove model from Anthropic tier list
function removeModelFromTier(tier, modelName) {
    const listContainer = document.getElementById(`strategy-${tier}-models-list`);
    const modelTag = listContainer.querySelector(`[data-model-name="${modelName}"]`);
    if (modelTag) {
        modelTag.remove();
    }
    
    // Update dropdowns to add the model back to all tier dropdowns
    updateTierDropdowns();
}

// Set OpenAI model selection
function setOpenAIModel(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const modelName = dropdown.value;
    const modelText = dropdown.options[dropdown.selectedIndex].text;
    
    if (!modelName) return;
    
    const listContainer = document.getElementById('strategy-openai-models-list');
    
    // Check if model already exists
    const existingModel = listContainer.querySelector(`[data-model-name="${modelName}"]`);
    if (existingModel) {
        return; // Model already exists
    }
    
    // Create model tag
    const modelTag = document.createElement('div');
    modelTag.className = 'model-tag flex items-center justify-between bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 px-3 py-1 rounded-md text-sm';
    modelTag.dataset.modelName = modelName;
    modelTag.innerHTML = `
        <span>${modelText}</span>
        <button type="button" onclick="removeOpenAIModel('${modelName}')" class="ml-2 text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    listContainer.appendChild(modelTag);
    
    // Reset dropdown
    dropdown.value = '';
    
    // Update dropdown to remove selected model
    updateOpenAIModelDropdown();
}

// Remove OpenAI model selection
function removeOpenAIModel(modelName) {
    const listContainer = document.getElementById('strategy-openai-models-list');
    const modelTag = listContainer.querySelector(`[data-model-name="${modelName}"]`);
    if (modelTag) {
        modelTag.remove();
    }
    
    // Update dropdown to add the model back
    updateOpenAIModelDropdown();
}

// Get selected models from tier lists
function getTierModels(tier) {
    const listContainer = document.getElementById(`strategy-${tier}-models-list`);
    const modelTags = listContainer.querySelectorAll('.model-tag');
    return Array.from(modelTags).map(tag => tag.dataset.modelName);
}

// Get selected OpenAI models
function getOpenAIModels() {
    const listContainer = document.getElementById('strategy-openai-models-list');
    const modelTags = listContainer.querySelectorAll('.model-tag');
    return Array.from(modelTags).map(tag => tag.dataset.modelName);
}

// Get selected OpenAI model (legacy function for compatibility)
function getOpenAIModel() {
    const models = getOpenAIModels();
    return models.length > 0 ? models[0] : null;
}

// Clear all strategy modal data
function clearStrategyModalData() {
    // Clear model lists
    document.getElementById('strategy-high-models-list').innerHTML = '';
    document.getElementById('strategy-medium-models-list').innerHTML = '';
    document.getElementById('strategy-low-models-list').innerHTML = '';
    document.getElementById('strategy-openai-models-list').innerHTML = '';
    
    // Provider priority functionality removed - fallback is now based on order list
    
    // Fallback order is now based on provider order list, not separate configuration
    
    // Clear model dropdowns
    document.getElementById('strategy-high-models-select').value = '';
    document.getElementById('strategy-medium-models-select').value = '';
    document.getElementById('strategy-low-models-select').value = '';
    document.getElementById('strategy-openai-models-select').value = '';
    
    // Clear stored models
    window.currentStrategyModels = [];
    
    // Reset dropdowns to show all available models
    updateTierDropdowns();
}

// Check if model exists in any tier
function isModelInAnyTier(modelName) {
    const tiers = ['high', 'medium', 'low'];
    for (let tier of tiers) {
        const listContainer = document.getElementById(`strategy-${tier}-models-list`);
        const existingModel = listContainer.querySelector(`[data-model-name="${modelName}"]`);
        if (existingModel) {
            return true;
        }
    }
    return false;
}

// Update tier dropdowns to remove models that are already selected
function updateTierDropdowns() {
    if (!window.currentStrategyModels) return;
    
    const tiers = ['high', 'medium', 'low'];
    const selectedModels = new Set();
    
    // Collect all selected models across all tiers
    tiers.forEach(tier => {
        const listContainer = document.getElementById(`strategy-${tier}-models-list`);
        const modelTags = listContainer.querySelectorAll('.model-tag');
        modelTags.forEach(tag => {
            selectedModels.add(tag.dataset.modelName);
        });
    });
    
    // Update each dropdown to only show unselected models
    tiers.forEach(tier => {
        const dropdown = document.getElementById(`strategy-${tier}-models-select`);
        if (!dropdown) return;
        
        const currentValue = dropdown.value;
        
        // Clear dropdown
        dropdown.innerHTML = '<option value="">Select model for ' + tier + ' tier</option>';
        
        // Add only unselected models
        window.currentStrategyModels.forEach(model => {
            if (!selectedModels.has(model.model_name)) {
                const option = document.createElement('option');
                option.value = model.model_name;
                option.textContent = model.display_name;
                dropdown.appendChild(option);
            }
        });
        
        // Restore selection if it still exists
        if (currentValue && !selectedModels.has(currentValue)) {
            dropdown.value = currentValue;
        }
    });
}

// Update OpenAI model dropdown to remove selected models
function updateOpenAIModelDropdown() {
    if (!window.currentStrategyModels) return;
    
    const dropdown = document.getElementById('strategy-openai-models-select');
    if (!dropdown) return;
    
    const currentValue = dropdown.value;
    const selectedModels = new Set();
    
    // Collect selected models
    const listContainer = document.getElementById('strategy-openai-models-list');
    const modelTags = listContainer.querySelectorAll('.model-tag');
    modelTags.forEach(tag => {
        selectedModels.add(tag.dataset.modelName);
    });
    
    // Clear dropdown
    dropdown.innerHTML = '<option value="">Select model for OpenAI strategy</option>';
    
    // Add only unselected models
    window.currentStrategyModels.forEach(model => {
        if (!selectedModels.has(model.model_name)) {
            const option = document.createElement('option');
            option.value = model.model_name;
            option.textContent = model.display_name;
            dropdown.appendChild(option);
        }
    });
    
    // Restore selection if it still exists
    if (currentValue && !selectedModels.has(currentValue)) {
        dropdown.value = currentValue;
    }
}

// Add model to tier list (for editing)
function addModelToTierList(tier, modelName) {
    // Find the model in the dropdown options to get the display name
    const dropdown = document.getElementById(`strategy-${tier}-models-select`);
    const option = Array.from(dropdown.options).find(opt => opt.value === modelName);
    const displayText = option ? option.textContent : modelName;
    
    const listContainer = document.getElementById(`strategy-${tier}-models-list`);
    
    // Check if model already exists
    const existingModel = listContainer.querySelector(`[data-model-name="${modelName}"]`);
    if (existingModel) return;
    
    // Create model tag
    const modelTag = document.createElement('div');
    modelTag.className = 'model-tag flex items-center justify-between bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200 px-3 py-1 rounded-md text-sm';
    modelTag.dataset.modelName = modelName;
    modelTag.innerHTML = `
        <span>${displayText}</span>
        <button type="button" onclick="removeModelFromTier('${tier}', '${modelName}')" class="ml-2 text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-200">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    listContainer.appendChild(modelTag);
}

// Add OpenAI model to list (for editing)
function addOpenAIModelToList(modelName) {
    // Find the model in the dropdown options to get the display name
    const dropdown = document.getElementById('strategy-openai-models-select');
    const option = Array.from(dropdown.options).find(opt => opt.value === modelName);
    const displayText = option ? option.textContent : modelName;
    
    const listContainer = document.getElementById('strategy-openai-models-list');
    
    // Check if model already exists
    const existingModel = listContainer.querySelector(`[data-model-name="${modelName}"]`);
    if (existingModel) return;
    
    // Create model tag
    const modelTag = document.createElement('div');
    modelTag.className = 'model-tag flex items-center justify-between bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 px-3 py-1 rounded-md text-sm';
    modelTag.dataset.modelName = modelName;
    modelTag.innerHTML = `
        <span>${displayText}</span>
        <button type="button" onclick="removeOpenAIModel('${modelName}')" class="ml-2 text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    listContainer.appendChild(modelTag);
    
    // Update dropdown to remove selected model
    updateOpenAIModelDropdown();
}

// Legacy function for backward compatibility
function addModelToStrategy(dropdownId, textareaId) {
    // This function is deprecated but kept for compatibility
    console.warn('addModelToStrategy is deprecated. Use addModelToTier or setOpenAIModel instead.');
}

// Parse model list from comma-separated text
function parseModelList(text) {
    if (!text.trim()) return [];
    return text.split(',').map(model => model.trim()).filter(model => model.length > 0);
}

// Load strategies for display
async function loadStrategies() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/strategies-with-providers`);
        if (!response.ok) return;
        
        const strategies = await response.json();
        const strategiesList = document.getElementById('strategies-list');
        
        if (strategies.length === 0) {
            strategiesList.innerHTML = `
                <div class="p-8 text-center text-gray-500 dark:text-gray-400">
                    <i class="fas fa-chess text-4xl mb-4"></i>
                    <p>No strategies configured yet</p>
                    <p class="text-sm">Create a strategy to define model mapping and fallback rules</p>
                </div>
            `;
            return;
        }
        
        strategiesList.innerHTML = strategies.map(strategy => {
            const typeColor = strategy.strategy_type === 'anthropic' ? 'purple' : 'green';
            const typeBg = strategy.strategy_type === 'anthropic' ? 'bg-purple-100 dark:bg-purple-900/20' : 'bg-green-100 dark:bg-green-900/20';
            const typeText = strategy.strategy_type === 'anthropic' ? 'text-purple-800 dark:text-purple-200' : 'text-green-800 dark:text-green-200';
            
            return `
            <div class="p-6 border-l-4 border-${typeColor}-500">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="flex items-center space-x-2">
                            <h3 class="text-lg font-medium text-gray-900 dark:text-white">${strategy.name}</h3>
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${typeBg} ${typeText}">
                                ${strategy.strategy_type.toUpperCase()}
                            </span>
                            ${strategy.fallback_enabled ? 
                                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">Fallback</span>' : 
                                ''
                            }
                        </div>
                        ${strategy.description ? `<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${strategy.description}</p>` : ''}
                        
                        ${strategy.strategy_type === 'anthropic' ? `
                        <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300">High Tier</h4>
                                <div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                    ${strategy.high_tier_models.length > 0 ? 
                                        strategy.high_tier_models.join(', ') : 
                                        '<span class="text-gray-400">No models</span>'
                                    }
                                </div>
                            </div>
                            <div>
                                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300">Medium Tier</h4>
                                <div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                    ${strategy.medium_tier_models.length > 0 ? 
                                        strategy.medium_tier_models.join(', ') : 
                                        '<span class="text-gray-400">No models</span>'
                                    }
                                </div>
                            </div>
                            <div>
                                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300">Low Tier</h4>
                                <div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                    ${strategy.low_tier_models.length > 0 ? 
                                        strategy.low_tier_models.join(', ') : 
                                        '<span class="text-gray-400">No models</span>'
                                    }
                                </div>
                            </div>
                        </div>
                        ` : strategy.strategy_type === 'openai' ? `
                        <div class="mt-4">
                            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300">Models</h4>
                            <div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                ${(strategy.models && strategy.models.length > 0) || (strategy.high_tier_models && strategy.high_tier_models.length > 0) ? 
                                    (strategy.models || strategy.high_tier_models).join(', ') : 
                                    '<span class="text-gray-400">No models</span>'
                                }
                            </div>
                        </div>
                        ` : ''}
                        
                        
                    </div>
                    <div class="ml-4 flex space-x-2">
                        <button onclick="editStrategy(${strategy.id})" class="p-2 text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 rounded-full hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="deleteStrategy(${strategy.id})" class="p-2 text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
            `;}).join('');
        
    } catch (error) {
        console.error('Error loading strategies:', error);
    }
}

// Update provider strategy dropdown
function updateProviderStrategyDropdown(strategies) {
    const strategySelect = document.getElementById('provider-strategy');
    if (!strategySelect) return;
    
    // Keep current selection
    const currentValue = strategySelect.value;
    
    // Clear existing options except the first one
    strategySelect.innerHTML = '<option value="">No strategy</option>';
    
    // Add strategies to dropdown
    strategies.forEach(strategy => {
        const option = document.createElement('option');
        option.value = strategy.id;
        option.textContent = `${strategy.name} (${strategy.strategy_type})`;
        strategySelect.appendChild(option);
    });
    
    // Restore selection
    if (currentValue) {
        strategySelect.value = currentValue;
    }
}

// Load strategies for dropdown (legacy function)
async function loadStrategiesForDropdown() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/strategies`);
        if (!response.ok) return;
        
        const strategies = await response.json();
        updateProviderStrategyDropdown(strategies);
    } catch (error) {
        console.error('Error loading strategies:', error);
    }
}

// Edit strategy
async function editStrategy(id) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/strategies-with-providers`);
        if (!response.ok) throw new Error('Failed to load strategy');
        
        const strategies = await response.json();
        const strategy = strategies.find(s => s.id === id);
        if (!strategy) throw new Error('Strategy not found');
        
        // Populate form fields
        document.getElementById('strategy-name').value = strategy.name;
        document.getElementById('strategy-description').value = strategy.description || '';
        document.getElementById('strategy-type').value = strategy.strategy_type;
        document.getElementById('strategy-fallback').value = strategy.fallback_enabled.toString();
        
        if (strategy.strategy_type === 'anthropic') {
            // Clear existing model lists
            document.getElementById('strategy-high-models-list').innerHTML = '';
            document.getElementById('strategy-medium-models-list').innerHTML = '';
            document.getElementById('strategy-low-models-list').innerHTML = '';
            
            // Load models and populate tier lists
            await loadStrategyModels('anthropic');
            
            // Add models to tier lists after a delay to ensure dropdowns are populated
            setTimeout(() => {
                strategy.high_tier_models.forEach(modelName => {
                    addModelToTierList('high', modelName);
                });
                strategy.medium_tier_models.forEach(modelName => {
                    addModelToTierList('medium', modelName);
                });
                strategy.low_tier_models.forEach(modelName => {
                    addModelToTierList('low', modelName);
                });
            }, 100);
        } else if (strategy.strategy_type === 'openai') {
            // Clear existing model list
            document.getElementById('strategy-openai-models-list').innerHTML = '';
            
            // Load models and populate OpenAI model selection
            await loadStrategyModels('openai');
            
            // Add models from the new models array (OpenAI strategy uses multiple models)
            setTimeout(() => {
                if (strategy.models && strategy.models.length > 0) {
                    strategy.models.forEach(modelName => {
                        addOpenAIModelToList(modelName);
                    });
                } else if (strategy.high_tier_models && strategy.high_tier_models.length > 0) {
                    // Fallback to old structure for backward compatibility
                    strategy.high_tier_models.forEach(modelName => {
                        addOpenAIModelToList(modelName);
                    });
                }
            }, 100);
        }
        
        // Fallback order is now based on provider order list, not separate configuration
        
        // Trigger the type change handler to show/hide appropriate fields
        handleStrategyTypeChange();
        
        // Provider priority is now based on fallback order, not separate configuration
        
        // Store strategy ID for update
        document.getElementById('strategy-form').dataset.editingId = id;
        
        // Update modal title
        document.querySelector('#strategy-modal h3').textContent = 'Edit Strategy';
        
        document.getElementById('strategy-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading strategy:', error);
        showError('Failed to load strategy');
    }
}

// Delete strategy (placeholder for future implementation)
async function deleteStrategy(id) {
    if (!confirm('Are you sure you want to delete this strategy?')) return;
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/portal/strategies/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete strategy');
        
        await loadStrategies();
        showSuccess('Strategy deleted successfully');
    } catch (error) {
        console.error('Error deleting strategy:', error);
        showError('Failed to delete strategy');
    }
}

// Playground functions
function clearPlayground() {
    document.getElementById('playground-api-type').value = 'openai';
    document.getElementById('playground-model').value = '';
    document.getElementById('playground-message').value = 'Hello, please respond with a simple greeting.';
    document.getElementById('playground-temperature').value = '0.7';
    document.getElementById('playground-max-tokens').value = '1000';
    document.getElementById('playground-stream').checked = false;
    
    document.getElementById('playground-status').textContent = 'Ready to test';
    document.getElementById('playground-status').className = 'mt-1 p-3 rounded-md bg-gray-50 dark:bg-gray-700 text-sm text-gray-500 dark:text-gray-400';
    document.getElementById('playground-response-time').textContent = '-';
    document.getElementById('playground-response').textContent = 'No response yet';
}

async function runPlaygroundTest() {
    const apiType = document.getElementById('playground-api-type').value;
    const model = document.getElementById('playground-model').value;
    const message = document.getElementById('playground-message').value;
    const temperature = parseFloat(document.getElementById('playground-temperature').value);
    const maxTokens = parseInt(document.getElementById('playground-max-tokens').value);
    const stream = document.getElementById('playground-stream').checked;
    
    if (!model) {
        showError('Please enter a model name');
        return;
    }
    
    if (!message.trim()) {
        showError('Please enter a message');
        return;
    }
    
    const statusDiv = document.getElementById('playground-status');
    const responseTimeDiv = document.getElementById('playground-response-time');
    const responseDiv = document.getElementById('playground-response');
    
    statusDiv.textContent = 'Sending request...';
    statusDiv.className = 'mt-1 p-3 rounded-md bg-yellow-50 dark:bg-yellow-900/20 text-sm text-yellow-800 dark:text-yellow-200';
    responseTimeDiv.textContent = '-';
    responseDiv.textContent = 'Processing...';
    
    try {
        const startTime = Date.now();
        
        let endpoint, requestBody;
        
        if (apiType === 'openai') {
            endpoint = `${API_BASE}/v1/chat/completions`;
            requestBody = {
                model: model,
                messages: [{
                    role: 'user',
                    content: message
                }],
                temperature: temperature,
                max_tokens: maxTokens,
                stream: stream
            };
        } else if (apiType === 'anthropic') {
            endpoint = `${API_BASE}/api/anthropic/v1/messages`;
            requestBody = {
                model: model,
                max_tokens: maxTokens,
                temperature: temperature,
                messages: [{
                    role: 'user',
                    content: message
                }]
            };
        }
        
        const response = await authenticatedFetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        
        responseTimeDiv.textContent = `${responseTime}ms`;
        
        if (response.ok) {
            const data = await response.json();
            statusDiv.textContent = 'Success';
            statusDiv.className = 'mt-1 p-3 rounded-md bg-green-50 dark:bg-green-900/20 text-sm text-green-800 dark:text-green-200';
            responseDiv.textContent = JSON.stringify(data, null, 2);
        } else {
            const errorData = await response.text();
            statusDiv.textContent = `Error (${response.status})`;
            statusDiv.className = 'mt-1 p-3 rounded-md bg-red-50 dark:bg-red-900/20 text-sm text-red-800 dark:text-red-200';
            responseDiv.textContent = errorData;
        }
    } catch (error) {
        statusDiv.textContent = 'Request failed';
        statusDiv.className = 'mt-1 p-3 rounded-md bg-red-50 dark:bg-red-900/20 text-sm text-red-800 dark:text-red-200';
        responseDiv.textContent = error.message;
    }
}

// Auto-refresh data every 30 seconds
setInterval(loadData, 30000);