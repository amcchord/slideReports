# LLM CSS Preservation Guide

## Problem
When LLMs create artifacts or modify templates, they often drop the `runbook-styles.css` reference because they don't know what's in the external file and may attempt to recreate styling themselves.

## Why runbook-styles.css is Critical

The `runbook-styles.css` file contains essential styling that cannot be easily recreated:

### 1. Custom Color Scheme
```css
:root {
    --dark-navy: #213448;
    --medium-blue: #547792;
    --light-blue: #94B4C1;
    --light-cream: #F8F9F5;
    /* ... more variables */
}
```

### 2. LLM-Specific Placeholder Styling
```css
.llm-placeholder {
    background: var(--light-cream);
    border: 2px dashed var(--medium-blue);
    /* ... distinctive styling */
}

.llm-placeholder::before {
    content: "● LLM_FILL: ";
    font-weight: 600;
    color: var(--medium-blue);
}
```

### 3. Custom Components
- `.section-header` - Styled section dividers
- `.contact-card` - Emergency contact styling
- `.server-card` - Server inventory cards
- `.priority-high/medium/low` - Priority indicators
- `.timeline-item` - Recovery sequence styling
- `.step-number` - Numbered step circles

### 4. Print Media Queries
- Page breaks between sections
- Print-optimized colors and layout
- Prevents content from breaking across pages

### 5. Mobile Responsive Design
- Tablet and phone optimizations
- Adjusted padding and fonts for smaller screens

## Strategies to Preserve CSS Reference

### Strategy 1: Descriptive Comments ✅ IMPLEMENTED
Add comments that hint at the CSS content:

**HTML:**
```html
<!-- CRITICAL: Custom runbook styles including .llm-placeholder, section headers, print styles, color scheme -->
<link href="https://raw.githubusercontent.com/amcchord/slideReports/main/runbook-styles.css" rel="stylesheet">
```

**HAML:**
```haml
/ CRITICAL: Custom runbook styles including .llm-placeholder, section headers, print styles, color scheme
%link{href: "https://raw.githubusercontent.com/amcchord/slideReports/main/runbook-styles.css", rel: "stylesheet"}
```

### Strategy 2: Explicit Instructions in Prompts
When asking LLMs to modify the runbook, always include:

```
IMPORTANT: Always preserve the runbook-styles.css link in the <head>. 
This file contains critical styling for:
- .llm-placeholder elements with dashed borders
- Custom color scheme (navy/blue/cream theme)
- Section headers and component styling
- Print media queries for proper PDF generation
- Mobile responsive design
```

### Strategy 3: Template with CSS Summary
Create a version with an embedded comment that lists the key classes:

```html
<!-- 
DEPENDENCIES: runbook-styles.css contains these critical classes:
- .llm-placeholder (dashed border placeholders)
- .section-header (styled section dividers)  
- .contact-card, .server-card (component styling)
- .priority-high/.priority-medium/.priority-low
- .timeline-item, .step-number
- Print media queries for sections
- Mobile responsive breakpoints
-->
```

### Strategy 4: Inline Critical Styles (Fallback)
If the CSS link must be dropped, these are the most critical styles to preserve inline:

```css
<style>
.llm-placeholder {
    background: #F8F9F5;
    border: 2px dashed #547792;
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 4px;
    font-style: italic;
    color: #213448;
}
.llm-placeholder::before {
    content: "● LLM_FILL: ";
    font-weight: 600;
    color: #547792;
    font-style: normal;
}
</style>
```

### Strategy 5: Self-Documenting CSS Link
Use a data attribute to document the CSS purpose:

```html
<link href="https://raw.githubusercontent.com/amcchord/slideReports/main/runbook-styles.css" 
      rel="stylesheet"
      data-purpose="llm-placeholders,section-styling,print-layout,color-scheme">
```

## Best Practices When Working with LLMs

1. **Always mention the CSS** in your prompt
2. **Specify which classes** are used in the template
3. **Explain why** the external CSS cannot be recreated
4. **Ask the LLM to confirm** it will preserve the link
5. **Provide examples** of what breaks without the CSS

## Template Verification Checklist

Before using any LLM-generated version, verify:
- [ ] `runbook-styles.css` link is present in `<head>`
- [ ] `.llm-placeholder` elements are used for content placeholders
- [ ] Section headers use `.section-header` class
- [ ] Contact and server cards use proper classes
- [ ] No inline styles attempt to replace the external CSS
- [ ] Print media queries are not embedded inline

## Emergency CSS Recovery

If the CSS link is lost and you need to restore styling quickly:

1. **Check the original files** (`runbook.html` or `runbook.haml`)
2. **Re-add the link** with the descriptive comment
3. **Verify class usage** matches the CSS definitions
4. **Test print layout** to ensure media queries work

## File Locations

- **Main CSS:** `runbook-styles.css` (454 lines of custom styling)
- **HTML Template:** `runbook.html` (with preserved CSS link)  
- **HAML Template:** `runbook.haml` (with preserved CSS link)
- **This Guide:** `llm-css-preservation-guide.md` 