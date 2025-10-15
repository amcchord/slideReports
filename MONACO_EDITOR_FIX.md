# Monaco Editor Fix - Template HTML Not Showing/Saving

## Problem

The Monaco HTML editor was blank and templates weren't being saved properly:
1. Monaco editor displayed blank even when templates had HTML content
2. AI-generated templates appeared in preview but editor showed nothing
3. Templates weren't getting saved to database
4. Hidden textarea wasn't being read correctly

## Root Causes

### 1. **Scope Issue - Monaco Not Globally Accessible**
- Monaco was declared as `let monacoEditor = null` in template scope
- `main.js` couldn't access it to update after AI generation
- Variable wasn't on `window` object

### 2. **Save Function Reading Wrong Source**
- `saveTemplate()` only read from hidden textarea
- Monaco editor was updating textarea via events
- But no fallback to read directly from Monaco if textarea wasn't updated yet

### 3. **Timing Issues**
- Monaco loads asynchronously via RequireJS
- AI generation might complete before Monaco finished loading
- No retry mechanism if Monaco wasn't ready

### 4. **No Error Handling**
- Silent failures if Monaco didn't initialize
- No fallback to regular textarea
- No console logging for debugging

## Fixes Applied

### Fix 1: Make Monaco Globally Accessible
**File: `templates/template_editor.html`**

```javascript
// Make Monaco globally accessible for other scripts
window.monacoEditor = monacoEditor;
window.monacoEditorInstance = monacoEditor;
```

Now other scripts can access Monaco via `window.monacoEditor`.

### Fix 2: Update Save Function to Read from Monaco
**File: `templates/template_editor.html`**

```javascript
async function saveTemplate() {
    // Get HTML content from Monaco editor if available, otherwise from textarea
    let htmlContent;
    if (monacoEditor) {
        htmlContent = monacoEditor.getValue();
    } else {
        htmlContent = document.getElementById('template-html').value;
    }
    // ... rest of save logic
}
```

Now saves read directly from Monaco editor first, with textarea as fallback.

### Fix 3: Enhanced Monaco Initialization
**File: `templates/template_editor.html`**

Added:
- ✅ DOM ready check with `addEventListener('DOMContentLoaded')`
- ✅ Error handling with try-catch
- ✅ Container existence check
- ✅ Console logging for debugging
- ✅ Fallback to show textarea if Monaco fails
- ✅ Load error handler for RequireJS

```javascript
document.addEventListener('DOMContentLoaded', function() {
    require(['vs/editor/editor.main'], function() {
        try {
            // Check if container exists
            if (!editorContainer) {
                console.error('Monaco editor container not found');
                return;
            }
            
            // Create editor
            monacoEditor = monaco.editor.create(...);
            
            console.log('Monaco Editor initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Monaco Editor:', error);
            // Fallback: show the textarea
            document.getElementById('template-html').style.display = 'block';
        }
    }, function(err) {
        console.error('Failed to load Monaco Editor:', err);
        // Fallback: show the textarea
        document.getElementById('template-html').style.display = 'block';
    });
});
```

### Fix 4: Robust AI Generation Update
**File: `static/js/main.js`**

```javascript
// Update the hidden textarea first (always)
const htmlField = document.getElementById('template-html');
if (htmlField) {
    htmlField.value = data.html;
}

// Try to update Monaco editor if it exists
const editor = window.monacoEditor || window.monacoEditorInstance;
if (editor && editor.setValue) {
    try {
        editor.setValue(data.html);
        console.log('Updated Monaco editor with generated template');
    } catch (e) {
        console.error('Failed to update Monaco editor:', e);
    }
} else {
    console.log('Monaco editor not ready, updated textarea. Will retry...');
    
    // Wait a bit and try again (Monaco might still be loading)
    setTimeout(() => {
        const retryEditor = window.monacoEditor || window.monacoEditorInstance;
        if (retryEditor && retryEditor.setValue) {
            retryEditor.setValue(data.html);
            console.log('Updated Monaco editor (retry succeeded)');
        }
    }, 500);
    
    // Update preview manually since Monaco isn't ready
    if (previewFrame) {
        // ... manual preview update
    }
}
```

**Key improvements:**
- ✅ Always update hidden textarea first
- ✅ Check both `window.monacoEditor` and `window.monacoEditorInstance`
- ✅ Try-catch for Monaco updates
- ✅ 500ms retry if Monaco not ready yet
- ✅ Manual preview update as fallback
- ✅ Extensive console logging

