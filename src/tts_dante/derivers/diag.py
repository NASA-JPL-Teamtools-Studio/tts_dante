from tts_dtat import commonchartfuncs as common

# Your config
my_config = {
    "mode": "lines+markers",
    "symbol": "x",
    "size": 15,
    "marker_line_width": 0.1,  # <--- The value we want
    "color": "black",
    "line": {
        "width": 2,            # <--- The fallback we want to avoid
        "color": "black",
        "shape": "hv"
    } 
}

# Ask the library what it calculates
result = common.get_plotly_marker_values(my_config)

print(f"Input Marker Width: {my_config.get('marker_line_width')}")
print(f"Calculated Marker Width: {result['line']['width']}")

if result['line']['width'] == 0.1:
    print("SUCCESS: Library logic is correct. Plotly is receiving 0.1.")
elif result['line']['width'] == 2:
    print("FAILURE: Library is falling back to trace line width.")
else:
    print(f"FAILURE: Library is using default {result['line']['width']}")