#!/usr/bin/python

# mehr Spektrallinien gibs bei
# http://cdsweb.u-strasbg.fr/viz-bin/VizieR?-source=VI/16


neon = [
[ 352.956 , 90 ],
[ 354.962 , 60 ],
[ 587.213 , 35 ],
[ 589.179 , 35 ],
[ 589.911 , 35 ],
[ 591.830 , 70 ],
[ 595.920 , 100 ],
[ 598.706 , 75 ],
[ 598.891 , 35 ],
[ 600.036 , 70 ],
[ 602.726 , 170 ],
[ 615.628 , 170 ],
[ 618.672 , 170 ],
[ 619.102 , 120 ],
[ 626.823 , 200 ],
[ 629.739 , 200 ],
[ 735.896 , 1000 ],
[ 743.720 , 400 ],
[ 993.880 , 60 ],
[ 1068.650 , 70 ],
[ 1131.720 , 90 ],
[ 1229.830 , 90 ],
[ 1418.380 , 90 ],
[ 1428.580 , 90 ],
[ 1436.090 , 90 ],
[ 2974.720 , 15 ],
[ 2982.670 , 12 ],
[ 3126.199 , 10 ],
[ 3369.808 , 12 ],
[ 3369.908 , 40 ],
[ 3417.904 , 50 ],
[ 3418.006 , 15 ],
[ 3447.703 , 60 ],
[ 3454.195 , 50 ],
[ 3460.524 , 25 ],
[ 3464.339 , 30 ],
[ 3466.579 , 30 ],
[ 3472.571 , 60 ],
[ 3498.064 , 25 ],
[ 3501.216 , 30 ],
[ 3515.191 , 25 ],
[ 3520.472 , 150 ],
[ 3593.526 , 50 ],
[ 3593.640 , 30 ],
[ 3600.169 , 15 ],
[ 3633.665 , 20 ],
[ 3682.243 , 20 ],
[ 3685.736 , 12 ],
[ 3701.225 , 10 ],
[ 4537.754 , 10 ],
[ 4540.380 , 10 ],
[ 4704.395 , 15 ],
[ 4708.862 , 12 ],
[ 4710.067 , 10 ],
[ 4712.066 , 10 ],
[ 4715.347 , 15 ],
[ 4752.732 , 10 ],
[ 4788.927 , 12 ],
[ 4790.220 , 10 ],
[ 4827.344 , 10 ],
[ 4884.917 , 100 ],
[ 4892.09 , 50 ],
[ 4955.38 , 15 ], 
[ 4957.03 , 100 ],
[ 4994.93 , 15 ],
[ 5005.159 , 4 ],
[ 5031.35 , 25 ],
[ 5037.751 , 50 ],
[ 5074.20 , 10 ],
[ 5080.38 , 15 ],
[ 5113.68 , 10 ],
[ 5116.5 , 15 ],
[ 5120.51 , 10 ],
[ 5122.26 , 15 ],
[ 5144.938 , 50 ],
[ 5145.01 , 50 ],
[ 5151.96 , 10 ],
[ 5188.61 , 15 ],
[ 5193.13 , 15 ],
[ 5193.22 , 15 ],
[ 5203.90 , 15 ],
[ 5208.86 , 7 ],
[ 5210.57 , 5 ],
[ 5222.35 , 5 ],
[ 5234.03 , 5 ],
[ 5274.04 , 4 ],
[ 5280.09 , 5 ],
[ 5298.19 , 15 ],
[ 5304.76 , 70 ],
[ 5330.778 , 25 ],
[ 5341.094 , 100 ],
[ 5343.283 , 60 ],
[ 5349.21 , 15 ],
[ 5355.18 , 15 ],
[ 5355.42 , 15 ],
[ 5360.01 , 15 ],
[ 5400.562 , 60 ],
[ 5562.766 , 5 ],
[ 5656.659 , 10 ],
[ 5719.225 , 5 ],
[ 5748.298 , 12 ],
[ 5764.419 , 80 ],
[ 5804.450 , 12 ],
[ 5820.156 , 40 ],
[ 5852.488 , 500 ],
[ 5872.828 , 100 ],
[ 5881.895 , 100 ],
[ 5902.462 , 60 ],
[ 5906.429 , 60 ],
[ 5944.834 , 100 ],
[ 5965.471 , 100 ],
[ 5974.627 , 100 ],
[ 5975.534 , 120 ],
[ 5987.907 , 80 ],
[ 6029.997 , 100 ],
[ 6074.338 , 100 ],
[ 6096.163 , 80 ],
[ 6128.450 , 60 ],
[ 6143.063 , 100 ],
[ 6163.594 , 120 ],
[ 6182.146 , 250 ],
[ 6217.281 , 150 ],
[ 6266.495 , 150 ],
[ 6304.789 , 60 ],
[ 6334.428 , 100 ],
[ 6382.992 , 120 ],
[ 6402.246 , 200 ],
[ 6506.528 , 150 ],
[ 6532.882 , 60 ],
[ 6598.953 , 150 ],
[ 6652.093 , 70 ],
[ 6678.276 , 90 ],
[ 6717.043 , 20 ],
[ 6929.467 , 100 ],
[ 7024.050 , 90 ],
[ 7032.413 , 100 ],
[ 7051.292 , 50 ],
[ 7059.107 , 80 ],
[ 7173.938 , 100 ],
[ 7245.167 , 100 ],
[ 7438.900 , 100 ],
[ 7472.439 , 40 ],
[ 7488.871 , 90 ],
[ 7535.774 , 80 ],
[ 7544.044 , 60 ],
[ 7724.628 , 100 ],
[ 7839.055 , 300 ],
[ 7927.118 , 400 ],
[ 7936.996 , 700 ],
[ 7943.181 , 2000 ],
[ 8082.458 , 2000 ],
[ 8118.549 , 1000 ],
[ 8128.911 , 600 ],
[ 8136.406 , 3000 ],
[ 8248.70 ,  30 ],
[ 8259.379 , 2500 ],
[ 8266.077 , 2500 ],
[ 8267.117 , 800 ],
[ 8300.326 , 6000 ],
[ 8365.749 , 1500 ],
[ 8377.606 , 8000 ],
[ 8417.159 , 1000 ],
[ 8418.427 , 4000 ],
[ 8463.358 , 1500 ],
[ 8484.444 , 800 ],
[ 8495.360 , 5000 ],
[ 8544.696 , 600 ],
[ 8571.352 , 1000 ],
[ 8591.259 , 4000 ],
[ 8634.647 , 6000 ],
[ 8647.041 , 3000 ],
[ 8654.383 , 15000 ],
[ 8655.522 , 4000 ],
[ 8679.492 , 5000 ],
[ 8681.921 , 5000 ],
[ 8704.112 , 2000 ],
[ 8771.656 , 4000 ],
[ 8780.621 , 12000 ],
[ 8783.753 , 10000 ],
[ 8830.907 , 500 ],
[ 8853.867 , 7000 ],
[ 8865.306 , 1000 ],
[ 8865.755 , 1000 ],
[ 8919.501 , 3000 ],
[ 8988.570 , 2000 ],
[ 9148.670 , 6000 ],
[ 9201.760 , 6000 ],
[ 9220.060 , 4000 ],
[ 9221.580 , 2000 ],
[ 9226.690 , 2000 ],
[ 9275.520 , 1000 ],
[ 9300.850 , 6000 ],
[ 9310.580 , 1500 ],
[ 9313.970 , 3000 ],
[ 9326.510 , 6000 ],
[ 9373.310 , 2000 ],
[ 9425.380 , 5000 ],
[ 9459.210 , 3000 ],
[ 9486.680 , 5000 ],
[ 9534.160 , 5000 ],
[ 9547.400 , 3000 ],
[ 9665.420 , 1000 ],
[ 9837.47 , 20 ],
[ 9900.58 , 40 ],
[ 9902.31 , 30 ],
[ 9915.13 , 20 ],
[ 9936.83 , 10 ],
[ 9938.35 , 15 ],
[ 9947.94 , 15 ],
[ 10005.54 , 20 ],
[ 10007.31 , 30 ],
[ 10295.420 , 800 ],
[ 10562.410 , 2000 ],
[ 10620.70  , 400 ],
[ 10798.070 , 1500 ],
[ 10844.480 , 2000 ],
[ 11143.020 , 3000 ],
[ 11177.528 , 3500 ],
[ 11390.434 , 1600 ],
[ 11409.134 , 1100 ],
[ 11522.746 , 3000 ],
[ 11525.020 , 1500 ],
[ 11536.344 , 950 ],
[ 11601.537 , 500 ],
[ 11614.081 , 1200 ],
[ 11688.002 , 300 ],
[ 11766.792 , 2000 ],
[ 11789.044 , 1500 ],
[ 11789.889 , 500 ],
[ 11984.912 , 1000 ],
[ 12066.334 , 3000 ],
[ 12459.389 , 800 ],
[ 12689.201 , 1000 ],
[ 12912.014 , 1100 ],
[ 13219.241 , 700 ],
[ 15230.714 , 800 ],
[ 17161.930 , 400 ],
[ 18035.801 , 400 ],
[ 18083.211 , 1000 ],
[ 18221.109 , 350 ],
[ 18227.020 , 250 ],
[ 18276.680 , 2500 ],
[ 18282.619 , 2000 ],
[ 18303.971 , 1200 ],
[ 18359.119 , 250 ],
[ 18384.850 , 1200 ],
[ 18389.949 , 2000 ],
[ 18402.840 , 1000 ],
[ 18422.391 , 1200 ],
[ 18458.650 , 300 ],
[ 18475.789 , 400 ],
[ 18591.551 , 900 ],
[ 18597.699 , 1600 ],
[ 18618.961 , 350 ],
[ 18625.160 , 550 ],
[ 21041.295 , 1200 ],
[ 21708.145 , 750 ],
[ 22247.350 , 300 ],
[ 22428.131 , 350 ],
[ 22530.400 , 2250 ],
[ 22661.811 , 400 ],
[ 23100.510 , 600 ],
[ 23260.301 , 1000 ],
[ 23373.000 , 1050 ],
[ 23565.359 , 850 ],
[ 23636.520 , 3500 ],
[ 23701.641 , 300 ],
[ 23709.199 , 1100 ],
[ 23951.420 , 1800 ],
[ 23956.461 , 600 ],
[ 23978.119 , 1000 ],
[ 24098.539 , 200 ],
[ 24161.420 , 500 ],
[ 24249.641 , 600 ],
[ 24365.051 , 1500 ],
[ 24371.600 , 800 ],
[ 24447.850 , 400 ],
[ 24459.400 , 700 ],
[ 24776.461 , 300 ],
[ 24928.881 , 550 ],
[ 25161.689 , 250 ],
[ 25524.369 , 650 ],
[ 28386.211 , 125 ],
[ 30200.000 , 150 ],
[ 33173.090 , 250 ],
[ 33352.352 , 450 ],
[ 33901.000 , 1300 ],
[ 33912.102 , 2200 ],
[ 34131.309 , 600 ],
[ 34471.441 , 100 ],
[ 35834.781 , 120 ]
]