## Testing Flow

### Scenario 1: View Existing Template
1. User clicks "Edit" on a template
2. Page loads with hidden textarea containing HTML
3. Monaco loads asynchronously
4. Monaco reads from textarea and displays content
5. ✅ User sees HTML in editor with syntax highlighting

### Scenario 2: AI Generate Template
1. User enters description and clicks "Generate with AI"
2. AI generates HTML (takes 1-5 minutes)
3. Response arrives, code updates:
   - Hidden textarea ← HTML
   - Check for Monaco
   - If ready: Monaco.setValue(HTML)
   - If not: Wait 500ms and retry
   - Preview updates
4. ✅ User sees HTML in both editor and preview

### Scenario 3: Save Template
1. User clicks "Save Template"
2. Code reads from Monaco (if loaded) or textarea (fallback)
3. Sends HTML to server
4. ✅ Template saved correctly

### Scenario 4: Monaco Fails to Load
1. Monaco CDN fails or browser issue
2. Error caught and logged
3. Hidden textarea is shown (display: block)
4. ✅ User can still edit HTML in plain textarea

## Debug Console Commands

To check Monaco status in browser console:

```javascript
// Check if Monaco is loaded
console.log('Monaco loaded:', !!window.monacoEditor);

// Get current content
if (window.monacoEditor) {
    console.log('Content length:', window.monacoEditor.getValue().length);
}

// Manually set content (for testing)
if (window.monacoEditor) {
    window.monacoEditor.setValue('<html><body>Test</body></html>');
}

// Check hidden textarea
console.log('Textarea value:', document.getElementById('template-html').value);
```

## Files Modified

1. **`/var/www/reports.slide.recipes/templates/template_editor.html`**
   - Enhanced Monaco initialization with error handling
   - Made Monaco globally accessible
   - Updated save function to read from Monaco first

2. **`/var/www/reports.slide.recipes/static/js/main.js`**
   - Always update hidden textarea
   - Check both global Monaco references
   - Add retry mechanism
   - Extensive logging

## Benefits

✅ **Monaco displays content correctly** - Loads existing templates  
✅ **AI generation works** - Updates Monaco after generation  
✅ **Templates save properly** - Reads from correct source  
✅ **Graceful degradation** - Falls back to textarea if Monaco fails  
✅ **Better debugging** - Console logs help troubleshoot issues  
✅ **Retry mechanism** - Handles async loading race conditions  
✅ **Error handling** - Catches and logs failures  

## Before vs After

### Before
```
User generates template with AI
↓
Template shows in preview
↓
Editor is blank ❌
↓
User tries to save
↓
Reads from blank textarea ❌
↓
Nothing saved ❌
```

### After
```
User generates template with AI
↓
Updates hidden textarea ✅
↓
Updates Monaco editor ✅
↓
Template shows in preview ✅
↓
User sees HTML in editor ✅
↓
User clicks save ✅
↓
Reads from Monaco ✅
↓
Template saved correctly ✅
```

## Additional Improvements Made

1. **Better async handling** - Waits for DOM ready
2. **Multiple fallbacks** - Textarea → Monaco → Retry → Manual preview
3. **Global accessibility** - Sets both `window.monacoEditor` and `window.monacoEditorInstance`
4. **Console visibility** - All key operations logged
5. **Error recovery** - Shows textarea if Monaco fails completely

## Testing Checklist

- [ ] View existing template - HTML appears in Monaco
- [ ] Generate new template with AI - HTML appears in Monaco
- [ ] Edit HTML in Monaco - Preview updates
- [ ] Save new template - Saves correctly
- [ ] Save edited template - Updates correctly
- [ ] Clone built-in template - HTML appears in Monaco
- [ ] Test with slow connection - Retry mechanism works
- [ ] Test with Monaco blocked - Textarea fallback works

## Known Limitations

- 500ms retry delay may not be enough on very slow connections
- Only retries once (could implement exponential backoff)
- Console logs stay in production (could be removed or made conditional)

## Future Enhancements

1. Show loading indicator while Monaco initializes
2. Exponential backoff for retries (500ms, 1s, 2s)
3. Visual indicator when using textarea fallback
4. "Monaco not loaded" notification to user
5. Option to manually reload Monaco if it fails

