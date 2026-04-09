import sys
import jishaku
print(f"Python: {sys.version}")
print(f"Jishaku: {jishaku.__version__}")
try:
    from jishaku.cog import Jishaku
    print("Successfully imported Jishaku cog")
except Exception as e:
    import traceback
    traceback.print_exc()