argon = [
[ 802.859 , 20 ],
[ 806.471 , 100 ],
[ 806.869 , 60 ],
[ 807.218 , 30 ],
[ 807.653 , 40 ],
[ 809.927 , 50 ],
[ 816.232 , 120 ],
[ 816.464 , 70 ],
[ 820.124 , 80 ],
[ 825.346 , 120 ],
[ 826.365 , 120 ],
[ 834.392 , 150 ],
[ 835.002 , 100 ],
[ 842.805 , 100 ],
[ 866.800 , 180 ],
[ 869.754 , 150 ],
[ 876.058 , 180 ],
[ 879.947 , 180 ],
[ 894.310 , 150 ],
[ 1048.220 , 1000 ],
[ 1066.660 , 500 ],
[ 3200.370 , 8 ],
[ 3319.340 , 7 ],
[ 3373.470 , 7 ],
[ 3393.730 , 7 ],
[ 3461.070 , 7 ],
[ 3554.306 , 7 ],
[ 3606.522 , 7 ],
[ 3770.369 , 20 ],
[ 3834.679 , 7 ],
[ 3947.505 , 7 ],
[ 3948.979 , 35 ],
[ 4044.418 , 50 ],
[ 4158.590 , 400 ],
[ 4164.180 , 50 ],
[ 4181.884 , 50 ],
[ 4190.713 , 100 ],
[ 4191.029 , 50 ],
[ 4198.317 , 200 ],
[ 4200.674 , 400 ],
[ 4251.185 , 25 ],
[ 4259.362 , 200 ],
[ 4266.286 , 100 ],
[ 4272.169 , 150 ],
[ 4300.101 , 100 ],
[ 4333.561 , 100 ],
[ 4335.338 , 50 ],
[ 4345.168 , 25 ],
[ 4510.733 , 100 ],
[ 4522.323 , 20 ],
[ 4596.097 , 15 ],
[ 4628.441 , 7 ],
[ 4702.316 , 15 ],
[ 5151.391 , 5 ],
[ 5162.285 , 15 ],
[ 5187.746 , 20 ],
[ 5221.271 , 7 ],
[ 5421.352 , 5 ],
[ 5451.652 , 10 ],
[ 5495.874 , 25 ],
[ 5506.113 , 5 ],
[ 5558.702 , 25 ],
[ 5572.541 , 10 ],
[ 5606.733 , 35 ],
[ 5650.704 , 20 ],
[ 5739.520 , 10 ],
[ 5834.263 , 5 ],
[ 5860.310 , 10 ],
[ 5882.624 , 15 ],
[ 5888.584 , 25 ],
[ 5912.085 , 50 ],
[ 5928.813 , 15 ],
[ 5942.669 , 5 ],
[ 5987.302 , 7 ],
[ 5998.999 , 5 ],
[ 6025.150 , 5 ],
[ 6032.127 , 70 ],
[ 6043.223 , 35 ],
[ 6052.723 , 10 ],
[ 6059.372 , 20 ],
[ 6098.803 , 7 ],
[ 6105.635 , 10 ],
[ 6145.441 , 10 ],
[ 6170.174 , 7 ],
[ 6173.096 , 10 ],
[ 6212.503 , 10 ],
[ 6215.938 , 5 ],
[ 6296.872 , 7 ],
[ 6307.657 , 15 ],
[ 6369.575 , 7 ],
[ 6384.717 , 20 ],
[ 6416.307 , 70 ],
[ 6538.112 , 15 ],
[ 6604.853 , 15 ],
[ 6660.676 , 5 ],
[ 6664.051 , 5 ],
[ 6677.282 , 100 ],
[ 6752.834 , 150 ],
[ 6756.163 , 5 ],
[ 6766.612 , 15 ],
[ 6871.289 , 150 ],
[ 6879.582 , 5 ],
[ 6888.174 , 10 ],
[ 6937.664 , 50 ],
[ 6951.478 , 7 ],
[ 6960.250 , 7 ],
[ 6965.431 , 10000 ],
[ 7030.251 , 150 ],
[ 7067.218 , 10000 ],
[ 7068.736 , 100 ],
[ 7107.478 , 25 ],
[ 7125.820 , 25 ],
[ 7147.042 , 1000 ],
[ 7158.839 , 15 ],
[ 7206.980 , 70 ],
[ 7265.172 , 15 ],
[ 7270.664 , 7 ],
[ 7272.936 , 2000 ],
[ 7311.716 , 35 ],
[ 7316.005 , 25 ],
[ 7350.814 , 5 ],
[ 7353.293 , 70 ],
[ 7372.118 , 200 ],
[ 7383.980 , 10000 ],
[ 7392.980 , 20 ],
[ 7412.337 , 15 ],
[ 7425.294 , 10 ],
[ 7435.368 , 25 ],
[ 7436.297 , 10 ],
[ 7503.869 , 20000 ],
[ 7514.652 , 15000 ],
[ 7635.106 , 25000 ],
[ 7723.761 , 15000 ],
[ 7724.207 , 10000 ],
[ 7891.075 , 10 ],
[ 7948.176 , 20000 ],
[ 8006.157 , 20000 ],
[ 8014.786 , 25000 ],
[ 8053.308 , 7 ],
[ 8103.693 , 20000 ],
[ 8115.311 , 35000 ],
[ 8264.522 , 10000 ],
[ 8392.270 , 20 ],
[ 8408.210 , 15000 ],
[ 8424.648 , 20000 ],
[ 8521.442 , 15000 ],
[ 8605.776 , 7 ],
[ 8667.944 , 4500 ],
[ 8849.910 , 180 ],
[ 9075.394 , 20 ],
[ 9122.967 , 35000 ],
[ 9194.638 , 550 ],
[ 9224.499 , 15000 ],
[ 9291.531 , 400 ],
[ 9354.220 , 1600 ],
[ 9657.786 , 25000 ],
[ 9784.503 , 4500 ],
[ 10052.060 , 180 ],
[ 10332.720 , 30 ],
[ 10470.054 , 1600 ],
[ 10478.034 , 13 ],
[ 10506.500 , 180 ],
[ 10673.565 , 200 ],
[ 10681.773 , 11 ],
[ 10733.870 , 30 ],
[ 10759.160 , 30 ],
[ 11078.869 , 11 ],
[ 11106.460 , 30 ],
[ 11441.832 , 12 ],
[ 11488.109 , 400 ],
[ 11668.710 , 200 ],
[ 11719.488 , 12 ],
[ 12112.326 , 200 ],
[ 12139.738 , 50 ],
[ 12343.393 , 50 ],
[ 12402.827 , 200 ],
[ 12439.321 , 200 ],
[ 12456.120 , 100 ],
[ 12487.663 , 200 ],
[ 12702.281 , 150 ],
[ 12733.418 , 30 ],
[ 12746.232 , 12 ],
[ 12802.739 , 200 ],
[ 12933.195 , 50 ],
[ 12956.659 , 500 ],
[ 13008.264 , 200 ],
[ 13213.990 , 200 ],
[ 13228.107 , 200 ],
[ 13230.900 , 100 ],
[ 13272.640 , 500 ],
[ 13313.210 , 1000 ],
[ 13367.111 , 1000 ],
[ 13499.410 , 30 ],
[ 13504.191 , 1000 ],
[ 13573.617 , 11 ],
[ 13599.333 , 30 ],
[ 13622.659 , 400 ],
[ 13678.550 , 200 ],
[ 13718.577 , 1000 ],
[ 13825.715 , 10 ],
[ 13907.478 , 10 ],
[ 14093.640 , 200 ],
[ 15046.500 , 100 ],
[ 15172.690 , 25 ],
[ 15329.340 , 10 ],
[ 15989.490 , 30 ],
[ 16519.859 , 30 ],
[ 16940.580 , 500 ],
[ 18427.760 , 12 ],
[ 20616.230 , 50 ],
[ 20986.109 , 30 ],
[ 23133.199 , 20 ],
[ 23966.520 , 20 ]
]

