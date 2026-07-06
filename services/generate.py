"""Thin shim — delegates to the installed laser-init package.

Run directly:
    python3 services/generate.py NGA 1 2020 2020 --emit-scripts

Or use the installed entry point:
    laser-generate NGA 1 2020 2020 --emit-scripts
"""

from laser.init.generate import main

if __name__ == "__main__":
    main()
