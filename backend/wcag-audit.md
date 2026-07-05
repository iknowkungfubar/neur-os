# Phase 1.6: WCAG 3.0 Bronze — Frontend Accessibility

## Audit against WCAG 3.0 Bronze requirements

### Clear Language
- ✅ Jargon elimination (all text is plain English)
- ❌ Some color-only indicators (traffic lights need text labels for screen readers)
- ✅ Short sentences, active voice

### Predictable Interaction
- ✅ Consistent navigation order
- ❌ No undo on destructive actions (no "are you sure?" before crisis mode)
- ✅ Keyboard navigation available

### Error Prevention
- ✅ No data loss on brain dump (auto-saves to API)
- ❌ Timer: no confirm before stop (stop is instant)
- ✅ Form validation on check-in

### Fixes needed
1. Add aria-labels to traffic light mode dots
2. Add confirm dialog before crisis mode activation
3. Ensure all interactive elements have visible focus indicators
