
import { RankedCandidate, DetailedAnalysis } from '../types';

export const API_BASE_URL = 'https://b8516a8724d9.ngrok-free.app';

export interface ReportResponse {
    summary_report: string;
    parsed_summary?: {
        table_of_contents: string;
        executive_ranking: string;
        deep_dive_analysis: string;
    };
    detailed_analysis?: DetailedAnalysis[];
    report_path: string;
    results?: string; // Fallback for legacy response
}

const getHeaders = () => {
    return {
        'ngrok-skip-browser-warning': 'true',
    };
};

export const getTotalResumes = async (): Promise<number> => {
    const response = await fetch(`${API_BASE_URL}/total-resumes/`, {
        headers: getHeaders(),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Failed to get total resumes: ${response.status} ${response.statusText}`);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
        const text = await response.text();
        // Truncate text if it's too long (likely HTML) to avoid clogging console
        const truncatedText = text.length > 150 ? text.substring(0, 150) + "..." : text;
        throw new Error(`Expected JSON response but got ${contentType}. Response body: ${truncatedText}`);
    }

    const data = await response.json();
    return data.total;
};

export const uploadResumes = async (files: File[]): Promise<any> => {
    const formData = new FormData();
    files.forEach((file) => {
        formData.append('files', file);
    });

    // Fetch automatically sets Content-Type for FormData, so we only merge custom headers
    const response = await fetch(`${API_BASE_URL}/upload-cv/`, {
        method: 'POST',
        headers: getHeaders(),
        body: formData,
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Failed to upload resumes: ${text}`);
    }

    return response.json();
};

export const getScores = async (jdFile: File | null, jdText: string | null, n: number = 5): Promise<Record<string, any>> => {
    const formData = new FormData();

    if (jdFile) {
        formData.append('file', jdFile);
    } else if (jdText) {
        // If we have text but no file, we need to create a file from text because /scores/ expects a file
        const blob = new Blob([jdText], { type: 'text/plain' });
        formData.append('file', blob, 'job_description.txt');
    } else {
        throw new Error("No JD provided");
    }

    const response = await fetch(`${API_BASE_URL}/scores/?n=${n}`, {
        method: 'POST',
        headers: getHeaders(),
        body: formData,
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Failed to get scores: ${text}`);
    }

    return response.json();
};

export const generateReport = async (jdFile: File | null, jdText: string | null, n: number = 5): Promise<ReportResponse> => {
    const formData = new FormData();

    // The /report/ endpoint accepts an optional file. 
    if (jdFile) {
        formData.append('file', jdFile);
    } else if (jdText) {
        const blob = new Blob([jdText], { type: 'text/plain' });
        formData.append('file', blob, 'job_description.txt');
    }

    const response = await fetch(`${API_BASE_URL}/report/?n=${n}`, {
        method: 'POST',
        headers: getHeaders(),
        body: formData,
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Failed to generate report: ${text}`);
    }

    return response.json();
};
