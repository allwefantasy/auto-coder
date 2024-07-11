export const handleIndexBuild = async (
    autoCoderServerPort: number | null, 
    requestId: string, 
    addLogMessage: (text: string) => void
) => {
    if (!autoCoderServerPort) {
        console.error('Auto-Coder server port is not set');
        return;
    }

    const pollInterval = 1000; // 1 second
    const maxAttempts = 60*10; // Maximum number of attempts (1 minute)
    let attempts = 0;

    const pollLogs = async () => {
        try {
            const response = await fetch(`http://127.0.0.1:${autoCoderServerPort}/extra/logs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ request_id: requestId }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.logs === null) {
                addLogMessage('Indexing completed.');
                return;
            }

            if (Array.isArray(data.logs)) {
                data.logs.forEach((log: string) => {
                    addLogMessage(log);
                });
            }

            attempts++;

            if (attempts < maxAttempts) {
                setTimeout(pollLogs, pollInterval);
            } else {
                addLogMessage('Indexing timed out.');
            }
        } catch (error) {
            console.error('Error polling logs:', error);
            addLogMessage('Error occurred while indexing.');
        }
    };

    pollLogs();
};