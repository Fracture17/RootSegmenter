# Scripts

- `smoke_test.py` - Quick check that the project loads and runs on the current machine. Imports every module and calls each C++ kernel against a small synthetic image. Pass `--networks` to also load each trained SavedModel. Run from the repository root.
- `repro_two_point_crash.py` - Regression test for the add segment segfault. Connects far apart background points, which gives the search nothing to follow and previously walked crawlers off the image. Exits non-zero if the kernel crashes.
- `rsml_to_mask.py` - Rasterizes an RSML file into a binary root mask. RSML is the polyline format RootNav, SmartRoot, and the GigaDB datasets use, so this is needed to compare those labels against a segmentation mask.
