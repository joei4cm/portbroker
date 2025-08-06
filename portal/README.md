# PortBroker Portal UI

A modern Vue.js-based portal interface for managing PortBroker AI provider gateway.

## Features

- **Dashboard**: System overview with statistics and activity monitoring
- **Playground**: Interactive API testing for both OpenAI and Anthropic formats
- **Providers**: Manage AI provider configurations and settings
- **Strategies**: Complex strategy management with model selection and failover
- **Settings**: System configuration and security settings

## Key Features

### Strategy Management
- Support for both OpenAI and Anthropic strategy types
- Dynamic model selection with searchable dropdowns
- Model categorization (big, medium, small) for Anthropic strategies
- Sortable model lists with duplicate prevention
- Enable/disable controls with type-based restrictions

### API Playground
- Support for both OpenAI-compatible and Anthropic-compatible endpoints
- Real-time API testing with formatted response display
- Model selection and parameter configuration
- Request/response monitoring and statistics

### Provider Management
- CRUD operations for AI providers
- Priority-based failover configuration
- Model mapping and testing capabilities
- Status monitoring and management

## Technology Stack

- **Vue 3** with Composition API
- **Ant Design Vue** for UI components
- **Vue Router** for navigation
- **Axios** for API communication
- **Vite** for build tooling

## Setup Instructions

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

1. Navigate to the portal directory:
```bash
cd portal
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. The portal will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## API Integration

The portal integrates with the PortBroker backend through the following endpoints:

### Authentication
- `POST /api/portal/login` - User authentication

### Providers
- `GET /api/portal/providers` - List all providers
- `POST /api/portal/providers` - Create new provider
- `PUT /api/portal/providers/{id}` - Update provider
- `DELETE /api/portal/providers/{id}` - Delete provider

### Strategies
- `GET /api/portal/strategies` - List all strategies
- `POST /api/portal/strategies` - Create new strategy
- `PUT /api/portal/strategies/{id}` - Update strategy
- `DELETE /api/portal/strategies/{id}` - Delete strategy

### Settings
- `GET /api/portal/settings` - Get system settings
- `PUT /api/portal/settings` - Update system settings

### API Testing
- `POST /v1/chat/completions` - OpenAI-compatible endpoint
- `POST /api/anthropic/v1/messages` - Anthropic-compatible endpoint

## Configuration

The portal is configured through `vite.config.js`:

- Development server runs on port 3000
- API requests are proxied to `http://localhost:8000`
- Hot reload is enabled for development

## Security Features

- JWT-based authentication
- Protected routes with automatic redirection
- API token management
- CORS configuration
- Rate limiting support

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development

### Project Structure
```
portal/
├── src/
│   ├── api/           # API integration
│   ├── components/    # Reusable components
│   ├── router/        # Vue Router configuration
│   ├── utils/         # Utility functions
│   ├── views/         # Page components
│   ├── App.vue        # Root component
│   └── main.js        # Application entry
├── public/            # Static assets
├── index.html         # HTML template
├── vite.config.js     # Vite configuration
└── package.json       # Dependencies and scripts
```

### Adding New Features

1. Create new views in `src/views/`
2. Add routes in `src/router/index.js`
3. Update navigation in `src/components/Layout.vue`
4. Add API methods in `src/api/index.js`

### Styling

The portal uses Ant Design Vue's default styling with custom overrides. Additional styles can be added in component `<style>` blocks.

## Testing

The portal is designed to work with the PortBroker backend. To test the complete system:

1. Start the PortBroker backend server
2. Start the portal development server
3. Access the portal at `http://localhost:3000`
4. Test all features through the web interface

## Troubleshooting

### Common Issues

1. **CORS Issues**: Ensure the backend allows requests from `http://localhost:3000`
2. **Authentication Problems**: Check that JWT tokens are properly stored and sent
3. **API Connection Issues**: Verify the backend server is running on port 8000
4. **Build Errors**: Ensure all dependencies are installed with `npm install`

### Debug Mode

Enable debug mode in the settings to see detailed API request information in the browser console.

## Contributing

1. Follow the existing code style and structure
2. Use Vue 3 Composition API patterns
3. Implement proper error handling
4. Add appropriate TypeScript types if using TypeScript
5. Test thoroughly with the backend API

## License

This project is part of the PortBroker system and follows the same license terms.