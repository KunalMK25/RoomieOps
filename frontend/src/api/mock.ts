import { ProcessedDocument, Clause, RiskResult, Language } from '../types'

/**
 * Mock Bedrock responses for testing without AWS access.
 * These simulate the exact output format expected from the four-stage pipeline.
 */

export const mockClauses: Clause[] = [
  {
    clauseId: 'c1',
    text: 'All students are required to maintain a minimum attendance of 75% in all courses across the academic session.',
    section: '4.1',
  },
  {
    clauseId: 'c2',
    text: 'Attendance is calculated as: Total number of classes attended / Total number of classes held × 100',
    section: '4.2',
  },
  {
    clauseId: 'c3',
    text: 'A student is eligible to write the examination if they meet both: (1) Attendance of at least 75%, OR attendance of at least 70% with condonation approval',
    section: '6.1',
  },
  {
    clauseId: 'c4',
    text: 'Students may request condonation of absence due to medical reasons: Medical certificate must be issued by a recognized hospital or medical practitioner. Application must be submitted within 7 days of return to campus.',
    section: '5.1',
  },
  {
    clauseId: 'c5',
    text: 'Condonation of up to 5% of the required attendance may be granted for documented medical emergencies or hospitalization.',
    section: '5.2',
  },
]

export const mockRiskResults = {
  below_threshold: {
    riskTier: 'red' as const,
    clauseId: 'c1',
    reasoning: 'Stated attendance (72%) is below the 75% threshold in clause 4.1. Without medical condonation, you may be ineligible to write your exam.',
    confidence: 'high' as const,
  },
  above_threshold: {
    riskTier: 'green' as const,
    clauseId: 'c1',
    reasoning: 'Stated attendance (85%) exceeds the required 75% threshold. You are eligible to write your exam.',
    confidence: 'high' as const,
  },
  below_with_medical: {
    riskTier: 'yellow' as const,
    clauseId: 'c4',
    reasoning: 'Your attendance is 72%, below the 75% threshold. However, you have a medical reason. You may be eligible for condonation (up to 5%) if you submit a valid medical certificate within 7 days.',
    confidence: 'high' as const,
  },
  low_confidence: {
    riskTier: 'yellow' as const,
    clauseId: 'c3',
    reasoning: 'The document contains conflicting requirements about examination eligibility. Manual verification is recommended.',
    confidence: 'low' as const,
  },
}

