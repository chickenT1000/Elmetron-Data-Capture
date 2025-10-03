# 10-Minute Rolling Charts Implementation Plan

**Task:** Add 10-Minute Rolling Charts Beneath Live Readouts  
**Priority:** High  
**Estimated Effort:** 2-3 days  
**Status:** Planning → Implementation

---

## Requirements

### Functional Requirements
1. **4 Synchronized Charts** - One for each measurement (pH, Redox, Conductivity, Temperature)
2. **10-Minute Sliding Window** - Display last 10 minutes of data
3. **Auto-Refresh** - Charts update as new measurements arrive
4. **Gap Handling** - Show gaps when no data available
5. **Time Synchronization** - All charts share the same time axis

### Non-Functional Requirements
- **Performance:** 60fps with 600 data points
- **Responsive:** Works on different screen sizes
- **Accessible:** Screen reader friendly
- **Archive Mode:** Handle gracefully when device offline

---

## Technical Design

### 1. Charting Library Selection

**Options Evaluated:**
- **Recharts** ✅ RECOMMENDED
  - React-native, declarative API
  - Good performance with moderate datasets
  - Built-in responsive container
  - Material-UI compatible styling
  
- **Chart.js**
  - More features, heavier
  - Imperative API (less React-friendly)
  
- **D3.js**
  - Most flexible
  - Steep learning curve
  - Overkill for this use case

**Decision:** Use **Recharts** for simplicity and React integration

### 2. Data Management

**API Endpoint Needed:**
```
GET /api/measurements/recent?minutes=10&session_id={current}
```

**Response Format:**
```json
{
  "session_id": 123,
  "start_time": "2025-10-02T10:00:00Z",
  "end_time": "2025-10-02T10:10:00Z",
  "measurements": [
    {
      "timestamp": "2025-10-02T10:00:00Z",
      "ph": 7.12,
      "redox": -110,
      "conductivity": 1450,
      "temperature": 22.5
    },
    // ... more measurements
  ]
}
```

**Data Fetching Strategy:**
- Initial load: Fetch last 10 minutes
- Updates: Poll every 2 seconds for new data
- Optimization: Only fetch measurements after last known timestamp

### 3. Component Structure

```
DashboardPage
├── MeasurementPanel (existing)
└── RollingChartsPanel (NEW)
    ├── ChartContainer
    │   ├── MeasurementChart (pH)
    │   ├── MeasurementChart (Redox)
    │   ├── MeasurementChart (Conductivity)
    │   └── MeasurementChart (Temperature)
    └── ChartControls (optional)
```

### 4. Component Props

```typescript
interface MeasurementChartProps {
  title: string;
  data: MeasurementDataPoint[];
  valueKey: 'ph' | 'redox' | 'conductivity' | 'temperature';
  unit: string;
  color: string;
  domain?: [number, number]; // Y-axis range
  loading?: boolean;
}

interface MeasurementDataPoint {
  timestamp: string;
  timestampMs: number; // For easier time calculations
  ph?: number | null;
  redox?: number | null;
  conductivity?: number | null;
  temperature?: number | null;
}
```

---

## Implementation Steps

### Phase 1: Backend API (if needed)
1. [ ] Check if `/api/measurements/recent` exists
2. [ ] If not, create endpoint in `data_api_service.py`
3. [ ] Test endpoint returns correct data format

### Phase 2: Data Hook
1. [ ] Create `useRecentMeasurements` hook
2. [ ] Implement 10-minute sliding window logic
3. [ ] Add polling/SSE for real-time updates
4. [ ] Handle archive mode (no updates)

### Phase 3: Chart Component
1. [ ] Install Recharts: `npm install recharts`
2. [ ] Create `MeasurementChart.tsx` component
3. [ ] Configure responsive container
4. [ ] Add time axis formatting
5. [ ] Add gap visualization
6. [ ] Style to match Material-UI theme

### Phase 4: Chart Container
1. [ ] Create `RollingChartsPanel.tsx`
2. [ ] Layout 4 charts (Grid or Stack)
3. [ ] Synchronize time axes
4. [ ] Add loading states
5. [ ] Add error handling

### Phase 5: Integration
1. [ ] Add to DashboardPage below MeasurementPanel
2. [ ] Connect to data hook
3. [ ] Test with live data
4. [ ] Test archive mode
5. [ ] Test gap scenarios

### Phase 6: Polish
1. [ ] Optimize performance (memoization)
2. [ ] Add chart legends
3. [ ] Add tooltips on hover
4. [ ] Responsive layout testing
5. [ ] Accessibility audit

---

## Code Snippets

### useRecentMeasurements Hook

```typescript
// ui/src/hooks/useRecentMeasurements.ts
import { useState, useEffect } from 'react';

export interface MeasurementDataPoint {
  timestamp: string;
  timestampMs: number;
  ph?: number | null;
  redox?: number | null;
  conductivity?: number | null;
  temperature?: number | null;
}

export function useRecentMeasurements(windowMinutes: number = 10, pollingMs: number = 2000) {
  const [data, setData] = useState<MeasurementDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(
          `/api/measurements/recent?minutes=${windowMinutes}`
        );
        if (!response.ok) throw new Error('Failed to fetch measurements');
        
        const result = await response.json();
        const measurements = result.measurements.map((m: any) => ({
          ...m,
          timestampMs: new Date(m.timestamp).getTime(),
        }));
        
        setData(measurements);
        setLoading(false);
      } catch (err) {
        setError(err as Error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, pollingMs);
    
    return () => clearInterval(interval);
  }, [windowMinutes, pollingMs]);

  return { data, loading, error };
}
```

