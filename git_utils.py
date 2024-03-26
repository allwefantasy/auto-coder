import os

class GitUtils:
    def __init__(self):
        pass

    def echo(self, message):
        """
        Prints the provided message to the console.

        Args:
            message (str): The message to be displayed.
        """
        print(message)

# Example usage:
if __name__ == "__main__":
    git_helper = GitUtils()
    git_helper.echo("Hello from git_utils.py!")