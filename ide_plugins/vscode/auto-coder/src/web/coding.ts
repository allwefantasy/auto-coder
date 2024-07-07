import { pollResult } from './utils';

interface CodingEvent {
    event_type: string;
    data: string;
}

export async function handleCoding(query: string, port: number | null, updateMessages: (text: string, sender: 'user' | 'bot') => void) {
    if (!port) {
        updateMessages("Error: Server port is not set.", 'bot');
        return;
    }

    try {
        // Send initial coding request
        const response = await fetch(`http://127.0.0.1:${port}/coding`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const requestId = data.request_id;

        // Start polling for events
        while (true) {
            const eventResponse = await fetch(`http://127.0.0.1:${port}/extra/event/get`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ request_id: requestId }),
            });

            if (!eventResponse.ok) {
                if (eventResponse.status === 404) {
                    // No more events, exit the loop
                    break;
                }
                throw new Error(`HTTP error! status: ${eventResponse.status}`);
            }

            const eventData: CodingEvent = await eventResponse.json();

            switch (eventData.event_type) {
                case 'code_start':
                    updateMessages("AI is ready to start coding. Do you want to proceed? (y/n)", 'bot');
                    const userResponse = await getUserResponse();
                    await sendEventResponse(port, requestId, eventData, userResponse);
                    if (userResponse.toLowerCase() !== 'y') {
                        updateMessages("Coding process cancelled by user.", 'bot');
                        return;
                    }
                    break;
                case 'code_merge':
                    updateMessages("AI has completed coding. Merging changes...", 'bot');
                    await sendEventResponse(port, requestId, eventData, 'proceed');
                    break;
                // Add more cases for other event types as needed
                default:
                    updateMessages(`Received event: ${eventData.event_type}`, 'bot');
                    await sendEventResponse(port, requestId, eventData, 'acknowledged');
            }
        }

        // After all events are processed, poll for the final result
        const finalResult = await pollResult(port, requestId, (text) => {
            updateMessages(text, 'bot');
        });

        if (finalResult.status === 'completed') {
            updateMessages("Coding process completed successfully.", 'bot');
        } else {
            updateMessages("Coding process failed or was interrupted.", 'bot');
        }

    } catch (error) {
        console.error('Error in coding process:', error);
        updateMessages(`An error occurred during the coding process: ${error}`, 'bot');
    }
}

async function getUserResponse(): Promise<string> {
    // In a real implementation, this would wait for user input
    // For now, we'll simulate a "yes" response after a short delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    return 'y';
}

async function sendEventResponse(port: number, requestId: string, event: CodingEvent, response: string) {
    const responseBody = {
        request_id: requestId,
        event: event,
        response: response,
    };

    const responseResult = await fetch(`http://127.0.0.1:${port}/extra/event/response`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(responseBody),
    });

    if (!responseResult.ok) {
        throw new Error(`HTTP error in event response! status: ${responseResult.status}`);
    }
}