mercury = [
[ 2247.550,     5],
[ 2302.060,    20],
[ 2302.065,    20],
[ 2323.200,    15],
[ 2340.570,     5],
[ 2345.430,    20],
[ 2345.440,    20],
[ 2352.480,    20],
[ 2378.320,   100],
[ 2378.325,   100],
[ 2380.000,    20],
[ 2380.004,    20],
[ 2399.349,    40],
[ 2399.380,    40],
[ 2399.729,    20],
[ 2399.730,    20],
[ 2400.490,    10],
[ 2441.060,     5],
[ 2446.900,    20],
[ 2446.900,    20],
[ 2464.060,    15],
[ 2464.064,    15],
[ 2481.999,    40],
[ 2482.000,    40],
[ 2482.713,    30],
[ 2482.720,    30],
[ 2483.820,    40],
[ 2483.821,    40],
[ 2534.769,    90],
[ 2534.770,    90],
[ 2536.506, 15000],
[ 2536.520, 15000],
[ 2563.860,    25],
[ 2563.861,    25],
[ 2576.290,    25],
[ 2576.290,    25],
[ 2578.910,     5],
[ 2625.190,    15],
[ 2639.780,     5],
[ 2652.040,   250],
[ 2652.043,   250],
[ 2653.683,   400],
[ 2653.690,   400],
[ 2655.130,   100],
[ 2655.130,   100],
[ 2674.910,     5],
[ 2698.830,    50],
[ 2698.831,    50],
[ 2699.380,    50],
[ 2752.780,    80],
[ 2752.783,    80],
[ 2759.710,    20],
[ 2759.710,    20],
[ 2803.460,    40],
[ 2803.471,    40],
[ 2804.430,    30],
[ 2804.438,    30],
[ 2805.340,     2],
[ 2806.770,     2],
[ 2856.939,    50],
[ 2856.940,    50],
[ 2893.598,   150],
[ 2893.600,   150],
[ 2925.410,    60],
[ 2925.413,    60],
[ 2967.280,  1200],
[ 2967.283,  1200],
[ 3021.500,   300],
[ 3021.500,   300],
[ 3023.470,   120],
[ 3023.476,   120],
[ 3025.608,    30],
[ 3025.610,    30],
[ 3027.490,    50],
[ 3027.490,    50],
[ 3125.670,   400],
[ 3125.670,   400],
[ 3131.550,   320],
[ 3131.551,   320],
[ 3131.840,   320],
[ 3131.842,   320],
[ 3341.480,    80],
[ 3341.481,    80],
[ 3650.150,  2800],
[ 3650.157,  2800],
[ 3654.839,   300],
[ 3654.840,   300],
[ 3662.880,    80],
[ 3662.883,    80],
[ 3663.280,   240],
[ 3663.281,   240],
[ 3701.432,    30],
[ 3701.440,    30],
[ 3704.170,    35],
[ 3704.170,    35],
[ 3801.660,    30],
[ 3801.660,    30],
[ 3901.867,    20],
[ 3901.870,    20],
[ 3906.370,    60],
[ 3906.372,    60],
[ 4046.560,  1800],
[ 4046.572,  1800],
[ 4077.830,   150],
[ 4077.838,   150],
[ 4108.050,    40],
[ 4108.057,    40],
[ 4339.220,   250],
[ 4339.224,   250],
[ 4347.490,   400],
[ 4347.496,   400],
[ 4358.330,  4000],
[ 4358.337,  4000],
[ 4883.000,     5],
[ 4889.910,     5],
[ 4916.068,    80],
[ 4916.070,    80],
[ 4970.370,     5],
[ 4980.640,     5],
[ 5102.700,    20],
[ 5120.640,    40],
[ 5137.940,    20],
[ 5290.740,    20],
[ 5316.780,     5],
[ 5354.050,    60],
[ 5384.630,    30],
[ 5460.740,  1100],
[ 5460.753,  1100],
[ 5549.630,    30],
[ 5675.860,   160],
[ 5675.922,   160],
[ 5769.598,   240],
[ 5769.600,   240],
[ 5789.660,   100],
[ 5790.660,   280],
[ 5790.663,   280],
[ 5803.780,   140],
[ 5859.250,    60],
[ 5871.980,    20],
[ 6072.713,    20],
[ 6072.720,    20],
[ 6234.400,    30],
[ 6234.402,    30],
[ 6716.429,   160],
[ 6716.430,   160],
[ 6907.461,   250],
[ 6907.520,   250],
[ 7081.900,   250],
[ 7091.860,   200],
[ 7728.820,    20],
[10139.750,  2000],
[10229.600,    40],
[10298.200,    20],
[10333.000,    20],
[11287.400,   240],
[11287.407,   240],
[13209.950,   120],
[13426.570,   140],
[13468.380,    60],
[13505.580,    80],
[13570.210,   500],
[13673.510,   450],
[13950.550,   200],
[15295.820,   500],
[16881.480,   100],
[16920.160,   400],
[16942.000,   300],
[17072.789,   500],
[17109.930,   400],
[17116.750,    20],
[17198.670,    20],
[17213.199,    20],
[17329.410,    70],
[17436.180,    30],
[18130.381,    50],
[19700.170,    40]
]

