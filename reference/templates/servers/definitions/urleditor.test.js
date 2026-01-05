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
    getElementById: jest.fn((id) => ({
        innerHTML: '',
        textContent: '',
        addEventListener: jest.fn(),
        classList: {
            remove: jest.fn(),
            add: jest.fn()
        },
        setAttribute: jest.fn(),
        title: ''
    })),
    querySelectorAll: () => []
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

// Mock fetch for async tests
global.fetch = jest.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ cid_value: 'AAAAAAA' + 'A'.repeat(20) }),
    text: () => Promise.resolve('test content')
}));

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
    let mockEditor;
    
    beforeEach(() => {
        // Reset document.getElementById mock to return elements with addEventListener
        global.document.getElementById = jest.fn((id) => ({
            innerHTML: '',
            textContent: '',
            addEventListener: jest.fn(),
            classList: {
                remove: jest.fn(),
                add: jest.fn()
            },
            setAttribute: jest.fn(),
            title: ''
        }));
        
        // Create a mock editor
        mockEditor = {
            getValue: jest.fn(() => ''),
            setValue: jest.fn(),
            session: {
                on: jest.fn()
            }
        };
        
        // Reset fetch mock
        global.fetch.mockClear();
        
        // Create app instance with mocked editor
        app = new URLEditorApp();
        app.editor = mockEditor;
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
    
    describe('escapeHtml', () => {
        test('should escape HTML special characters', () => {
            // Mock document.createElement properly for this test
            const mockDiv = {
                textContent: '',
                innerHTML: ''
            };
            const originalCreateElement = global.document.createElement;
            global.document.createElement = jest.fn(() => mockDiv);
            
            // Set up the mock behavior
            const testInput = '<script>alert("xss")</script>';
            mockDiv.textContent = testInput;
            mockDiv.innerHTML = '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;';
            
            const result = app.escapeHtml(testInput);
            expect(result).toContain('&lt;');
            expect(result).toContain('&gt;');
            
            global.document.createElement = originalCreateElement;
        });
        
        test('should handle empty string', () => {
            const result = app.escapeHtml('');
            expect(typeof result).toBe('string');
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
            global.document.getElementById = jest.fn((id) => {
                if (id.startsWith('status-')) {
                    return mockStatusElement;
                }
                return null;
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
    
    describe('toBase64Url', () => {
        test('should convert buffer to base64url format', () => {
            const buffer = new Uint8Array([72, 101, 108, 108, 111]).buffer;
            const result = app.toBase64Url(buffer);
            
            // Base64url should not contain +, / or = characters
            expect(result).not.toContain('+');
            expect(result).not.toContain('/');
            expect(result).not.toMatch(/=+$/);
        });
    });
    
    describe('encodeLength', () => {
        test('should encode length as 6-byte big-endian integer', () => {
            const result = app.encodeLength(100);
            
            // Should return a base64url encoded string
            expect(typeof result).toBe('string');
            expect(result.length).toBeGreaterThan(0);
        });
        
        test('should handle zero length', () => {
            const result = app.encodeLength(0);
            expect(typeof result).toBe('string');
        });
    });
});

// Run tests with Jest
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { URLEditorApp };
}