export const mockExplanations: Record<string, Record<Language, string>> = {
  below_threshold: {
    en: 'Your attendance is currently 72%, which is below the required 75% threshold. Based on the regulation, you may not be eligible to write your exam unless you have documented medical exemption or successfully appeal for condonation. Consider reviewing the medical exemption clause (Section 5.1) and submitting supporting documentation if applicable.',
    kn: 'ನಿಮ್ಮ ಹಾಜರಿ ಪ್ರಸ್ತುತವಾಗಿ 72% ಆಗಿದೆ, ಇದು ಅಗತ್ಯವಿರುವ 75% ಮೇಲಿನ ಸೀಮೆಗಿಂತ ಕಡಿಮೆಯಾಗಿದೆ. ನಿಯಮದ ಪ್ರಕಾರ, ನೀವು ದಾಖಲೆಯ ಆಧಾರದ ಮೇಲೆ ವೈದ್ಯಕೀಯ ವಿನಾಯಿತಿ ಅಥವಾ ಕ್ಷಮಾ ಮೆಚ್ಚುಬೆಳೆ ಇಲ್ಲದೆ ನಿಮ್ಮ ಪರೀಕ್ಷೆ ಬರೆಯಲು ಅರ್ಹವಾಗಿರಬಾರದು. ವೈದ್ಯಕೀಯ ವಿನಾಯಿತಿ ನಿಯಮ (ವಿಭಾಗ 5.1) ಮರುಪರಿಶೀಲನೆ ಮಾಡುವುದನ್ನು ಪರಿಗಣಿಸಿ ಮತ್ತು ಅನ್ವಯವಾಗಿದ್ದರೆ ಬೆಂಬಲಿಸುವ ದಾಖಲೆಗಳನ್ನು ಸಲ್ಲಿಸಿ.',
  },
  above_threshold: {
    en: 'Your attendance of 85% exceeds the required 75% threshold. You are eligible to write your exam. No further action is needed regarding attendance requirements.',
    kn: 'ನಿಮ್ಮ ಹಾಜರಿ 85% ರಿಂದ ಅಗತ್ಯವಿರುವ 75% ಮೇಲಿನ ಸೀಮೆಯನ್ನು ಮೀರಿಸುತ್ತದೆ. ನೀವು ನಿಮ್ಮ ಪರೀಕ್ಷೆ ಬರೆಯಲು ಅರ್ಹವಾಗಿದ್ದೀರಿ. ಹಾಜರಿ ಅವಶ್ಯಕತೆಗಳಿಗೆ ಸಂಬಂಧಿಸಿದಂತೆ ಯಾವುದೇ ಹೆಚ್ಚಿನ ಕ್ರಿಯೆಯನ್ನು ಕೈಗೊಳ್ಳಬೇಕಾಗಿಲ್ಲ.',
  },
  below_with_medical: {
    en: 'Your attendance is 72%, which is below the threshold. However, since you mentioned a medical reason, you may be eligible for condonation of up to 5% (Section 5.2). You must submit a medical certificate from a recognized hospital within 7 days of returning to campus. If approved, your adjusted attendance would be considered against the policy.',
    kn: 'ನಿಮ್ಮ ಹಾಜರಿ 72% ಆಗಿದೆ, ಇದು ಮೇಲಿನ ಸೀಮೆಗಿಂತ ಕಡಿಮೆಯಾಗಿದೆ. ಆದಾಗ್ಯೂ, ನೀವು ವೈದ್ಯಕೀಯ ಕಾರಣವನ್ನು ಉಲ್ಲೇಖ ಮಾಡಿರುವುದರಿಂದ, ನೀವು 5% ವರೆಗಿನ ಕ್ಷಮಾಮೆಚ್ಚುಬೆಳೆಗೆ ಅರ್ಹವಾಗಿರಬಹುದು (ವಿಭಾಗ 5.2). ನೀವು ಮುಖ್ಯ ಆಸ್ಪತ್ರೆಯಿಂದ ವೈದ್ಯಕೀಯ ಪ್ರಮಾಣಪತ್ರವನ್ನು ಕ್ಯಾಂಪಸ್‌ಗೆ ಹಿಂತಿರುಗುವ ಎಂಟು ದಿನಗಳ ಳಿತರೆ ಸಲ್ಲಿಸಬೇಕು. ಅನುಮೋದಿಸಲಾದರೆ, ನಿಮ್ಮ ಸರಿಹೊಂದಿಸಿದ ಹಾಜರಿಯನ್ನು ನೀತಿಗೆ ವಿರುದ್ಧವಾಗಿ ಪರಿಗಣಿಸಲಾಗುತ್ತದೆ.',
  },
}

/**
 * Simulates backend processing with realistic delays.
 * In production, this would be replaced with real API calls.
 */
export async function simulateProcessing(
  documentId: string,
  situation: string,
  language: Language = 'en'
): Promise<ProcessedDocument> {
  // Simulate network delay and processing stages
  await new Promise((resolve) => setTimeout(resolve, 2000)) // reading
  await new Promise((resolve) => setTimeout(resolve, 3000)) // extracting
  await new Promise((resolve) => setTimeout(resolve, 2500)) // matching
  await new Promise((resolve) => setTimeout(resolve, 2000)) // classifying
  await new Promise((resolve) => setTimeout(resolve, 1500)) // explaining

  // Determine which mock result to use based on situation
  let resultKey = 'below_threshold'
  if (situation.toLowerCase().includes('85')) {
    resultKey = 'above_threshold'
  } else if (situation.toLowerCase().includes('medical')) {
    resultKey = 'below_with_medical'
  }

  const riskResult = mockRiskResults[resultKey as keyof typeof mockRiskResults] || mockRiskResults.below_threshold

  const explanations: Record<Language, string> = {}
  explanations[language] = mockExplanations[resultKey][language] || mockExplanations.below_threshold[language]

  return {
    documentId,
    docType: 'academic_regulation',
    status: 'complete',
    extractedClauses: mockClauses,
    riskResult,
    explanations,
    createdAt: new Date().toISOString(),
  }
}
