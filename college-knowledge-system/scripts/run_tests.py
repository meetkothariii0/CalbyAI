"""Run all test_*.py modules under tests/ by importing modules directly.
This avoids unittest discovery issues on some Windows environments.
"""
import os
import sys
import importlib
import unittest

ROOT = Path = os.path.dirname

TEST_DIR = os.path.join(os.path.dirname(__file__), '..', 'tests')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def find_test_modules():
    mods = []
    for fn in os.listdir(TEST_DIR):
        if fn.startswith('test_') and fn.endswith('.py'):
            mod = 'tests.' + fn[:-3]
            mods.append(mod)
    return mods

def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for modname in find_test_modules():
        try:
            m = importlib.import_module(modname)
            suite.addTests(loader.loadTestsFromModule(m))
        except Exception as e:
            print(f"Failed to import {modname}: {e}")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    main()
