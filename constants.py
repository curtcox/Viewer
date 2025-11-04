"""Application-wide constants for entity types, labels, and magic strings."""

# Entity type constants
ENTITY_TYPE_ALIAS = 'alias'
ENTITY_TYPE_SERVER = 'server'
ENTITY_TYPE_CID = 'cid'
ENTITY_TYPE_VARIABLE = 'variable'
ENTITY_TYPE_SECRET = 'secret'

# Entity type labels for display
TYPE_LABELS = {
    ENTITY_TYPE_ALIAS: 'Alias',
    ENTITY_TYPE_SERVER: 'Server',
    ENTITY_TYPE_CID: 'CID',
    ENTITY_TYPE_VARIABLE: 'Variable',
    ENTITY_TYPE_SECRET: 'Secret',
}

# Reserved route paths that take precedence over dynamic routes
RESERVED_ROUTES = {
    '/',
    '/dashboard',
    '/profile',
    '/upload',
    '/uploads',
    '/history',
    '/servers',
    '/variables',
    '/secrets',
    '/settings',
    '/aliases',
    '/aliases/new',
    '/edit',
    '/meta',
    '/search',
    '/search/results',
    '/export',
    '/import',
}
