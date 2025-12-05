import { GoogleGenAI, Type } from "@google/genai";
import { RankedCandidate } from "../types";

// Safely retrieve API Key to prevent crashes in environments where process is undefined
const getApiKey = (): string => {
  try {
    return process.env.API_KEY || '';
  } catch (e) {
    console.warn("process.env.API_KEY is not accessible.");
    return '';
  }
};

const apiKey = getApiKey();

// Initialize the Gemini AI client
const ai = new GoogleGenAI({ apiKey });

export const rankCandidates = async (
  jobDescription: string | { mimeType: string; data: string },
  resumes: { name: string; content: string }[]
): Promise<RankedCandidate[]> => {
  if (!apiKey) {
    throw new Error("API Key is missing. Please check your environment variables.");
  }

  const model = "gemini-2.5-flash";

  // Construct the prompt for resumes
  const resumesText = resumes
    .map((r, index) => `Resume ${index + 1} (Name: ${r.name}):\n${r.content}\n---`)
    .join("\n");

  let systemPrompt = `
    You are an expert HR recruiter and talent acquisition specialist.
    
    Task: Analyze each resume against the job description. Assign a relevance score from 0 to 100 based on skills, experience, and fit.
    Provide a brief summary, a list of pros, and a list of cons for each candidate.
    
    Strictly follow the JSON response schema.
  `;

  const parts: any[] = [];

  // Add Job Description (Text or File)
  if (typeof jobDescription === 'string') {
    systemPrompt += `\n\nJOB DESCRIPTION:\n${jobDescription}`;
  } else {
    systemPrompt += `\n\nJOB DESCRIPTION: (Provided as attachment)`;
    parts.push({
        inlineData: {
            mimeType: jobDescription.mimeType,
            data: jobDescription.data
        }
    });
  }

  systemPrompt += `\n\nCANDIDATE RESUMES:\n${resumesText}`;

  // Add the text prompt as a part
  parts.push({ text: systemPrompt });

  try {
    const response = await ai.models.generateContent({
      model,
      contents: { parts },
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              name: { type: Type.STRING, description: "Candidate's full name derived from the resume or filename" },
              score: { type: Type.NUMBER, description: "Match score from 0 to 100" },
              summary: { type: Type.STRING, description: "1-2 sentence summary of the candidate's fit" },
              pros: { 
                type: Type.ARRAY, 
                items: { type: Type.STRING },
                description: "Key strengths relevant to the JD" 
              },
              cons: { 
                type: Type.ARRAY, 
                items: { type: Type.STRING },
                description: "Key weaknesses or missing requirements" 
              }
            },
            required: ["name", "score", "summary", "pros", "cons"],
          },
        },
      },
    });

    const jsonText = response.text || "[]";
    const candidates = JSON.parse(jsonText) as RankedCandidate[];

    // Sort by score descending
    return candidates.sort((a, b) => b.score - a.score);

  } catch (error) {
    console.error("Error ranking candidates:", error);
    throw new Error("Failed to rank candidates. Please try again.");
  }
};