### MeasurementChart Component

```typescript
// ui/src/components/MeasurementChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Paper, Typography, Box } from '@mui/material';
import { MeasurementDataPoint } from '../hooks/useRecentMeasurements';

interface MeasurementChartProps {
  title: string;
  data: MeasurementDataPoint[];
  valueKey: 'ph' | 'redox' | 'conductivity' | 'temperature';
  unit: string;
  color: string;
  loading?: boolean;
}

export function MeasurementChart({ title, data, valueKey, unit, color, loading }: MeasurementChartProps) {
  const formatXAxis = (timestampMs: number) => {
    return new Date(timestampMs).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatTooltip = (value: number) => {
    return `${value.toFixed(2)} ${unit}`;
  };

  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6">{title}</Typography>
        <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          Loading...
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>{title}</Typography>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="timestampMs" 
            tickFormatter={formatXAxis}
            domain={['dataMin', 'dataMax']}
            type="number"
          />
          <YAxis unit={` ${unit}`} />
          <Tooltip 
            labelFormatter={(value) => new Date(value).toLocaleString()}
            formatter={formatTooltip}
          />
          <Line 
            type="monotone" 
            dataKey={valueKey} 
            stroke={color} 
            strokeWidth={2}
            dot={false}
            connectNulls={false} // Show gaps
          />
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
}
```

### RollingChartsPanel Component

```typescript
// ui/src/components/RollingChartsPanel.tsx
import { Grid, Typography, Alert } from '@mui/material';
import { MeasurementChart } from './MeasurementChart';
import { useRecentMeasurements } from '../hooks/useRecentMeasurements';

export function RollingChartsPanel() {
  const { data, loading, error } = useRecentMeasurements(10, 2000);

  if (error) {
    return <Alert severity="error">Failed to load measurement history: {error.message}</Alert>;
  }

  return (
    <>
      <Typography variant="h5" sx={{ mb: 2 }}>
        10-Minute Rolling Charts
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <MeasurementChart
            title="pH"
            data={data}
            valueKey="ph"
            unit=""
            color="#2196f3"
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <MeasurementChart
            title="Redox Potential"
            data={data}
            valueKey="redox"
            unit="mV"
            color="#f44336"
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <MeasurementChart
            title="Conductivity"
            data={data}
            valueKey="conductivity"
            unit="μS/cm"
            color="#4caf50"
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <MeasurementChart
            title="Temperature"
            data={data}
            valueKey="temperature"
            unit="°C"
            color="#ff9800"
            loading={loading}
          />
        </Grid>
      </Grid>
    </>
  );
}
```

---

## Testing Strategy

### Unit Tests
- [ ] Test `useRecentMeasurements` hook with mock data
- [ ] Test time window filtering
- [ ] Test data transformation

### Integration Tests
- [ ] Test chart rendering with various data scenarios
- [ ] Test gap visualization
- [ ] Test time synchronization across charts

### Manual Tests
- [ ] View with live device connected
- [ ] View in archive mode
- [ ] View with gaps in data
- [ ] Responsive layout on mobile/tablet
- [ ] Performance with 600+ data points

---

## Performance Optimizations

1. **Memoization**
   ```typescript
   const chartData = useMemo(() => 
     data.filter(d => d.timestampMs > Date.now() - 10 * 60 * 1000),
     [data]
   );
   ```

2. **Debounced Updates**
   - Don't re-render on every single measurement
   - Batch updates every 1-2 seconds

3. **Virtual Scrolling** (if needed)
   - Only render visible charts
   - Lazy load off-screen charts

---

## Success Criteria

- [ ] 4 charts display correctly
- [ ] Charts update in real-time
- [ ] 10-minute window maintained
- [ ] Gaps visible when no data
- [ ] Time axes synchronized
- [ ] Performance: 60fps with 600 points
- [ ] Works in archive mode
- [ ] Responsive on mobile
- [ ] Accessible (keyboard navigation, screen readers)

---

## Dependencies

### NPM Packages
```bash
npm install recharts
npm install --save-dev @types/recharts
```

### API Endpoints
- Existing: `/health` (for latest measurement)
- New: `/api/measurements/recent?minutes=10` (to be created)

---

## Timeline

**Day 1:**
- Morning: Check/create backend API endpoint
- Afternoon: Implement `useRecentMeasurements` hook

**Day 2:**
- Morning: Create `MeasurementChart` component
- Afternoon: Create `RollingChartsPanel` component

**Day 3:**
- Morning: Integration into DashboardPage
- Afternoon: Testing, polish, performance optimization

---

**Status:** Ready to start implementation  
**Next Step:** Check if `/api/measurements/recent` endpoint exists
