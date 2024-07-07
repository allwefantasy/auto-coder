export interface PollResult {
    text: string;
    status: 'running' | 'completed' | 'failed';
}

export interface StreamValue {
    value: string[];
}

export interface DefaultValue {
    value: string;
}

export interface ResponseData {
    result: StreamValue | DefaultValue;
    status: 'running' | 'completed' | 'failed';
}