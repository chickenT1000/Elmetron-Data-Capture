# UI Migration Guide: MUI → shadcn/ui + Tailwind CSS

## Overview

This document tracks the migration from Material-UI (MUI) to shadcn/ui + Tailwind CSS for better performance, smaller bundle size, and agent-friendly architecture.

## Migration Status

### Phase 1: Setup & Configuration ✅ COMPLETE

**Installed Dependencies:**
- `tailwindcss` - Utility-first CSS framework
- `postcss`, `autoprefixer` - CSS processing
- `class-variance-authority` - Component variants
- `clsx`, `tailwind-merge` - Utility functions  
- `lucide-react` - Modern icon library

**Configuration Files:**
- ✅ `ui/tailwind.config.js` - Tailwind configuration with shadcn/ui theme
- ✅ `ui/postcss.config.js` - PostCSS configuration
- ✅ `ui/src/index.css` - Tailwind directives + CSS variables
- ✅ `ui/src/lib/utils.ts` - `cn()` utility function

**Component Library Structure:**
```
ui/src/components/ui/
  ├── alert.tsx          ✅ COMPLETE
  ├── button.tsx         ⏳ TODO
  ├── card.tsx           ⏳ TODO
  ├── input.tsx          ⏳ TODO
  ├── select.tsx         ⏳ TODO
  └── ...
```

### Phase 2: Component Migration 🔄 IN PROGRESS

**Migrated Components:**
- ✅ `CloseWarningBanner` - MUI Alert → shadcn/ui Alert + Lucide icons

**Pending Components:**
- ⏳ `AppLayout` - Complex layout with Drawer, AppBar
- ⏳ `OfflineWarning` - MUI Modal/Dialog
- ⏳ Dashboard page components
- ⏳ Service Health page components
- ⏳ Session Evaluation page components

### Phase 3: JSON DSL Implementation 📋 TODO

**Planned Features:**
1. JSON schema for component definitions
2. Component registry system
3. DSL interpreter/runner
4. Visual regression testing

---

## Design Tokens

The new design system uses CSS variables for theming:

### Light Theme
```css
--primary: 210 98% 48%          /* Material Blue #1976D2 */
--background: 0 0% 100%         /* White */
--foreground: 222.2 84% 4.9%    /* Almost black */
```

### Dark Theme  
```css
--primary: 210 98% 48%          /* Material Blue (same) */
--background: 222.2 84% 4.9%    /* Dark blue-gray */
--foreground: 210 40% 98%       /* Almost white */
```

---

## Migration Patterns

### Before (MUI):
```tsx
import { Alert, AlertTitle } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';

<Alert severity="info" icon={<InfoIcon />}>
  <AlertTitle>Warning</AlertTitle>
  Message here
</Alert>
```

### After (shadcn/ui + Tailwind):
```tsx
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import { Info } from 'lucide-react';

<Alert variant="info">
  <Info className="h-4 w-4" />
  <AlertTitle>Warning</AlertTitle>
  <AlertDescription>Message here</AlertDescription>
</Alert>
```

---

## Benefits

✅ **Bundle Size**: ~300KB → ~50KB (-83%)
✅ **Performance**: No runtime CSS-in-JS overhead  
✅ **Testing**: Static Tailwind classes (easier to test)
✅ **Agent-Friendly**: JSON DSL for AI tools
✅ **Accessibility**: Built on Radix UI primitives
✅ **Modern**: Latest React patterns

---

## Next Steps

1. **Continue Component Migration**
   - Migrate `AppLayout` to use Tailwind
   - Add more shadcn/ui components as needed

2. **Design JSON DSL**
   - Define schema for component definitions
   - Build component registry
   - Implement interpreter

3. **Remove MUI**
   - After all components migrated
   - Remove `@mui/material`, `@emotion` dependencies

---

## Resources

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [Radix UI Documentation](https://www.radix-ui.com/)
- [Lucide Icons](https://lucide.dev/)
