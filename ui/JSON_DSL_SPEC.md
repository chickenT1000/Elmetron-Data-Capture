# JSON UI DSL Specification

## Overview

This JSON-based Domain-Specific Language (DSL) allows AI agents and automated tools to define, test, and validate UI components without writing TypeScript/JSX code directly.

## Design Goals

1. **Agent-Friendly**: Simple JSON structure that AI can generate and validate
2. **Type-Safe**: Schema validation with clear error messages
3. **Component-Agnostic**: Works with any React component
4. **Testable**: Built-in visual regression testing
5. **Deterministic**: Same input always produces same output

---

## Schema Definition

### Component Definition

```json
{
  "type": "component",
  "name": "Alert",
  "variant": "info",
  "props": {
    "className": "rounded-none border-b"
  },
  "children": [
    {
      "type": "icon",
      "name": "Info",
      "props": {
        "className": "h-4 w-4"
      }
    },
    {
      "type": "component",
      "name": "AlertTitle",
      "children": ["⚠️ Keep This Tab Open"]
    },
    {
      "type": "component",
      "name": "AlertDescription",
      "children": [
        "Do not close this browser tab while capturing data."
      ]
    }
  ]
}
```

### Test Suite Definition

```json
{
  "suite": "CloseWarningBanner Tests",
  "tests": [
    {
      "name": "renders with correct message",
      "component": {
        "type": "component",
        "name": "CloseWarningBanner"
      },
      "assertions": [
        {
          "type": "textContent",
          "selector": "h5",
          "value": "⚠️ Keep This Tab Open"
        }
      ],
      "snapshot": true
    }
  ]
}
```

---

## Node Types

### 1. Component Node

```typescript
interface ComponentNode {
  type: "component"
  name: string                    // Component name (e.g., "Alert")
  variant?: string                // Variant name (e.g., "info", "destructive")
  props?: Record<string, any>     // Component props
  children?: (ComponentNode | IconNode | string)[]
}
```

### 2. Icon Node

```typescript
interface IconNode {
  type: "icon"
  name: string                    // Icon name from lucide-react
  props?: {
    className?: string            // Tailwind classes
    size?: number                 // Icon size in pixels
  }
}
```

### 3. Layout Node

```typescript
interface LayoutNode {
  type: "layout"
  direction: "row" | "column"
  gap?: string                    // Tailwind gap class
  className?: string
  children: (ComponentNode | LayoutNode)[]
}
```

---

## Component Registry

The DSL interpreter uses a component registry to map names to actual React components:

```typescript
// ui/src/dsl/registry.ts
import * as AlertComponents from '../components/ui/alert'
import * as Icons from 'lucide-react'

export const componentRegistry = {
  // shadcn/ui components
  Alert: AlertComponents.Alert,
  AlertTitle: AlertComponents.AlertTitle,
  AlertDescription: AlertComponents.AlertDescription,
  
  // Custom components
  CloseWarningBanner: () => import('../components/CloseWarningBanner'),
  
  // Icons
  Info: Icons.Info,
  Check: Icons.Check,
  AlertCircle: Icons.AlertCircle,
  X: Icons.X,
}
```

---

## DSL Interpreter

### Basic Interpreter Flow

```typescript
// ui/src/dsl/interpreter.ts
import { createElement } from 'react'
import { componentRegistry } from './registry'

export function interpretNode(node: ComponentNode | IconNode | string) {
  // Handle text nodes
  if (typeof node === 'string') {
    return node
  }
  
  // Get component from registry
  const Component = componentRegistry[node.name]
  if (!Component) {
    throw new Error(`Component "${node.name}" not found in registry`)
  }
  
  // Handle children recursively
  const children = node.children?.map(interpretNode)
  
  // Create React element
  return createElement(Component, node.props, ...children)
}
```

---

## Usage Examples

### 1. Simple Alert

**JSON DSL:**
```json
{
  "type": "component",
  "name": "Alert",
  "variant": "info",
  "children": ["This is an informational alert"]
}
```

**Rendered Output:**
```tsx
<Alert variant="info">
  This is an informational alert
</Alert>
```

### 2. Complex Layout

**JSON DSL:**
```json
{
  "type": "layout",
  "direction": "column",
  "gap": "gap-4",
  "children": [
    {
      "type": "component",
      "name": "Alert",
      "variant": "info",
      "children": ["First alert"]
    },
    {
      "type": "component",
      "name": "Alert",
      "variant": "destructive",
      "children": ["Second alert"]
    }
  ]
}
```

---

## Visual Regression Testing

### Test Runner

```typescript
// ui/src/dsl/test-runner.ts
import { interpretNode } from './interpreter'
import { render } from '@testing-library/react'
import { toMatchImageSnapshot } from 'jest-image-snapshot'

export async function runDSLTest(testDef: TestDefinition) {
  // Interpret DSL to React component
  const component = interpretNode(testDef.component)
  
  // Render component
  const { container } = render(component)
  
  // Run assertions
  for (const assertion of testDef.assertions) {
    runAssertion(container, assertion)
  }
  
  // Take snapshot if requested
  if (testDef.snapshot) {
    expect(container).toMatchImageSnapshot()
  }
}
```

---

## CLI Tool

```bash
# Render DSL from JSON file
npm run dsl:render -- component.json

# Run tests from DSL
npm run dsl:test -- tests/*.json

# Generate component from DSL
npm run dsl:generate -- alert.json --output src/components/MyAlert.tsx
```

---

## Benefits for AI Agents

1. **Structured Format**: JSON is easy for AI to generate and parse
2. **No Syntax Errors**: Validated JSON prevents compilation errors
3. **Incremental Building**: Can generate components piece by piece
4. **Self-Testing**: Built-in testing framework
5. **Human-Readable**: Easy to review AI-generated UI code

---

## Future Enhancements

1. **State Management**: Add state definition to DSL
2. **Event Handlers**: Support for onClick, onChange, etc.
3. **Conditional Rendering**: if/else logic in DSL
4. **Data Binding**: Connect DSL to API responses
5. **Animation**: Define transitions and animations

---

## Implementation Status

- ⏳ Schema definition (THIS DOCUMENT)
- ⏳ Component registry
- ⏳ DSL interpreter
- ⏳ Test runner
- ⏳ CLI tool
- ⏳ Integration with existing codebase
