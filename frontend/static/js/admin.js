// Global variables
let currentSection = 'providers';
let editingProvider = null;
let editingApiKey = null;

// API Base URL
const API_BASE = '';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
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
            loadProviders(),
            loadApiKeys(),
            loadSettings()
        ]);
        updateStatus('Connected', 'success');
    } catch (error) {
        console.error('Error loading data:', error);
        updateStatus('Connection Error', 'error');
    }
}

// Load providers
async function loadProviders() {
    try {
        const response = await fetch(`${API_BASE}/admin/providers`);
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
        const response = await fetch(`${API_BASE}/admin/api-keys`);
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
        const response = await fetch(`${API_BASE}/admin/settings`);
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
            <li class="px-4 py-4 text-sm text-gray-500">
                No providers configured. Click "Add Provider" to get started.
            </li>
        `;
        return;
    }
    
    container.innerHTML = providers.map(provider => `
        <li class="px-4 py-4 hover:bg-gray-50">
            <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                            <div class="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-server text-indigo-600"></i>
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium text-gray-900 truncate">
                                ${provider.name}
                            </p>
                            <p class="text-sm text-gray-500 truncate">
                                ${provider.provider_type} • ${provider.base_url}
                            </p>
                            <div class="flex items-center space-x-4 mt-1">
                                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${provider.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                    ${provider.is_active ? 'Active' : 'Inactive'}
                                </span>
                                <span class="text-xs text-gray-500">
                                    Priority: ${provider.priority}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="editProvider(${provider.id})" class="text-indigo-600 hover:text-indigo-900">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button onclick="toggleProviderStatus(${provider.id}, ${!provider.is_active})" class="text-${provider.is_active ? 'yellow' : 'green'}-600 hover:text-${provider.is_active ? 'yellow' : 'green'}-900">
                        <i class="fas fa-${provider.is_active ? 'pause' : 'play'}"></i>
                    </button>
                    <button onclick="deleteProvider(${provider.id})" class="text-red-600 hover:text-red-900">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </li>
    `).join('');
}

// Render API keys
function renderApiKeys(apiKeys) {
    const container = document.getElementById('api-keys-list');
    
    if (apiKeys.length === 0) {
        container.innerHTML = `
            <li class="px-4 py-4 text-sm text-gray-500">
                No API keys configured. Click "Add API Key" to get started.
            </li>
        `;
        return;
    }
    
    container.innerHTML = apiKeys.map(apiKey => `
        <li class="px-4 py-4 hover:bg-gray-50">
            <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                            <div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-key text-green-600"></i>
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium text-gray-900 truncate">
                                ${apiKey.key_name}
                            </p>
                            <p class="text-sm text-gray-500 truncate">
                                ${apiKey.description || 'No description'}
                            </p>
                            <div class="flex items-center space-x-4 mt-1">
                                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${apiKey.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                    ${apiKey.is_active ? 'Active' : 'Inactive'}
                                </span>
                                ${apiKey.expires_at ? `
                                    <span class="text-xs text-gray-500">
                                        Expires: ${new Date(apiKey.expires_at).toLocaleDateString()}
                                    </span>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="editApiKey(${apiKey.id})" class="text-indigo-600 hover:text-indigo-900">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button onclick="toggleApiKeyStatus(${apiKey.id}, ${!apiKey.is_active})" class="text-${apiKey.is_active ? 'yellow' : 'green'}-600 hover:text-${apiKey.is_active ? 'yellow' : 'green'}-900">
                        <i class="fas fa-${apiKey.is_active ? 'pause' : 'play'}"></i>
                    </button>
                    <button onclick="deleteApiKey(${apiKey.id})" class="text-red-600 hover:text-red-900">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </li>
    `).join('');
}

// Provider modal functions
function showProviderModal() {
    editingProvider = null;
    document.getElementById('provider-form').reset();
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
    
    const formData = {
        name: document.getElementById('provider-name').value,
        provider_type: document.getElementById('provider-type').value,
        base_url: document.getElementById('provider-base-url').value,
        api_key: document.getElementById('provider-api-key').value,
        big_model: document.getElementById('provider-big-model').value,
        medium_model: document.getElementById('provider-medium-model').value,
        small_model: document.getElementById('provider-small-model').value,
        priority: parseInt(document.getElementById('provider-priority').value),
        is_active: true,
        headers: {}
    };
    
    // Parse headers if provided
    const headersText = document.getElementById('provider-headers').value;
    if (headersText.trim()) {
        try {
            formData.headers = JSON.parse(headersText);
        } catch (error) {
            showError('Invalid JSON in headers field');
            return;
        }
    }
    
    try {
        const url = editingProvider ? `${API_BASE}/admin/providers/${editingProvider}` : `${API_BASE}/admin/providers`;
        const method = editingProvider ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
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
        api_key: document.getElementById('api-key-value').value,
        description: document.getElementById('api-key-description').value,
        is_active: true
    };
    
    // Add expires_at if provided
    const expiresAt = document.getElementById('api-key-expires').value;
    if (expiresAt) {
        formData.expires_at = new Date(expiresAt).toISOString();
    }
    
    try {
        const url = editingApiKey ? `${API_BASE}/admin/api-keys/${editingApiKey}` : `${API_BASE}/admin/api-keys`;
        const method = editingApiKey ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) throw new Error('Failed to save API key');
        
        hideApiKeyModal();
        await loadApiKeys();
        showSuccess('API key saved successfully');
    } catch (error) {
        console.error('Error saving API key:', error);
        showError('Failed to save API key');
    }
}

// Edit provider
async function editProvider(id) {
    try {
        const response = await fetch(`${API_BASE}/admin/providers/${id}`);
        if (!response.ok) throw new Error('Failed to load provider');
        
        const provider = await response.json();
        editingProvider = id;
        
        // Fill form
        document.getElementById('provider-name').value = provider.name;
        document.getElementById('provider-type').value = provider.provider_type;
        document.getElementById('provider-base-url').value = provider.base_url;
        document.getElementById('provider-api-key').value = provider.api_key;
        document.getElementById('provider-big-model').value = provider.big_model;
        document.getElementById('provider-medium-model').value = provider.medium_model;
        document.getElementById('provider-small-model').value = provider.small_model;
        document.getElementById('provider-priority').value = provider.priority;
        document.getElementById('provider-headers').value = JSON.stringify(provider.headers || {}, null, 2);
        
        document.getElementById('provider-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading provider:', error);
        showError('Failed to load provider');
    }
}

// Edit API key
async function editApiKey(id) {
    try {
        const response = await fetch(`${API_BASE}/admin/api-keys/${id}`);
        if (!response.ok) throw new Error('Failed to load API key');
        
        const apiKey = await response.json();
        editingApiKey = id;
        
        // Fill form
        document.getElementById('api-key-name').value = apiKey.key_name;
        document.getElementById('api-key-value').value = apiKey.api_key;
        document.getElementById('api-key-description').value = apiKey.description || '';
        
        if (apiKey.expires_at) {
            const date = new Date(apiKey.expires_at);
            document.getElementById('api-key-expires').value = date.toISOString().slice(0, 16);
        }
        
        document.getElementById('api-key-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading API key:', error);
        showError('Failed to load API key');
    }
}

// Toggle provider status
async function toggleProviderStatus(id, newStatus) {
    try {
        const response = await fetch(`${API_BASE}/admin/providers/${id}`, {
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
        const response = await fetch(`${API_BASE}/admin/api-keys/${id}`, {
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
        const response = await fetch(`${API_BASE}/admin/providers/${id}`, {
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
        const response = await fetch(`${API_BASE}/admin/api-keys/${id}`, {
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
        const response = await fetch(`${API_BASE}/admin/settings`, {
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

// Auto-refresh data every 30 seconds
setInterval(loadData, 30000);