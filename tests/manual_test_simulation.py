import os
import shutil
import tempfile
from src import cleaner_core

def test_simulation():
    print("Setting up test environment...")
    test_dir = tempfile.mkdtemp()

    # Create simulated volume structure
    vol_path = os.path.join(test_dir, "MyUsbDrive")
    os.makedirs(vol_path)

    # Add files
    with open(os.path.join(vol_path, ".DS_Store"), "w") as f: f.write("junk")
    with open(os.path.join(vol_path, "file.txt"), "w") as f: f.write("keep")
    with open(os.path.join(vol_path, "._file.txt"), "w") as f: f.write("junk")

    print(f"Created simulated volume at {vol_path}")

    # 1. Scan
    print("Scanning...")
    files = list(cleaner_core.scan_for_junk(vol_path))
    print(f"Found {len(files)} junk files.")
    assert len(files) == 2

    # 2. Dry Run
    print("Running Dry Run...")
    s, f = cleaner_core.clean_files(files, dry_run=True, callback=lambda p, s: print(f"{s}: {p}"))
    assert os.path.exists(os.path.join(vol_path, ".DS_Store"))

    # 3. Clean
    print("Running Clean...")
    s, f = cleaner_core.clean_files(files, dry_run=False, callback=lambda p, s: print(f"{s}: {p}"))
    assert not os.path.exists(os.path.join(vol_path, ".DS_Store"))
    assert os.path.exists(os.path.join(vol_path, "file.txt"))

    print("Test Simulation Passed!")
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_simulation()
