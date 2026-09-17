# Scripts

- `smoke_test.py` - Quick check that the project loads and runs on the current machine. Imports every module and calls each C++ kernel against a small synthetic image. Pass `--networks` to also load each trained SavedModel. Run from the repository root.
- `repro_two_point_crash.py` - Regression test for the add segment segfault. Connects far apart background points, which gives the search nothing to follow and previously walked crawlers off the image. Exits non-zero if the kernel crashes.
- `rsml_to_mask.py` - Rasterizes an RSML file into a binary root mask. RSML is the polyline format RootNav, SmartRoot, and the GigaDB datasets use, so this is needed to compare those labels against a segmentation mask.
- `validate_length.py` - Checks the length estimators against shapes with analytically known lengths (line, diagonal, shallow line, arc, sine). Writes a figure showing each shape with its true and measured length. Exits non-zero if the spline estimator is off by more than 2 percent.
- `show_topology.py` - Draws the segment graph over a root image, with each segment in its own colour, junctions in red, and tips in cyan. Writes a full view and a 2x crop of the densest region. Use it to check the topology by eye before any heuristic interprets it.
