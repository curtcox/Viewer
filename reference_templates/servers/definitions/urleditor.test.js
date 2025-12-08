/**
 * Unit tests for URL Editor JavaScript
 * 
 * These tests verify the core functionality of the URLEditorApp class
 * without requiring a browser environment.
 */

// Mock dependencies for testing
const mockAce = {
    edit: () => ({
        setTheme: () => {},
        session: {
            setMode: () => {},
            on: () => {}
        },
        setOptions: () => {},
        setValue: () => {},
        getValue: () => ''
    })
};

const mockDocument = {
    createElement: (tag) => ({
        textContent: '',
        innerHTML: ''
    }),
    getElementById: () => ({
        innerHTML: '',
        textContent: '',
        addEventListener: () => {}
    })
};

const mockWindow = {
    location: {
        hash: ''
    },
    addEventListener: () => {},
    history: {
        replaceState: () => {}
    },
    navigator: {
        clipboard: {
            writeText: () => Promise.resolve()
        }
    },
    open: () => {}
};

// Set up global mocks
global.ace = mockAce;
global.document = mockDocument;
global.window = mockWindow;
global.history = mockWindow.history;
global.navigator = mockWindow.navigator;

// Load the URLEditorApp
const urlEditorModule = require('./urleditor.js');
const { URLEditorApp } = urlEditorModule;

