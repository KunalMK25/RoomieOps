# Development Guide

## Running the Frontend

### Prerequisites
- Node.js 18+ 
- npm or pnpm

### Setup

```bash
cd frontend
npm install
```

### Development Mode

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (Vite default) and supports hot module reloading.

**Key Features:**
- Mock API integration using simulated backend responses
- All four processing stages render correctly
- Language switching between English and Kannada
- Three main screens: Upload, Processing, Results

### Build for Production

```bash
npm run build
```

Outputs to `frontend/dist/`.

### Linting

```bash
npm run lint
```

### Type Checking

```bash
npm run type-check
```

---

## Frontend Architecture

### Key Files

**State Management:**
- `src/App.tsx` — Root component managing screen navigation and result state
- `src/types/index.ts` — TypeScript interfaces for all data structures

**Screens:**
- `src/screens/Upload.tsx` — File upload, situation input, language selection
- `src/screens/Processing.tsx` — Animated pipeline status display
- `src/screens/Results.tsx` — Risk tier display, clause citations, "Why?" explanation

**API Integration:**
- `src/api/client.ts` — Real API client (placeholder for AWS API Gateway)
- `src/api/mock.ts` — Mock responses simulating Bedrock pipeline output

### Component State Flow

```
App (manages global state)
├── currentScreen: 'upload' | 'processing' | 'results'
├── processingState: { documentId, docType, situation, language, file? }
└── result: ProcessedDocument

Upload → generates documentId + file → calls handleUploadSubmit → sets processingState
Processing → runs simulation → calls handleProcessingComplete with result
Results → displays result → onReset clears state
```

### Data Types

All types defined in `src/types/index.ts`:

```typescript
// Core types
RiskTier = 'green' | 'yellow' | 'red'
Confidence = 'high' | 'medium' | 'low'
Language = 'en' | 'kn'

// Extracted from document
Clause { clauseId, text, section }

// AI reasoning outputs
Match { clauseId, relevance, userFact }
RiskResult { riskTier, clauseId, reasoning, confidence }
ExplanationResult { explanation, language }

// Complete result
ProcessedDocument {
  documentId, docType, status, 
  extractedClauses[], riskResult, 
  explanations{}, error, createdAt
}
```

---

## Mock API

### Purpose

Simulates backend pipeline without AWS credentials or Bedrock access. Allows frontend development to proceed independently.

### Key Functions

**`simulateProcessing(documentId, situation, language)`**
- Simulates all 4 pipeline stages with realistic delays
- Returns a complete `ProcessedDocument`
- Chooses mock result based on situation keywords:
  - "85" → green result (high attendance)
  - "medical" → yellow result (medical exemption scenario)
  - default → red result (below threshold)

**Mock Data**
- `mockClauses[]` — Pre-extracted clauses from the demo regulation
- `mockRiskResults` — Result objects for different scenarios
- `mockExplanations` — English and Kannada explanations for each scenario

### Current Mock Scenarios

1. **below_threshold** (default)
   - Attendance: 72%
   - Risk: Red
   - Explanation: Below threshold, needs medical exemption
   - Language: English + Kannada

2. **above_threshold**
   - Attendance: 85%
   - Risk: Green
   - Explanation: Above threshold, eligible to write exam
   - Language: English + Kannada

3. **below_with_medical**
   - Attendance: 72% + medical reason
   - Risk: Yellow
   - Explanation: Below threshold but eligible for condonation
   - Language: English + Kannada

4. **low_confidence**
   - Risk: Yellow with low confidence
   - Explanation: Ambiguous, requires manual review
   - Language: English + Kannada

### Replacing Mock with Real API

When backend is ready, replace `simulateProcessing()` calls in `Processing.tsx` with:

```typescript
import { apiClient } from '../api/client'

// Instead of simulateProcessing:
const result = await apiClient.pollDocument(documentId)
```

---

## Styling

### Design System

**Colors:**
- Primary: `#667eea` (purple-blue)
- Accent: `#764ba2` (purple)
- Success (green): `#4caf50`
- Warning (yellow): `#ff9800`
- Error (red): `#f44336`
- Neutral: `#f5f5f5`, `#ddd`, `#999`

**Typography:**
- Headings: sans-serif, 700 weight
- Body: sans-serif, 400 weight, line-height 1.6
- Accent: monospace for code/values

**Spacing:**
- Base unit: 4px (multiples: 8, 12, 16, 20, 24, 30, etc.)
- Mobile padding: 16px
- Desktop padding: 20px
- Form gap: 20px

**Responsive:**
- Mobile-first design
- Breakpoint: 640px (max-width)
- Containers max-width: 500–600px
- Stack vertically on mobile, center horizontally

### CSS Modules

Each screen has its own `.css` file:
- `src/screens/Upload.css` — form styling, file input
- `src/screens/Processing.css` — animated stages, progress bar
- `src/screens/Results.css` — risk cards, expandable sections
- `src/App.css` — root container layout
- `src/index.css` — global styles, root element

---

## Testing the Frontend (Manual)

### Test Flow

1. **Upload Screen**
   - Select a file (any PDF/image)
   - Choose a document type
   - Enter a situation description
   - Choose a language
   - Click "Analyze"
   - Verify documentId is generated

2. **Processing Screen**
   - All 5 stages animate in sequence
   - Progress bar fills
   - Each stage shows completion checkmark
   - Processing completes after ~11 seconds

3. **Results Screen**
   - Risk card displays with correct emoji (🟢🟡🔴)
   - Explanation text visible
   - "Why?" button expands to show reasoning
   - Source clause displayed in expandable section
   - Confidence badge visible
   - Language selector works (changes explanation)
   - Disclaimer present
   - "Back" and "Analyze Another" buttons work

### Test Scenarios

**Scenario 1: Above Threshold**
- Situation: "I have 85% attendance"
- Expected: Green result, "All Clear"

**Scenario 2: Below Threshold**
- Situation: "I have 72% attendance"
- Expected: Red result, "Potential Issue"

**Scenario 3: Medical Exemption**
- Situation: "I have 72% attendance and missed classes because of a medical reason"
- Expected: Yellow result, "Pay Attention"

**Scenario 4: Language Switch**
- Any situation, then switch language to Kannada
- Expected: Explanation changes to Kannada text

---

## Debugging

### Common Issues

**Vite build fails:**
```bash
npm install  # Ensure all dependencies installed
npm run build  # Try again
```

**Hot reload not working:**
- Restart dev server: `npm run dev`
- Clear browser cache

**TypeScript errors:**
```bash
npm run type-check  # Check all types
```

**Linting errors:**
```bash
npm run lint  # See all issues
```

### Development Tools

- **Browser DevTools:** Chrome/Firefox DevTools for React component inspection
- **TypeScript:** All components are fully typed, IDE provides autocomplete
- **Vite:** Fast rebuilds, good error messages

---

## Next Steps

Once Phase 2 (AWS Foundation) is complete:

1. Replace mock API with real API Gateway endpoints
2. Implement Cognito authentication
3. Add real S3 document upload
4. Connect to Step Functions pipeline
5. Verify DynamoDB result storage

Until then, the frontend works end-to-end with mock data for testing UI/UX.
