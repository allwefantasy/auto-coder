import {PollResult,StreamValue,DefaultValue,ResponseData} from './types'

export async function checkBackendReady(port: number, setIsBackendReady: (isReady: boolean) => void): Promise<void> {
    const checkReady = async () => {
        try {
            const response = await fetch(`http://127.0.0.1:${port}/list_files`);
            if (response.status === 200) {
                setIsBackendReady(true);
            } else {
                setTimeout(checkReady, 1000); // Retry after 1 second
            }
        } catch (error) {
            console.error('Backend not ready:', error);
            setTimeout(checkReady, 1000); // Retry after 1 second
        }
    };

    await checkReady();
}

export async function fetchConfigOptions(port: number|null): Promise<string[]> {
    try {
        const response = await fetch(`http://127.0.0.1:${port}/extra/conf/list`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.options;
    } catch (error) {
        console.error('Error fetching config options:', error);
        return [];
    }
}

export async function fetchFileList(port: number|null): Promise<string[]> {
    try {
        const response = await fetch(`http://127.0.0.1:${port}/list_files`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.files;
    } catch (error) {
        console.error('Error fetching file list:', error);
        return [];
    }
}

export async function pollResult(port: number|null, requestId: string, onUpdate: (text: string) => void): Promise<PollResult> {
    let result = '';
    let status: 'running' | 'completed' | 'failed' = 'running';

    while (status === 'running') {
        try {
            const response = await fetch(`http://127.0.0.1:${port}/extra/result/${requestId}`);
            if (!response.ok) {
                status = 'completed';
                break;
            }
            
            const data: ResponseData = await response.json();
            status = data.status;            

            if ('value' in data.result && Array.isArray(data.result.value)) {
                const newText = data.result.value.join('');
                if (newText !== result) {
                    result = newText;
                    onUpdate(result);
                }
            } else if ('value' in data.result && typeof data.result.value === 'string') {
                if (data.result.value !== result) {
                    result = data.result.value;
                    onUpdate(result);
                }
            }

            if (status === 'completed') {
                break;
            }

            if (status === 'running') {
                await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒后再次轮询
            }
        } catch (error) {
            console.error('Error polling result:', error);
            status = 'failed';
        }
    }

    return { text: result, status };
}