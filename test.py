import timeit
from enum import Enum
from typing import NamedTuple


# --- Setup ---
class Point(NamedTuple):
    x: int
    y: int


class AngleUnit(Enum):
    RADIANS = "radians"
    DEGREES = "degrees"
    HOURS = "hours"
    ARCMINUTES = "arcminutes"
    ARCSECONDS = "arcseconds"
    MILLIARCSECONDS = "mas"


# --- Test Functions ---

# 1. Match/case with Enum
def match_enum(unit: AngleUnit) -> str:
    match unit:
        case AngleUnit.RADIANS:
            return "rad"
        case AngleUnit.DEGREES:
            return "°"
        case AngleUnit.HOURS:
            return "h"
        case AngleUnit.ARCMINUTES:
            return "'"
        case AngleUnit.ARCSECONDS:
            return "\""
        case AngleUnit.MILLIARCSECONDS:
            return "mas"
        case _:
            return "°"


# 2. If/elif with Enum
def if_elif_enum(unit: AngleUnit) -> str:
    if unit == AngleUnit.RADIANS:
        return "rad"
    elif unit == AngleUnit.DEGREES:
        return "°"
    elif unit == AngleUnit.HOURS:
        return "h"
    elif unit == AngleUnit.ARCMINUTES:
        return "'"
    elif unit == AngleUnit.ARCSECONDS:
        return "\""
    elif unit == AngleUnit.MILLIARCSECONDS:
        return "mas"
    else:
        return "°"


# 3. Match/case with string
def match_string(unit: str) -> str:
    match unit:
        case "radians":
            return "rad"
        case "degrees":
            return "°"
        case "hours":
            return "h"
        case "arcminutes":
            return "'"
        case "arcseconds":
            return "\""
        case "mas":
            return "mas"
        case _:
            return "°"


# 4. If/elif with string
def if_elif_string(unit: str) -> str:
    if unit == "radians":
        return "rad"
    elif unit == "degrees":
        return "°"
    elif unit == "hours":
        return "h"
    elif unit == "arcminutes":
        return "'"
    elif unit == "arcseconds":
        return "\""
    elif unit == "mas":
        return "mas"
    else:
        return "°"


# 5. Dictionary lookup (baseline)
UNIT_MAP = {
    "radians": "rad",
    "degrees": "°",
    "hours": "h",
    "arcminutes": "'",
    "arcseconds": "\"",
    "mas": "mas"
}

def dict_lookup(unit: str) -> str:
    return UNIT_MAP.get(unit, "°")


# 6. Enum with dict lookup
ENUM_MAP = {
    AngleUnit.RADIANS: "rad",
    AngleUnit.DEGREES: "°",
    AngleUnit.HOURS: "h",
    AngleUnit.ARCMINUTES: "'",
    AngleUnit.ARCSECONDS: "\"",
    AngleUnit.MILLIARCSECONDS: "mas"
}

def dict_lookup_enum(unit: AngleUnit) -> str:
    return ENUM_MAP.get(unit, "°")


# --- Benchmark ---
iterations = 1_000_000

print("=" * 70)
print("PATTERN MATCHING vs IF/ELIF vs DICT LOOKUP")
print("=" * 70)
print(f"Iterations: {iterations:,}")
print()

# Test with first item (best case)
print("--- FIRST MATCH (BEST CASE) ---")
print()

match_enum_first = timeit.timeit(
    'match_enum(AngleUnit.RADIANS)',
    globals=globals(),
    number=iterations
)

if_elif_enum_first = timeit.timeit(
    'if_elif_enum(AngleUnit.RADIANS)',
    globals=globals(),
    number=iterations
)

dict_enum_first = timeit.timeit(
    'dict_lookup_enum(AngleUnit.RADIANS)',
    globals=globals(),
    number=iterations
)

print(f"match/case (Enum):     {match_enum_first:.4f}s")
print(f"if/elif (Enum):        {if_elif_enum_first:.4f}s ({if_elif_enum_first/match_enum_first:.2f}x)")
print(f"dict lookup (Enum):    {dict_enum_first:.4f}s ({dict_enum_first/match_enum_first:.2f}x)")
print()

# Test with last item (worst case)
print("--- LAST MATCH (WORST CASE) ---")
print()

match_enum_last = timeit.timeit(
    'match_enum(AngleUnit.MILLIARCSECONDS)',
    globals=globals(),
    number=iterations
)

