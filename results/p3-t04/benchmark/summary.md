# V0 benchmark

GPU: Tesla T4, 580.82.07. CPU: Intel(R) Xeon(R) CPU @ 2.00GHz. Time (UTC): 2026-10-20T10:05:02+00:00. Runs per configuration: 5, after one untimed warm-up.

## Average (ms, share of Total_ms)

| Site | Size | S1 | S2 | S3 | S4 | S5 | S6 | Total | Hot stage | p | 1/(1-p) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| site1 | small | 30.551 (2.8%) | 197.815 (17.9%) | 42.958 (3.9%) | 682.458 (61.6%) | 32.778 (3.0%) | 121.577 (11.0%) | 1108.137 | S4 | 0.616 | 2.603 |
| site1 | medium | 69.432 (4.2%) | 516.806 (30.9%) | 88.998 (5.3%) | 677.294 (40.5%) | 22.171 (1.3%) | 296.588 (17.7%) | 1671.290 | S4 | 0.405 | 1.681 |
| site1 | large | 305.414 (6.8%) | 1790.494 (39.9%) | 352.431 (7.9%) | 671.092 (15.0%) | 92.164 (2.1%) | 1273.371 (28.4%) | 4484.967 | S2 | 0.399 | 1.665 |
| site2 | small | 30.111 (2.7%) | 144.385 (13.0%) | 42.566 (3.8%) | 673.140 (60.4%) | 27.198 (2.4%) | 196.378 (17.6%) | 1113.778 | S4 | 0.604 | 2.528 |
| site2 | medium | 69.875 (4.3%) | 316.481 (19.6%) | 87.897 (5.4%) | 668.359 (41.4%) | 18.311 (1.1%) | 454.659 (28.1%) | 1615.582 | S4 | 0.414 | 1.706 |
| site2 | large | 278.694 (6.1%) | 1192.493 (26.2%) | 338.089 (7.4%) | 664.157 (14.6%) | 87.745 (1.9%) | 1983.117 (43.6%) | 4544.297 | S6 | 0.436 | 1.774 |
| site3 | small | 29.868 (4.0%) | 131.086 (17.6%) | 39.919 (5.4%) | 346.234 (46.4%) | 45.345 (6.1%) | 152.952 (20.5%) | 745.404 | S4 | 0.464 | 1.867 |
| site3 | medium | 67.999 (5.2%) | 274.675 (20.9%) | 85.691 (6.5%) | 499.615 (38.0%) | 53.235 (4.1%) | 332.342 (25.3%) | 1313.558 | S4 | 0.380 | 1.614 |
| site3 | large | 280.722 (8.0%) | 1046.092 (29.9%) | 333.408 (9.5%) | 430.840 (12.3%) | 89.835 (2.6%) | 1315.008 (37.6%) | 3495.906 | S6 | 0.376 | 1.603 |

## Minimum (ms)

| Site | Size | S1 | S2 | S3 | S4 | S5 | S6 | Total |
|---|---|---|---|---|---|---|---|---|
| site1 | small | 29.866 | 192.739 | 41.796 | 669.621 | 31.922 | 118.576 | 1099.393 |
| site1 | medium | 68.965 | 451.680 | 86.427 | 668.214 | 21.020 | 280.335 | 1586.209 |
| site1 | large | 282.171 | 1756.945 | 327.321 | 665.294 | 89.190 | 1181.695 | 4335.095 |
| site2 | small | 29.793 | 142.045 | 41.216 | 664.405 | 26.823 | 192.472 | 1101.307 |
| site2 | medium | 68.817 | 310.386 | 84.464 | 659.701 | 17.904 | 446.941 | 1595.738 |
| site2 | large | 274.149 | 1178.036 | 324.645 | 657.337 | 86.721 | 1947.973 | 4472.549 |
| site3 | small | 29.222 | 124.013 | 39.294 | 341.124 | 43.260 | 147.391 | 730.632 |
| site3 | medium | 67.011 | 265.981 | 82.018 | 492.315 | 52.162 | 325.194 | 1298.452 |
| site3 | large | 272.403 | 1024.405 | 323.780 | 424.482 | 83.039 | 1298.785 | 3454.652 |

## Config

| Site | Size | Version and seed | Config |
|---|---|---|---|
| site1 | small | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=2 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site1 | medium | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=3 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site1 | large | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=6 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site2 | small | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=2 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site2 | medium | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=3 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site2 | large | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=6 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site3 | small | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=2 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site3 | medium | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=3 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
| site3 | large | [debug] version=0 seed=16 runs=5 | [debug] config: gaussian_sigma=1 gaussian_radius=3 fast_threshold=0.0500000007 max_keypoints=2000 match_ratio_threshold=0.800000012 match_cross_check=0 ransac_iters=2000 ransac_threshold=6 seed=16 homography_epsilon=9.99999997e-07 max_canvas_pixels=100000000 |
