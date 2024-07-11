def example_function():
    print("This is a test message")
    print("Another test message", file=sys.stderr)

# 使用示例
log_capture = LogCapture(log_file="output.log")

with log_capture.capture() as log_queue:
    example_function()

# 获取捕获的日志
captured_logs = log_capture.get_captured_logs()
print("Captured logs:", captured_logs)

# 如果需要，可以从队列中直接读取日志
while not log_queue.empty():
    print("Log from queue:", log_queue.get())