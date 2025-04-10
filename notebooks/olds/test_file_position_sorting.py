from typing import Dict, List

class Result:
    def __init__(self, file_positions: Dict[str, int]):
        self.file_positions = file_positions

def test_file_position_sorting():
    # Test case 1: Simple case with 3 results
    results = [
        Result({"file1": 0, "file2": 1, "file3": 2}),
        Result({"file4": 0, "file5": 1}),
        Result({"file6": 0, "file7": 1, "file8": 2, "file9": 3})
    ]

    # Calculate max_position
    max_position = max([max(pos.values()) for pos in [result.file_positions for result in results if result.file_positions]] + [0])

    # Create position map
    position_map = {}
    for result in results:
        if result.file_positions:
            for file_path, position in result.file_positions.items():
                if position not in position_map:
                    position_map[position] = []
                position_map[position].append(file_path)

    # Reorder file paths
    new_file_positions = {}
    current_index = 0
    for position in range(max_position + 1):
        if position in position_map:
            for file_path in position_map[position]:
                new_file_positions[file_path] = current_index
                current_index += 1

    # Expected output
    expected_output = {
        "file1": 0, "file4": 1, "file6": 2,
        "file2": 3, "file5": 4, "file7": 5,
        "file3": 6, "file8": 7,
        "file9": 8
    }

    # Verify the result
    assert new_file_positions == expected_output, f"Expected {expected_output}, got {new_file_positions}"

    print("Test case 1 passed!")

    # Test case 2: Empty results
    results = []
    max_position = max([max(pos.values()) for pos in [result.file_positions for result in results if result.file_positions]] + [0])
    position_map = {}
    new_file_positions = {}
    current_index = 0
    for position in range(max_position + 1):
        if position in position_map:
            for file_path in position_map[position]:
                new_file_positions[file_path] = current_index
                current_index += 1

    assert new_file_positions == {}, "Expected empty dict for empty results"
    print("Test case 2 passed!")

    # Test case 3: Single result with single position
    results = [Result({"file1": 0})]
    max_position = max([max(pos.values()) for pos in [result.file_positions for result in results if result.file_positions]] + [0])
    position_map = {}
    new_file_positions = {}
    current_index = 0
    for position in range(max_position + 1):
        if position in position_map:
            for file_path in position_map[position]:
                new_file_positions[file_path] = current_index
                current_index += 1

    expected_output = {"file1": 0}
    assert new_file_positions == expected_output, f"Expected {expected_output}, got {new_file_positions}"
    print("Test case 3 passed!")

if __name__ == "__main__":
    test_file_position_sorting()