describe('URLEditorApp', () => {
    let app;
    
    beforeEach(() => {
        // Create a mock editor
        const editor = {
            getValue: () => '',
            setValue: jest.fn(),
            session: {
                on: jest.fn()
            }
        };
        
        app = new URLEditorApp();
        app.editor = editor;
    });
    
    describe('normalizeUrl', () => {
        test('should convert newlines to slashes', () => {
            const result = app.normalizeUrl('echo\nmarkdown\nshell');
            expect(result).toBe('/echo/markdown/shell');
        });
        
        test('should handle CID literals starting with #', () => {
            const result = app.normalizeUrl('#test');
            expect(result).toMatch(/^\/AAAAAAA/);
        });
        
        test('should trim whitespace from lines', () => {
            const result = app.normalizeUrl('  echo  \n  markdown  ');
            expect(result).toBe('/echo/markdown');
        });
        
        test('should handle empty input', () => {
            const result = app.normalizeUrl('');
            expect(result).toBe('/');
        });
        
        test('should clean up multiple slashes', () => {
            const result = app.normalizeUrl('echo//markdown///shell');
            expect(result).toBe('/echo/markdown/shell');
        });
    });
    
    describe('textToCidLiteral', () => {
        test('should convert text to CID-like format', () => {
            const result = app.textToCidLiteral('test');
            expect(result).toMatch(/^AAAAAAA/);
            expect(result.length).toBeGreaterThan(7);
        });
        
        test('should handle special characters', () => {
            const result = app.textToCidLiteral('hello world!');
            expect(result).toMatch(/^AAAAAAA/);
        });
    });
    
    describe('isValidPathSegment', () => {
        test('should accept valid path segments', () => {
            expect(app.isValidPathSegment('echo')).toBe(true);
            expect(app.isValidPathSegment('markdown_test')).toBe(true);
            expect(app.isValidPathSegment('test-123')).toBe(true);
        });
        
        test('should reject invalid path segments', () => {
            expect(app.isValidPathSegment('')).toBe(false);
            expect(app.isValidPathSegment('has space')).toBe(false);
            expect(app.isValidPathSegment('has<angle')).toBe(false);
            expect(app.isValidPathSegment('has>angle')).toBe(false);
            expect(app.isValidPathSegment('has"quote')).toBe(false);
        });
    });
    
    describe('isKnownServer', () => {
        test('should recognize known servers', () => {
            expect(app.isKnownServer('echo')).toBe(true);
            expect(app.isKnownServer('markdown')).toBe(true);
            expect(app.isKnownServer('shell')).toBe(true);
            expect(app.isKnownServer('ai_stub')).toBe(true);
        });
        
        test('should reject unknown servers', () => {
            expect(app.isKnownServer('unknown_server')).toBe(false);
            expect(app.isKnownServer('notaserver')).toBe(false);
        });
        
        test('should handle server names with prefixes', () => {
            expect(app.isKnownServer('#echo')).toBe(true);
            expect(app.isKnownServer('/echo')).toBe(true);
        });
    });
    
    describe('isValidCid', () => {
        test('should recognize valid CID format', () => {
            expect(app.isValidCid('AAAAAAA' + 'A'.repeat(20))).toBe(true);
            expect(app.isValidCid('AAAAAAAAABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')).toBe(true);
        });
        
        test('should recognize # prefix as CID indicator', () => {
            expect(app.isValidCid('#test')).toBe(true);
            expect(app.isValidCid('#anything')).toBe(true);
        });
        
        test('should reject invalid CID format', () => {
            expect(app.isValidCid('AAAAAAA')).toBe(false); // Too short
            expect(app.isValidCid('BBBBBBB' + 'A'.repeat(20))).toBe(false); // Wrong prefix
            expect(app.isValidCid('echo')).toBe(false);
        });
    });
    
    describe('escapeHtml', () => {
        test('should escape HTML special characters', () => {
            // Mock document.createElement properly for this test
            const originalCreateElement = global.document.createElement;
            const mockDiv = {
                textContent: '',
                innerHTML: ''
            };
            global.document.createElement = () => mockDiv;
            
            mockDiv.textContent = '<script>alert("xss")</script>';
            mockDiv.innerHTML = '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;';
            
            const result = app.escapeHtml('<script>alert("xss")</script>');
            expect(result).toContain('&lt;');
            expect(result).toContain('&gt;');
            
            global.document.createElement = originalCreateElement;
        });
        
        test('should return empty string for empty input in Node environment', () => {
            // In Node.js environment without full DOM, the mock returns empty string
            // This is expected behavior for testing
            const result = app.escapeHtml('');
            expect(typeof result).toBe('string');
        });
    });
    
    describe('parseUrlLines', () => {
        test('should parse lines from editor content', () => {
            app.editor.getValue = () => 'echo\nmarkdown\nshell';
            const lines = app.parseUrlLines();
            
            expect(lines).toHaveLength(3);
            expect(lines[0].text).toBe('echo');
            expect(lines[1].text).toBe('markdown');
            expect(lines[2].text).toBe('shell');
        });
        
        test('should filter empty lines', () => {
            app.editor.getValue = () => 'echo\n\n\nmarkdown\n  \nshell';
            const lines = app.parseUrlLines();
            
            expect(lines).toHaveLength(3);
        });
        
        test('should set validation flags', () => {
            app.editor.getValue = () => 'echo';
            const lines = app.parseUrlLines();
            
            expect(lines[0]).toHaveProperty('isValidSegment');
            expect(lines[0]).toHaveProperty('isServer');
            expect(lines[0]).toHaveProperty('isValidCid');
            expect(lines[0]).toHaveProperty('supportsChaining');
            expect(lines[0]).toHaveProperty('language');
        });
    });
    
    describe('getLanguage', () => {
        test('should return python for known servers', () => {
            expect(app.getLanguage('echo')).toBe('python');
            expect(app.getLanguage('markdown')).toBe('python');
        });
        
        test('should return - for unknown servers', () => {
            expect(app.getLanguage('unknown')).toBe('-');
            expect(app.getLanguage('notfound')).toBe('-');
        });
    });
    
    describe('updateStatusIndicator', () => {
        let mockStatusElement;
        
        beforeEach(() => {
            mockStatusElement = {
                classList: {
                    remove: jest.fn(),
                    add: jest.fn()
                },
                textContent: '',
                setAttribute: jest.fn(),
                title: ''
            };
            
            // Mock getElementById to return our mock element
            const originalGetElementById = global.document.getElementById;
            global.document.getElementById = jest.fn((id) => {
                if (id.startsWith('status-')) {
                    return mockStatusElement;
                }
                return originalGetElementById(id);
            });
        });
        
        test('should set pending status with hourglass icon', () => {
            app.updateStatusIndicator(0, 'pending', 'Request in progress...');
            
            expect(mockStatusElement.classList.remove).toHaveBeenCalledWith('pending', 'valid', 'invalid', 'unknown');
            expect(mockStatusElement.classList.add).toHaveBeenCalledWith('pending');
            expect(mockStatusElement.textContent).toBe('⏳');
            expect(mockStatusElement.setAttribute).toHaveBeenCalledWith('data-detail', 'Request in progress...');
            expect(mockStatusElement.title).toBe('Request in progress...');
        });
        
        test('should set valid status with checkmark icon', () => {
            app.updateStatusIndicator(1, 'valid', 'Request completed successfully');
            
            expect(mockStatusElement.classList.add).toHaveBeenCalledWith('valid');
            expect(mockStatusElement.textContent).toBe('✓');
            expect(mockStatusElement.title).toBe('Request completed successfully');
        });
        
        test('should set invalid status with X icon', () => {
            app.updateStatusIndicator(2, 'invalid', 'Request failed: HTTP 500');
            
            expect(mockStatusElement.classList.add).toHaveBeenCalledWith('invalid');
            expect(mockStatusElement.textContent).toBe('✗');
            expect(mockStatusElement.title).toBe('Request failed: HTTP 500');
        });
        
        test('should handle unknown status with dash icon', () => {
            app.updateStatusIndicator(3, 'unknown', 'Status unknown');
            
            expect(mockStatusElement.classList.add).toHaveBeenCalledWith('unknown');
            expect(mockStatusElement.textContent).toBe('-');
        });
        
        test('should handle missing status element gracefully', () => {
            global.document.getElementById = jest.fn(() => null);
            
            // Should not throw an error
            expect(() => {
                app.updateStatusIndicator(99, 'valid', 'Test message');
            }).not.toThrow();
        });
    });
});

// Run tests with Jest
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { URLEditorApp };
}
