
def test():
    try:
        print(x)  # 这里会抛出 UnboundLocalError
    except UnboundLocalError as e:
        print(f"捕获到 UnboundLocalError: {e}")
    except Exception as e:
        print(f"捕获到其他异常: {e}")


test()
