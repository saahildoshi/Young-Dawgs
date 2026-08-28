from pathlib import Path

def setup_iteration_files(num_iterations: int = 4) -> None:
    script_dir = Path(__file__).resolve().parent

    file_types = [
        ("iteration", "py"),
        ("prompt", "txt"),
        ("response", "txt")
    ]
    
    for i in range(num_iterations):
        for prefix, ext in file_types:
            filename = f"{prefix}_{i}.{ext}"
            file_path = script_dir / filename
            file_path.touch(exist_ok=True)
            print(f"Created: {file_path.name} in {script_dir}")

if __name__ == "__main__":
    setup_iteration_files()