cadmium = [
[ 2288.022, 1500],
[ 2491.000,    3],
[ 2508.910,   10],
[ 2518.590,   15],
[ 2525.196,   25],
[ 2544.613,   50],
[ 2553.465,   25],
[ 2565.789,    3],
[ 2580.106,   50],
[ 2584.870,    3],
[ 2592.026,   30],
[ 2602.048,   25],
[ 2628.979,   50],
[ 2632.190,   40],
[ 2639.420,   75],
[ 2660.325,   50],
[ 2677.540,  100],
[ 2677.748,   25],
[ 2712.505,   75],
[ 2733.820,   50],
[ 2763.894,  100],
[ 2764.230,   50],
[ 2774.958,   50],
[ 2836.900,  200],
[ 2868.180,  100],
[ 2880.767,  200],
[ 2881.224,   50],
[ 2980.620, 1000],
[ 2981.362,  200],
[ 2981.845,   50],
[ 3080.822,  150],
[ 3082.593,   30],
[ 3133.167,  200],
[ 3252.524,  300],
[ 3261.055,  300],
[ 3403.652,  800],
[ 3466.200, 1000],
[ 3467.655,  800],
[ 3499.952,   25],
[ 3610.508, 1000],
[ 3612.873,  800],
[ 3614.453,   60],
[ 3649.558,   20],
[ 3981.926,   10],
[ 4306.672,    8],
[ 4412.989,    3],
[ 4662.352,    8],
[ 4678.149,  200],
[ 4799.912,  300],
[ 5085.822, 1000],
[ 5154.660,    6],
[ 6099.142,  300],
[ 6111.490,  100],
[ 6325.166,  100],
[ 6330.013,   30],
[ 6438.470, 2000],
[ 6778.116,   30],
[ 7345.670, 1000],
[ 8200.309,    5],
[ 9292.000,   20],
[10394.600,   20],
[11655.000,   15],
[14491.000,   35],
[15712.000,   80],
[19125.000,   55],
[24378.000,   25],
[25455.000,   35]
]

from collections import OrderedDict

elements = OrderedDict([('Ne',neon),
                        ('Ar',argon),
                        ('Hg',mercury),
                        ('Cd',cadmium)])
