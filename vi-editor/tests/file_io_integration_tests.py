#!/usr/bin/env python3
"""File I/O integration tests - test actual file read/write operations."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_test_framework import ViSimulator


def test_file_operations():
    """Test complete file editing workflows."""
    print("FILE I/O INTEGRATION TESTS")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        
        # Test 1: Create and save new file
        print("Test 1: Create and save new file... ", end="")
        test_file = os.path.join(tmpdir, "test1.txt")
        sim = ViSimulator()
        sim.send_keys("iHello World<ESC>")
        sim.save_to_file(test_file)
        
        with open(test_file) as f:
            content = f.read()
        
        if content == "Hello World":
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL - Got: {repr(content)}")
            failed += 1
        
        # Test 2: Load file, edit, and save
        print("Test 2: Load, edit, and save file... ", end="")
        test_file2 = os.path.join(tmpdir, "test2.txt")
        with open(test_file2, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3")
        
        sim2 = ViSimulator()
        sim2.load_from_file(test_file2)
        sim2.send_keys("jciModified<ESC>")  # Down, change line
        sim2.save_to_file(test_file2)
        
        with open(test_file2) as f:
            content = f.read()
        
        expected = "Line 1\nModified\nLine 3"
        if content == expected:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL")
            print(f"  Expected: {repr(expected)}")
            print(f"  Got: {repr(content)}")
            failed += 1
        
        # Test 3: Delete lines and save
        print("Test 3: Delete lines and save... ", end="")
        test_file3 = os.path.join(tmpdir, "test3.txt")
        with open(test_file3, 'w') as f:
            f.write("Keep\nDelete1\nDelete2\nKeep")
        
        sim3 = ViSimulator()
        sim3.load_from_file(test_file3)
        sim3.send_keys("j2dd")  # Down, delete 2 lines
        sim3.save_to_file(test_file3)
        
        with open(test_file3) as f:
            content = f.read()
        
        expected = "Keep\nKeep"
        if content == expected:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL - Got: {repr(content)}")
            failed += 1
        
        # Test 4: Insert at beginning
        print("Test 4: Insert at beginning of file... ", end="")
        test_file4 = os.path.join(tmpdir, "test4.txt")
        with open(test_file4, 'w') as f:
            f.write("Second line")
        
        sim4 = ViSimulator()
        sim4.load_from_file(test_file4)
        sim4.send_keys("OFirst line<ESC>")  # Open line above
        sim4.save_to_file(test_file4)
        
        with open(test_file4) as f:
            content = f.read()
        
        expected = "First line\nSecond line"
        if content == expected:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL - Got: {repr(content)}")
            failed += 1
        
        # Test 5: Append to end
        print("Test 5: Append to end of file... ", end="")
        test_file5 = os.path.join(tmpdir, "test5.txt")
        with open(test_file5, 'w') as f:
            f.write("Line 1")
        
        sim5 = ViSimulator()
        sim5.load_from_file(test_file5)
        sim5.send_keys("GoLine 2<ESC>")  # Go to end, open line
        sim5.save_to_file(test_file5)
        
        with open(test_file5) as f:
            content = f.read()
        
        expected = "Line 1\nLine 2"
        if content == expected:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL - Got: {repr(content)}")
            failed += 1
        
        # Test 6: Replace entire file content
        print("Test 6: Replace entire file... ", end="")
        test_file6 = os.path.join(tmpdir, "test6.txt")
        with open(test_file6, 'w') as f:
            f.write("Old content\nMore old stuff\nEven more")
        
        sim6 = ViSimulator()
        sim6.load_from_file(test_file6)
        sim6.send_keys("dGiNew content<ESC>")  # Delete all, insert new
        sim6.save_to_file(test_file6)
        
        with open(test_file6) as f:
            content = f.read()
        
        expected = "New content"
        if content == expected:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL - Got: {repr(content)}")
            failed += 1
        
        # Test 7: Complex multi-line edit
        print("Test 7: Complex multi-line editing... ", end="")
        test_file7 = os.path.join(tmpdir, "test7.txt")
        with open(test_file7, 'w') as f:
            f.write("AAA\nBBB\nCCC\nDDD")
        
        sim7 = ViSimulator()
        sim7.load_from_file(test_file7)
        # Delete BBB, change CCC to XXX, keep rest
        sim7.send_keys("jddjciXXX<ESC>")
        sim7.save_to_file(test_file7)
        
        with open(test_file7) as f:
            content = f.read()
        
        expected = "AAA\nXXX\nDDD"
        if content == expected:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL")
            print(f"  Expected: {repr(expected)}")
            print(f"  Got: {repr(content)}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"FILE I/O TESTS: {passed} passed, {failed} failed")
    total = passed + failed
    percentage = (passed / total * 100) if total > 0 else 0
    print(f"SUCCESS RATE: {percentage:.1f}%")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL FILE I/O TESTS PASSED!")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(test_file_operations())
