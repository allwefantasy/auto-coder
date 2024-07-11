import { get } from "http";

interface CodingEvent {
    event_type: string;
    data: string;
}

export async function handleCoding(query: string, port: number | null,
    updateMessages: (text: string, sender: 'user' | 'bot') => void,
    setAwaitingUserResponse: (value: boolean) => void,
    getMessages: () => { text: string, sender: 'user' | 'bot' }[],
) {
    if (!port) {
        updateMessages("Error: Server port is not set.", 'bot');
        return;
    }

    console.log(`handleCoding called, messages: ${getMessages().length}`);

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

            console.log('Received event:', eventData);

            if (!eventData) {
                await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for 1s before polling again
                continue;
            }

            if (eventData.event_type === 'code_end') {                
                await sendEventResponse(port, requestId, eventData, 'proceed');
                setAwaitingUserResponse(false);
                updateMessages(`coding finished`, 'bot');
                break;
            }
            if (eventData.event_type === 'code_start') {
                await sendEventResponse(port, requestId, eventData, 'proceed');
                updateMessages(`start coding....`, 'bot');
            }

            if (eventData.event_type === 'code_merge_result') {
                await sendEventResponse(port, requestId, eventData, 'proceed');                  
                const blocks = JSON.parse(eventData.data);                
                let s = "The following files have been modified:\n";
                for (const block of blocks) {
                    s += `File: ${block.file_path}\n`;                    
                }
                updateMessages(s, 'bot');                
            }

            // if (eventData.event_type === 'code_merge_confirm') {
            //     updateMessages(`${eventData.data}`, 'bot');
            //     const userResponse = await getUserResponse(updateMessages, setAwaitingUserResponse, getMessages);
            //     await sendEventResponse(port, requestId, eventData, userResponse);
            //     if (userResponse.toLowerCase() !== 'y') {
            //         updateMessages("Coding merging cancelled by user.", 'bot');
            //     }
            // }
        }
    } catch (error) {
        console.error('Error in coding process:', error);
        updateMessages(`An error occurred during the coding process: ${error}`, 'bot');
    }
}

async function getUserResponse(updateMessages: (text: string, sender: 'user' | 'bot') => void,
    setAwaitingUserResponse: (value: boolean) => void,
    getMessages: () => { text: string, sender: 'user' | 'bot' }[],): Promise<string> {
    setAwaitingUserResponse(true);

    const messages = getMessages();
    const initialMessageCount = messages.length;
    while (true) {
        await new Promise(resolve => setTimeout(resolve, 1000));        
        if (getMessages().length > initialMessageCount) {
            const lastMessage = getMessages()[getMessages().length - 1];
            if (lastMessage.sender === 'user') {
                setAwaitingUserResponse(false);
                const v = lastMessage.text;
                console.log(`getUserResponse: ${v} ${lastMessage.sender}`);
                return v;
            }

        }
    }
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