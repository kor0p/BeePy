import sys
IS_DEV = not (len(sys.argv) > 2 and sys.argv[2].startswith('0.0.0.0'))