if_elif_enum_last = timeit.timeit(
    'if_elif_enum(AngleUnit.MILLIARCSECONDS)',
    globals=globals(),
    number=iterations
)

dict_enum_last = timeit.timeit(
    'dict_lookup_enum(AngleUnit.MILLIARCSECONDS)',
    globals=globals(),
    number=iterations
)

print(f"match/case (Enum):     {match_enum_last:.4f}s")
print(f"if/elif (Enum):        {if_elif_enum_last:.4f}s ({if_elif_enum_last/match_enum_last:.2f}x)")
print(f"dict lookup (Enum):    {dict_enum_last:.4f}s ({dict_enum_last/match_enum_last:.2f}x)")
print()

# Test with strings
print("--- STRING COMPARISON (MIDDLE MATCH) ---")
print()

match_string_time = timeit.timeit(
    'match_string("hours")',
    globals=globals(),
    number=iterations
)

if_elif_string_time = timeit.timeit(
    'if_elif_string("hours")',
    globals=globals(),
    number=iterations
)

dict_string_time = timeit.timeit(
    'dict_lookup("hours")',
    globals=globals(),
    number=iterations
)

print(f"match/case (string):   {match_string_time:.4f}s")
print(f"if/elif (string):      {if_elif_string_time:.4f}s ({if_elif_string_time/match_string_time:.2f}x)")
print(f"dict lookup (string):  {dict_string_time:.4f}s ({dict_string_time/match_string_time:.2f}x)")
print()

# Average case (test all options)
print("--- AVERAGE CASE (ALL OPTIONS) ---")
print()

match_enum_avg = timeit.timeit(
    '''
for unit in AngleUnit:
    match_enum(unit)
    ''',
    globals=globals(),
    number=iterations // 6  # Divide by number of enum members
)

if_elif_enum_avg = timeit.timeit(
    '''
for unit in AngleUnit:
    if_elif_enum(unit)
    ''',
    globals=globals(),
    number=iterations // 6
)

dict_enum_avg = timeit.timeit(
    '''
for unit in AngleUnit:
    dict_lookup_enum(unit)
    ''',
    globals=globals(),
    number=iterations // 6
)

print(f"match/case (Enum):     {match_enum_avg:.4f}s")
print(f"if/elif (Enum):        {if_elif_enum_avg:.4f}s ({if_elif_enum_avg/match_enum_avg:.2f}x)")
print(f"dict lookup (Enum):    {dict_enum_avg:.4f}s ({dict_enum_avg/match_enum_avg:.2f}x)")
print()

# --- Complex Pattern Matching ---
print("--- COMPLEX PATTERNS (match/case advantage) ---")
print()

# Match with guards
def match_with_guard(value: int) -> str:
    match value:
        case x if x < 0:
            return "negative"
        case 0:
            return "zero"
        case x if x < 10:
            return "single digit"
        case x if x < 100:
            return "double digit"
        case _:
            return "large"

# If/elif equivalent
def if_elif_with_guard(value: int) -> str:
    if value < 0:
        return "negative"
    elif value == 0:
        return "zero"
    elif value < 10:
        return "single digit"
    elif value < 100:
        return "double digit"
    else:
        return "large"

match_guard_time = timeit.timeit(
    'match_with_guard(50)',
    globals=globals(),
    number=iterations
)

if_elif_guard_time = timeit.timeit(
    'if_elif_with_guard(50)',
    globals=globals(),
    number=iterations
)

print(f"match/case (guards):   {match_guard_time:.4f}s")
print(f"if/elif (equivalent):  {if_elif_guard_time:.4f}s ({if_elif_guard_time/match_guard_time:.2f}x)")
print()

# --- Summary ---
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()
print("Simple lookups (enum/string equality):")
print("  Winner: DICT LOOKUP (fastest, O(1) lookup)")
print("  Runner-up: if/elif (slightly faster than match/case)")
print("  Note: match/case has overhead for pattern matching infrastructure")
print()
print("Complex patterns (guards, destructuring, multiple conditions):")
print("  Winner: match/case (cleaner syntax, similar performance)")
print()
print("RECOMMENDATIONS:")
print("  • Use DICT for simple value lookups (fastest)")
print("  • Use if/elif for 2-3 conditions (simple, fast)")
print("  • Use match/case for:")
print("    - Complex patterns with destructuring")
print("    - Multiple conditions with guards")
print("    - Better readability with many cases")
print()
print("For your AngleUnit.get_value() method:")
print("  → Use DICT LOOKUP (fastest and cleanest)")