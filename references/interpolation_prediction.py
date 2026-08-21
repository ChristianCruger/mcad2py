"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt

from mcad2py.runtime import sin, cos, mc_max, mc_min, power, col, matrix, transpose, vec_set, augment, matcol, rows, last, matelem, reverse, csort, GrubbsClassic, trim, linterp, lspline, pspline, cspline, interp, polyint, polyiter, polycoeff, rationalint, Thielecoeff, Thiele, predict, Spline2, Binterp, DWS, index_build, derivative, range_sum, arange, sample, static_axis, plot_axis, plot_trace, vectorize
from mcad2py.units import ureg


# examples from support.ptc.com/help/mathcad/

# Example: Least-Square Spline

a = matrix(
    [309.4, 3560, 377.359],
    [320.2, 3400, 368.782],
    [329.8, 3800, 389.872],
    [334, 3360, 366.606],
    [339.2, 3120, 353.27],
    [342.3, 3600, 379.473],
    [345.4, 3520, 375.233],
    [348.5, 3160, 355.528],
    [353.6, 3360, 366.606],
    [355.6, 3720, 385.746],
    [358.6, 3080, 350.999],
    [361.6, 3520, 375.233],
    [364.7, 3480, 373.095],
    [368.6, 3560, 377.359],
    [370.6, 3680, 383.667],
    [374.6, 3760, 387.814],
    [377.6, 3680, 383.667],
    [381.5, 3760, 387.814],
    [384.4, 3080, 350.999],
    [387.3, 3680, 383.667],
    [390.2, 3800, 389.872],
    [393.1, 3880, 393.954],
    [396, 3840, 391.918],
    [398.9, 3360, 366.606],
    [402.7, 3920, 395.98],
    [405.6, 3120, 353.27],
    [408.4, 3760, 387.814],
    [412.2, 3360, 366.606],
    [415.1, 3920, 395.98],
    [417.9, 3320, 364.417],
    [420.7, 3080, 350.999],
    [425.4, 3600, 379.473],
    [427.2, 4360, 417.612],
    [430.9, 3360, 366.606],
    [432.8, 3800, 389.872],
    [436.5, 3160, 355.528],
    [439.2, 3800, 389.872],
    [442.9, 4400, 419.524],
    [445.6, 4200, 409.878],
    [449.3, 3880, 393.954],
    [452, 4600, 428.952],
    [454.7, 3640, 381.576],
    [458.3, 4240, 411.825],
    [461.9, 4360, 417.612],
    [464.6, 4080, 403.98],
    [468.2, 3880, 393.954],
    [471.7, 4840, 440],
    [474.4, 4000, 400],
    [477.1, 3920, 395.98],
    [480.6, 4840, 440],
    [483.3, 4840, 440],
    [486.8, 4480, 423.32],
    [489.4, 4240, 411.825],
    [492.1, 3960, 397.995],
    [495.6, 3640, 381.576],
    [498.2, 3880, 393.954],
    [501.7, 3840, 391.918],
    [504.3, 3480, 373.095],
    [507.7, 4560, 427.083],
    [510.3, 4200, 409.878],
    [513.8, 4160, 407.922],
    [517.2, 3880, 393.954],
    [519.8, 4560, 427.083],
    [523.2, 3720, 385.746],
    [525.8, 3720, 385.746],
    [529.2, 4440, 421.426],
    [532.6, 4000, 400],
    [535.1, 4120, 405.956],
    [538.5, 3560, 377.359],
    [541.9, 4680, 432.666],
    [544.4, 3960, 397.995],
    [547.8, 3960, 397.995],
    [551.2, 3760, 387.814],
    [553.7, 4760, 436.348],
    [557, 5160, 454.313],
    [560.4, 5120, 452.548],
    [563.7, 4560, 427.083],
    [567.1, 5240, 457.821],
    [569.6, 5520, 469.894],
    [572.9, 5520, 469.894],
    [575.4, 5880, 484.974],
    [578.7, 5920, 486.621],
    [582, 4840, 440],
    [585.3, 5800, 481.664],
    [588.6, 6200, 497.996],
    [591, 6840, 523.068],
    [595.1, 7160, 535.164],
    [597.6, 7600, 551.362],
    [600.9, 7960, 564.269],
    [604.1, 9120, 603.987],
    [607.4, 9560, 618.385],
    [610.7, 9840, 627.375],
    [613.1, 10200, 638.749],
    [616.3, 11200, 669.328],
    [619.6, 12400, 704.273],
    [622.8, 12640, 711.056],
    [625.3, 13400, 732.12],
    [628.5, 17000, 824.621],
    [632.5, 16520, 812.896],
    [634.9, 17320, 832.346],
    [638.1, 19040, 872.697],
    [641.4, 18960, 870.862],
    [644.6, 20360, 902.441],
    [647.8, 20960, 915.642],
    [651, 21960, 937.23],
    [653.4, 21080, 918.259],
    [657.4, 20080, 896.214],
    [659.8, 20040, 895.321],
    [663, 18880, 869.022],
    [666.1, 17720, 841.903],
    [668.5, 16840, 820.731],
    [672.5, 16680, 816.823],
    [674.9, 15520, 787.909],
    [678.8, 15680, 791.96],
    [682, 13360, 731.027],
    [684.4, 12760, 714.423],
    [688.3, 12320, 701.997],
    [690.7, 11480, 677.643],
    [693.9, 11880, 689.348],
    [697, 10160, 637.495],
    [700.9, 10240, 640],
    [704.1, 10160, 637.495],
    [706.5, 10040, 633.719],
    [709.6, 11200, 669.328],
    [712.7, 12320, 701.997],
    [716.7, 11360, 674.092],
    [719, 12480, 706.541],
    [722.1, 14880, 771.492],
    [725.3, 15840, 795.99],
    [728.4, 14760, 768.375],
    [730.7, 16000, 800],
    [733.9, 18240, 854.166],
    [737.8, 19480, 882.723],
    [740.1, 21280, 922.605],
    [744, 23520, 969.948],
    [747.1, 26520, 1029.95],
    [751, 27800, 1054.51],
    [754.1, 32800, 1145.43],
    [756.4, 32480, 1139.82],
    [759.5, 38680, 1243.86],
    [762.6, 40800, 1277.5],
    [766.5, 42560, 1304.76],
    [768.9, 43880, 1324.84],
    [772, 49600, 1408.55],
    [775.8, 53080, 1457.12],
    [778.1, 57280, 1513.67],
    [782, 55720, 1492.92],
    [784.3, 58440, 1528.92],
    [788.2, 59800, 1546.61],
    [790.5, 58320, 1527.35],
    [793.6, 61880, 1573.28],
    [797.5, 59480, 1542.47],
    [800.6, 59280, 1539.87],
    [803.6, 55800, 1493.99],
    [806, 55160, 1485.4],
    [809.8, 51560, 1436.11],
    [812.9, 46440, 1362.94],
    [816, 44320, 1331.47],
    [819.1, 38640, 1243.22],
    [822.1, 33120, 1151],
    [825.2, 29480, 1085.91],
    [828.3, 26240, 1024.5],
    [831.4, 22920, 957.497],
    [834.4, 20920, 914.768],
    [837.5, 17720, 841.903],
    [840.6, 16960, 823.65],
    [843.7, 17080, 826.559],
    [846.7, 15000, 774.597],
    [849.8, 16160, 803.99],
    [852.9, 15040, 775.629],
    [855.2, 16400, 809.938],
    [859, 15800, 794.984],
    [862.1, 15800, 794.984],
    [865.2, 16480, 811.911],
    [869, 16600, 814.862],
    [871.3, 17160, 828.493],
    [875.1, 18880, 869.022],
    [877.4, 18800, 867.179],
    [881.3, 20440, 904.212],
    [884.3, 21520, 927.793],
    [886.7, 19200, 876.356],
    [890.5, 23960, 978.979],
    [893.6, 24200, 983.87],
    [896.6, 23160, 962.497],
    [898.9, 25160, 1003.19],
    [902.8, 24840, 996.795],
    [905.8, 25960, 1019.02],
    [908.9, 26400, 1027.62],
    [912, 27280, 1044.61],
    [915, 28120, 1060.57],
    [918.9, 29920, 1093.98],
    [921.2, 30520, 1104.9],
    [925, 30920, 1112.12],
    [927.3, 30440, 1103.45],
    [931.1, 31640, 1124.99],
    [933.4, 34480, 1174.39],
    [937.3, 35640, 1193.98],
    [940.3, 37240, 1220.49],
    [942.7, 37120, 1218.52],
    [945.7, 36880, 1214.58],
    [948.8, 37520, 1225.07],
    [952.6, 36600, 1209.96],
    [955.7, 36040, 1200.67],
    [958.8, 38160, 1235.48],
    [961.9, 39080, 1250.28],
    [964.9, 37600, 1226.38],
    [968, 37600, 1226.38],
    [970.3, 38000, 1232.88],
    [974.2, 38120, 1234.83],
    [977.2, 38040, 1233.53],
    [980.3, 36680, 1211.28],
    [983.4, 39560, 1257.93],
    [986.5, 40160, 1267.44],
    [990.3, 42200, 1299.23],
    [992.6, 42320, 1301.08],
    [995.7, 46560, 1364.7],
    [999.6, 45720, 1352.33],
    [1001.9, 47760, 1382.17],
    [1005.7, 51840, 1440],
    [1008.8, 48760, 1396.57],
    [1011.9, 49720, 1410.25],
    [1014.2, 53000, 1456.02],
    [1018.1, 51600, 1436.66],
    [1021.2, 54240, 1472.96],
    [1024.3, 55080, 1484.32],
    [1027.3, 54000, 1469.69],
    [1030.4, 55600, 1491.31],
    [1033.5, 54600, 1477.84],
    [1035.9, 54760, 1480],
    [1039.7, 53120, 1457.67],
    [1042, 51520, 1435.55],
    [1045.9, 51320, 1432.76],
    [1049, 48840, 1397.71],
    [1051.3, 47720, 1381.59],
    [1055.2, 47280, 1375.21],
    [1058.3, 46720, 1367.04],
    [1061.4, 41200, 1283.74],
    [1064.5, 42880, 1309.66],
    [1067.7, 39320, 1254.11],
    [1070.8, 38640, 1243.22],
    [1073.9, 35560, 1192.64],
    [1077, 35280, 1187.94],
    [1080.1, 35080, 1184.57],
    [1083.2, 32960, 1148.22],
    [1085.6, 32520, 1140.53],
    [1089.5, 30360, 1102],
    [1092.6, 29440, 1085.17],
    [1094.9, 29320, 1082.96],
    [1098, 29160, 1080],
    [1101.2, 28840, 1074.06],
    [1105.1, 28920, 1075.55],
    [1107.4, 29760, 1091.05],
    [1110.6, 27760, 1053.76],
    [1113.7, 27680, 1052.24],
    [1116.8, 29520, 1086.65],
    [1120, 29440, 1085.17],
    [1123.1, 29280, 1082.22],
    [1127, 30280, 1100.55],
    [1129.4, 31840, 1128.54],
    [1133.3, 30560, 1105.62],
    [1135.7, 32320, 1137.01],
    [1138.8, 31360, 1120],
    [1142, 31040, 1114.27],
    [1144.3, 33120, 1151],
    [1148.3, 36240, 1203.99],
    [1150.6, 32960, 1148.22],
    [1153.8, 33640, 1160],
    [1157, 36200, 1203.33],
    [1160.1, 41200, 1283.74],
    [1163.3, 38000, 1232.88],
    [1166.4, 37920, 1231.58],
    [1169.6, 39640, 1259.21],
    [1172.8, 42200, 1299.23],
    [1176, 42760, 1307.82],
    [1179.1, 43920, 1325.44],
    [1181.5, 44760, 1338.06],
    [1185.5, 44320, 1331.47],
    [1187.9, 46480, 1363.52],
    [1191.1, 45080, 1342.83],
    [1194.2, 46520, 1364.11],
    [1197.4, 47040, 1371.71],
    [1200.6, 45400, 1347.59],
    [1203.8, 43280, 1315.75],
    [1206.2, 45920, 1355.29],
    [1209.4, 45440, 1348.18],
    [1212.6, 44080, 1327.86],
    [1215.8, 41360, 1286.23],
    [1219.8, 42400, 1302.31],
    [1222.2, 40360, 1270.59],
    [1225.4, 38440, 1240],
    [1227.8, 39760, 1261.11],
    [1231.8, 37280, 1221.15],
    [1235.1, 37440, 1223.76],
    [1238.3, 35480, 1191.3],
    [1240.7, 32440, 1139.12],
    [1243.9, 32000, 1131.37],
    [1247.1, 31800, 1127.83],
    [1250.4, 29480, 1085.91],
    [1252.8, 31320, 1119.29],
    [1256, 29840, 1092.52],
    [1259.3, 28480, 1067.33],
    [1262.5, 27600, 1050.71],
    [1265.8, 26920, 1037.69],
    [1269, 24720, 994.384],
    [1272.2, 24080, 981.428],
    [1275.5, 22720, 953.31],
    [1278.8, 22880, 956.661],
    [1282, 22240, 943.186],
    [1285.3, 20480, 905.097],
    [1287.7, 21200, 920.869],
    [1291, 18560, 861.626],
    [1294.2, 20160, 897.998],
    [1297.5, 19000, 871.78],
    [1300, 19920, 892.637],
    [1303.2, 19080, 873.613],
    [1306.5, 18480, 859.767],
    [1309.8, 18480, 859.767],
    [1313.1, 17560, 838.093],
    [1315.6, 17760, 842.852],
    [1318.9, 16880, 821.706],
    [1322.1, 17360, 833.307],
    [1325.4, 16160, 803.99],
    [1328.7, 14640, 765.245],
    [1331.2, 14840, 770.454],
    [1335.4, 14280, 755.778],
    [1337.8, 14000, 748.331],
    [1340.3, 14000, 748.331],
    [1343.6, 14120, 751.532],
    [1346.1, 14480, 761.052],
    [1350.3, 13480, 734.302],
    [1352.8, 13120, 724.431],
    [1356.1, 12560, 708.802],
    [1358.6, 12960, 720],
    [1362.8, 12040, 693.974],
    [1365.3, 12400, 704.273],
    [1368.6, 10720, 654.828],
    [1371.9, 12880, 717.774],
    [1374.4, 11560, 680],
    [1377.8, 10600, 651.153],
    [1381.1, 11280, 671.714],
    [1384.5, 9640, 620.967],
    [1387, 9320, 610.574],
    [1390.4, 9800, 626.099],
    [1392.9, 8840, 594.643],
    [1396.3, 10040, 633.719],
    [1399.7, 8720, 590.593],
    [1402.2, 7520, 548.452],
    [1405.6, 8280, 575.5],
    [1408.1, 7040, 530.66],
    [1411.5, 8360, 578.273],
    [1414.9, 7080, 532.165],
    [1418.3, 7040, 530.66],
    [1421.7, 6680, 516.914],
    [1423.4, 6320, 502.792],
    [1427.6, 7040, 530.66],
    [1430.2, 7200, 536.656],
    [1433.6, 6560, 512.25],
    [1436.1, 5520, 469.894],
    [1439.5, 5920, 486.621],
    [1443, 6280, 501.199],
    [1445.5, 5400, 464.758],
    [1449.8, 5920, 486.621],
    [1452.4, 5880, 484.974],
    [1455.8, 6480, 509.117],
    [1458.4, 6240, 499.6],
    [1461.8, 5760, 480],
    [1465.3, 5800, 481.664],
    [1467.9, 6080, 493.153],
    [1471.3, 5960, 488.262],
    [1473.9, 5320, 461.303],
    [1477.4, 5760, 480],
    [1480.8, 5760, 480],
    [1483.4, 5400, 464.758],
    [1486, 5960, 488.262],
    [1489.5, 6600, 513.809],
    [1493, 5640, 474.974],
    [1495.6, 6640, 515.364],
    [1499.1, 6240, 499.6],
    [1501.7, 5280, 459.565],
    [1504.3, 6960, 527.636],
    [1507.8, 5440, 466.476],
    [1510.4, 5680, 476.655],
    [1514.8, 5520, 469.894],
    [1517.4, 5880, 484.974],
    [1521, 5840, 483.322],
    [1522.7, 6160, 496.387],
    [1526.2, 5720, 478.33],
    [1529.8, 5200, 456.07],
    [1533.3, 5360, 463.033],
    [1535.9, 5320, 461.303],
    [1539.5, 5560, 471.593],
    [1543, 5760, 480],
    [1545.7, 5560, 471.593],
    [1548.3, 4880, 441.814],
    [1551.9, 5480, 468.188],
    [1554.5, 4440, 421.426],
    [1558.1, 5080, 450.777],
    [1560.7, 5520, 469.894],
    [1564.3, 4840, 440],
    [1567, 4880, 441.814],
    [1569.7, 3880, 393.954],
    [1573.2, 3960, 397.995],
    [1575.9, 3440, 370.945],
    [1579.5, 4040, 401.995],
    [1582.2, 4680, 432.666],
    [1584.9, 4240, 411.825],
    [1589.4, 4080, 403.98],
    [1592.1, 4040, 401.995],
    [1594.8, 3840, 391.918],
    [1599.3, 3920, 395.98],
    [1602, 4920, 443.621],
    [1604.7, 4240, 411.825],
    [1607.4, 3800, 389.872],
    [1611.1, 3800, 389.872],
    [1614.7, 4000, 400],
    [1617.4, 3600, 379.473],
    [1620.2, 4160, 407.922],
    [1623.8, 3920, 395.98],
    [1626.5, 3560, 377.359],
    [1629.3, 3240, 360],
    [1632.9, 3760, 387.814],
    [1636.6, 4400, 419.524],
    [1639.3, 3920, 395.98],
    [1642.1, 3360, 366.606],
    [1645.8, 3840, 391.918],
    [1647.6, 4440, 421.426],
    [1652.2, 4280, 413.763],
    [1655, 3880, 393.954],
    [1657.7, 5040, 448.999],
    [1662.3, 4040, 401.995],
    [1664.2, 4240, 411.825],
    [1667.9, 3880, 393.954],
    [1670.7, 3800, 389.872],
    [1674.4, 4000, 400],
    [1678.1, 4800, 438.178],
    [1680, 4640, 430.813],
    [1683.7, 4360, 417.612],
    [1686.5, 4560, 427.083],
    [1689.3, 4360, 417.612],
    [1692.1, 4200, 409.878],
    [1695.8, 3720, 385.746],
    [1698.6, 4720, 434.511],
    [1701.4, 4880, 441.814],
    [1705.2, 5000, 447.214],
    [1709, 4520, 425.206],
    [1711.8, 4920, 443.621],
    [1714.6, 4960, 445.421],
    [1718.4, 4960, 445.421],
    [1720.3, 4240, 411.825],
    [1724, 3960, 397.995],
    [1726.9, 4080, 403.98],
    [1729.7, 5000, 447.214],
    [1733.5, 5040, 448.999],
    [1736.4, 4800, 438.178],
    [1741.1, 5240, 457.821],
    [1743, 5640, 474.974],
    [1746.8, 3760, 387.814],
    [1749.7, 4400, 419.524],
    [1752.6, 5120, 452.548],
    [1756.4, 4240, 411.825],
    [1758.3, 4920, 443.621],
    [1762.2, 4240, 411.825],
    [1766, 4920, 443.621],
    [1768.9, 4360, 417.612],
    [1772.7, 4640, 430.813],
    [1774.7, 5400, 464.758],
    [1778.5, 4320, 415.692],
    [1781.4, 5120, 452.548],
    [1785.3, 4720, 434.511],
    [1787.2, 4520, 425.206],
    [1790.1, 5080, 450.777],
    [1794, 5040, 448.999],
    [1797.9, 4200, 409.878],
    [1800.8, 4560, 427.083],
    [1803.8, 4160, 407.922],
    [1806.7, 4160, 407.922],
    [1809.6, 4160, 407.922],
    [1813.5, 4600, 428.952],
    [1816.5, 4080, 403.98],
    [1820.4, 4360, 417.612],
    [1822.4, 4840, 440],
    [1826.3, 4240, 411.825],
    [1828.3, 3760, 387.814],
    [1832.2, 4440, 421.426],
    [1835.2, 4720, 434.511],
    [1838.1, 4640, 430.813],
    [1842.1, 4880, 441.814],
    [1845.1, 4160, 407.922],
    [1848.1, 4200, 409.878],
    [1852, 4240, 411.825],
    [1855, 5920, 486.621],
    [1859, 4240, 411.825],
    [1860, 5480, 468.188],
    [1864, 4720, 434.511],
    [1868, 4800, 438.178],
    [1871, 4080, 403.98],
    [1874, 4040, 401.995],
    [1877, 4160, 407.922],
    [1880, 5360, 463.033],
    [1883.1, 4920, 443.621],
    [1887.1, 5360, 463.033],
    [1890.1, 5320, 461.303],
    [1894.2, 4640, 430.813],
    [1896.2, 4560, 427.083],
    [1900.2, 4640, 430.813],
    [1903.3, 6080, 493.153],
    [1906.3, 4840, 440],
    [1909.4, 4920, 443.621],
    [1911.4, 5160, 454.313],
    [1915.5, 5040, 448.999],
    [1919.6, 5760, 480],
    [1921.6, 5280, 459.565],
    [1925.7, 4640, 430.813],
    [1927.8, 5640, 474.974],
    [1931.9, 5560, 471.593],
    [1933.9, 5360, 463.033],
    [1938.1, 4440, 421.426],
    [1941.2, 5200, 456.07],
    [1944.3, 5000, 447.214],
    [1947.4, 5480, 468.188],
    [1950.5, 5480, 468.188],
    [1952.5, 5240, 457.821],
    [1956.7, 5880, 484.974],
    [1959.8, 5160, 454.313],
    [1964, 4440, 421.426],
    [1966.1, 5040, 448.999],
    [1970.2, 5720, 478.33],
    [1973.4, 5080, 450.777],
    [1976.5, 5840, 483.322],
    [1978.6, 6760, 520],
    [1981.7, 5440, 466.476],
    [1987, 5800, 481.664],
    [1989.1, 5520, 469.894],
    [1992.3, 5680, 476.655],
    [1996.5, 5640, 474.974],
    [1999.7, 6320, 502.792],
)

x = matcol(a, 0)

y = matcol(a, 1)

w = matcol(a, 2)

n = 3

# b = Spline2(x, y, n, w)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# print(b)
# TODO unsupported region: needs b, left undefined above

# i = arange(0, b[1], 1)
# TODO unsupported region: needs b, left undefined above

# knots = index_build(i, lambda i: b[i + 2])
# TODO unsupported region: needs b, i, left undefined above

print(mc_min(x))

# print(knots[0])
# TODO unsupported region: needs knots, left undefined above

print(mc_max(x))

# print(knots[len(knots) - 1])
# TODO unsupported region: needs knots, left undefined above

i = arange(0, 100, 1)

range_ = index_build(i, lambda i: i * (mc_max(x) - mc_min(x)) / 101 + mc_min(x))

# spline1 = transpose(Binterp(range_, b))
# TODO unsupported region: needs b, left undefined above

# _fig, _ax = plt.subplots()
# _ax.plot(*plot_trace(plot_axis(x, None), plot_axis(y, None)), label='x', color='#FF0000')
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(matcol(spline1, 0), None)), label='range_', color='#0000FF')
# _ax.axhline(0, color='0.6', linewidth=0.8)
# _ax.axvline(0, color='0.6', linewidth=0.8)
# _ax.grid(True, alpha=0.3)
# _ax.set_xlabel('')
# _ax.set_ylabel('')
# _ax.legend()
# plt.show()
# TODO unsupported region: needs spline1, left undefined above

# print(DWS(b))
# TODO unsupported region: needs b, left undefined above

# print(b[last(b) - 2])
# TODO unsupported region: needs b, left undefined above

level = 0.001

# b2 = Spline2(x, y, n, w, level)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# Nknots = b2[1]
# print(Nknots)
# TODO unsupported region: needs b2, left undefined above

# print(DWS(b2))
# TODO unsupported region: needs b2, left undefined above

# spline2 = transpose(Binterp(range_, b2))
# TODO unsupported region: needs b2, left undefined above

# _fig, _ax = plt.subplots()
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(matcol(spline1, 0), None)), label='range_', color='#0000FF')
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(matcol(spline2, 0), None)), label='range_', color='#FF0000')
# _ax.axhline(0, color='0.6', linewidth=0.8)
# _ax.axvline(0, color='0.6', linewidth=0.8)
# _ax.grid(True, alpha=0.3)
# _ax.set_xlabel('')
# _ax.set_ylabel('')
# _ax.legend()
# plt.show()
# TODO unsupported region: needs spline1, spline2, left undefined above

# b3 = Spline2(x, y, n)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# print(DWS(b3))
# TODO unsupported region: needs b3, left undefined above

# b4 = Spline2(x, y, n, 0.5)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# print(DWS(b4))
# TODO unsupported region: needs b4, left undefined above

# fd = matcol(spline1, 1)
# TODO unsupported region: needs spline1, left undefined above

# sd = matcol(spline1, 2)
# TODO unsupported region: needs spline1, left undefined above

# td = matcol(spline1, 3)
# TODO unsupported region: needs spline1, left undefined above

# _fig, _ax = plt.subplots()
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(fd, None)), label='range_', color='#FF0000')
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(10 * sd, None)), label='range_', color='#008000')
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(100 * td, None)), label='range_', color='#0000FF')
# _ax.axhline(0, color='0.6', linewidth=0.8)
# _ax.axvline(0, color='0.6', linewidth=0.8)
# _ax.grid(True, alpha=0.3)
# _ax.set_xlabel('')
# _ax.set_ylabel('')
# _ax.legend()
# plt.show()
# TODO unsupported region: needs fd, sd, td, left undefined above

Knots = range_

SplineW = Spline2(x, y, n, w, Knots)

spline3 = transpose(Binterp(range_, SplineW))

print(DWS(SplineW))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(y, None)), label='x', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(spline3, None)), label='range_', color='#0000FF')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

SplineNW = Spline2(x, y, n, Knots)

print(DWS(SplineNW))

index = matelem(GrubbsClassic(y, 0.55), 0, 0)

print(index)

X_no = trim(x, index)

Y_no = trim(y, index)

W_no = trim(w, index)

# b_no = Spline2(X_no, Y_no, n, W_no)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# WithOutlier = DWS(b)
# print(WithOutlier)
# TODO unsupported region: needs b, left undefined above

# WithoutOutlier = DWS(b_no)
# print(WithoutOutlier)
# TODO unsupported region: needs b_no, left undefined above

i = arange(0, 200, 1)

range_ = index_build(i, lambda i: 700 + i)

# spline_no = transpose(Binterp(range_, b_no))
# TODO unsupported region: needs b_no, left undefined above

# spline = transpose(Binterp(range_, b))
# TODO unsupported region: needs b, left undefined above

# _fig, _ax = plt.subplots()
# _ax.plot(*plot_trace(plot_axis(x, None), plot_axis(y, None)), label='x', color='#008000')
# _ax.plot(*plot_trace(plot_axis(x[index], None), plot_axis(y[index], None)), label='x[index]', color='#FF0000')
# _ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(matcol(spline, 0), None)), label='range_', color='#FF0000')
# _ax.plot(*plot_trace(plot_axis(x, None), plot_axis(matcol(spline_no, 0), None)), label='x', color='#008000')
# _ax.axhline(0, color='0.6', linewidth=0.8)
# _ax.axvline(0, color='0.6', linewidth=0.8)
# _ax.grid(True, alpha=0.3)
# _ax.set_xlabel('')
# _ax.set_ylabel('')
# _ax.legend()
# plt.show()
# TODO unsupported region: needs spline, spline_no, left undefined above

# Example: Cubic Spline Interpolation

Cu = matrix(
    [0.367, 20.15],
    [0.591, 24.41],
    [0.796, 28.78],
    [0.892, 29.57],
    [1.547, 34.82],
    [1.903, 37.41],
    [2.15, 39.12],
    [2.902, 44.09],
    [2.894, 45.07],
    [3.697, 50.24],
    [4.703, 54.98],
    [5.87, 61.38],
    [6.307, 65.51],
    [6.421, 66.25],
    [7.03, 70.53],
    [7.422, 73.42],
    [7.898, 75.7],
    [9.47, 89.57],
    [9.484, 91.14],
)

Cu = csort(Cu, 1)

vx = matcol(Cu, 1)

vy = matcol(Cu, 0)

c = cspline(vx, vy)

fitc = lambda x: interp(c, vx, vy, x)

l = lspline(vx, vy)

fitl = lambda x: interp(l, vx, vy, x)

p = pspline(vx, vy)

fitp = lambda x: interp(p, vx, vy, x)

m = arange(19, 95, 1)

x = index_build(m, lambda m: m)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(vx, None), plot_axis(vy, None)), label='vx', color='#00008B')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(fitl(x), None)), label='x', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(vx, None), plot_axis(fitp(x), None)), label='vx', color='#068149')
_ax.plot(*plot_trace(plot_axis(vx, None), plot_axis(fitc(x), None)), label='vx', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

n = arange(0, 65, 1)

x = index_build(n, lambda n: 19 + n / 10)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(vx, None), plot_axis(vy, None)), label='vx', color='#000000')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(fitl(x), None)), label='x', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(vx, None), plot_axis(fitp(x), None)), label='vx', color='#068149')
_ax.plot(*plot_trace(plot_axis(vx, None), plot_axis(fitc(x), None)), label='vx', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

sd_l = lambda x: derivative(lambda x: fitl(x), x, 2)

print(sd_l(vx[0]))

print(sd_l(vx[last(vx)]))

sd_p = lambda x: derivative(lambda x: fitp(x), x, 2)

print(sd_p(vx[0]))

print(sd_p(vx[1]))

print(sd_p(vx[last(vx) - 1]))

print(sd_p(vx[last(vx)]))

# Example: Linear Interpolation

Y = col(2.7, 7.6, 3.6, 4.7, 8.4, 1.8, 6.9, 6, 2.2, 8.6)

i = arange(0, rows(Y) - 1, 1)

X = index_build(i, lambda i: i)

j = arange(0, 95, 1)

X_int = index_build(j, lambda j: 0.1 * j)

Y_int = index_build(j, lambda j: linterp(X, Y, X_int[j]))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(X, None), plot_axis(Y, None)), label='X', color='#00008B')
_ax.plot(*plot_trace(plot_axis(X_int, None), plot_axis(Y_int, None)), label='X_int', color='#000000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Linear Prediction 1

y = col(3719, 3722, 3624, 3539, 3613, 3365, 3422, 3317, 3283, 3410, 3520, 3451, 3466, 3377, 3391, 3339, 3196, 3146, 2985, 3053, 3105, 3081, 2925, 3029, 3041, 3163, 2980, 3029, 2875, 2794, 2692, 2696, 2610, 2470, 2493, 2459, 2391, 2301, 2349, 2365, 2423, 2295, 2277, 2235, 2225, 2218, 2279, 2286, 2285, 2193, 2250, 2247, 2277, 2296, 2236, 2267, 2295, 2417, 2388, 2347, 2257, 2333, 2201, 2009, 2049, 2171, 2179, 2115, 2042, 2046, 2042, 1934, 2088, 2071, 2026, 2107, 2026, 2162, 2171, 2137, 2286, 2240, 2169, 2190, 2427, 2663, 2787, 2938, 3158, 3193, 3304, 3356, 3487, 3656, 3911, 4032, 3902, 3868, 3884, 3857, 3981, 3928, 4007, 4060, 4068, 3971, 4102, 4091, 3933, 3843, 3894, 3858, 3954, 3837, 3910, 3871, 3756, 3832, 3474, 3420, 3402, 3441, 3393, 3385, 3324, 3253, 3253, 3280, 3303, 3175, 3391, 3422, 3567, 3607, 3563, 3628, 3653, 3750, 3928, 3889, 4248, 4430, 4851, 5272, 6059, 6124, 6493, 6798, 7078, 6772, 6721, 6420, 6666, 6605, 6426, 6276, 6045, 5854, 5849, 5864, 5724, 5995, 5945, 5998, 6056, 6060, 6107, 6146, 5792, 5867, 5742, 5626, 5539, 5585, 5458, 5534, 5362, 5398, 5331, 5052, 5115, 5009, 4952, 4769, 4821, 4670, 4968, 4738, 4769, 4600, 4642, 4798, 4699, 4816, 4718, 4768, 4514, 4627, 4714, 4893, 4856, 4923, 4924, 4975, 5276, 5285, 5391, 5992, 6589, 6687, 6967, 6877, 6720, 6645, 6682, 6509, 6612, 6619, 6533, 6429, 6640, 6627, 6464, 6468, 6740, 7127, 7453, 7894, 7830, 8012, 8329, 8545, 8691, 8967, 9089, 9194, 9538, 9928, 10160, 10250, 9824, 9891, 9734, 9630, 9464, 9414, 8919, 8987, 8671, 8346, 7943, 7751, 7549, 7287, 7287, 7301, 6991, 6632, 6988, 6980, 6858, 6968, 6786, 6908, 6982, 6908, 6797, 6818, 6719, 6811, 6915, 6701, 6718, 6727, 6721, 6668, 6500, 6898, 6879, 6759, 6924, 6798, 6684, 6518, 6739, 6688, 6673, 6465, 6534, 6488, 6275, 6018, 6052, 5998, 5837, 5783, 5587, 5718)

i = arange(0, last(y), 1)

observed_data = index_build(i, lambda i: i)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(observed_data, None), plot_axis(y, None)), label='observed_data', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

Nprev = 15

Nnext = 10

y_pred = predict(y, Nprev, Nnext)

k = arange(0, last(y_pred), 1)

predicted_values = index_build(k, lambda k: k + last(y))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(observed_data, None), plot_axis(y, None)), label='observed_data', color='#00008B')
_ax.plot(*plot_trace(plot_axis(predicted_values, None), plot_axis(y_pred, None)), label='predicted_values', color='#FF0000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# How predict Works

N_previous = 3

N_future = 4

X = col(2.7, 5.7, 6.8, 2.9, 5.1, 6.2, 2.5)

# shown, not computed: Eq(X[k], c[0] * X[k - 3] + c[1] * X[k - 2] + c[2] * X[k - 1])

c = col(0.8814224392928995, -0.417638429300996, 0.5225643330159371)

Xpred = vec_set(None, 0, c[0] * X[4] + c[1] * X[5] + c[2] * X[6])

Xpred = vec_set(Xpred, 1, c[0] * X[5] + c[1] * X[6] + c[2] * Xpred[0])

Xpred = vec_set(Xpred, 2, c[0] * X[6] + c[1] * Xpred[0] + c[2] * Xpred[1])

Xpred = vec_set(Xpred, 3, c[0] * Xpred[0] + c[1] * Xpred[1] + c[2] * Xpred[2])

print(Xpred)

print(predict(X, N_previous, N_future))

# Error Messages

# The error messages returned by predict are often due to its arguments. In one case, the error message is related to the algorithm itself:

# Mathcad reports an error here: This value must be less than the number of data points.
try:
    print(predict(col(2.7, 8.2, 1.9, 0.3, 2.7), 5, 3))
except Exception as _err:
    print('error:', _err)

# The predicted values cannot be a linear function of all the data points. You can use up to (n - 1) data points:

print(predict(col(2.7, 8.2, 1.9, 0.3, 2.7), 4, 3))

# It is best to choose a value that is not too large relative to the amount of data points.

# Example: Linear Prediction 2

n = arange(0, 59, 1)

F = index_build(n, lambda n: sin(12 * math.pi * (n / 100)) + cos(6 * math.pi * (n / 100)))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(n, None), plot_axis(sample(lambda n: F[n], n), None)), label='F[n]', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('n')
_ax.set_ylabel('')
_ax.legend()
plt.show()

k = arange(60, 79, 1)

CF = index_build(k, lambda k: sin(12 * math.pi * (k / 100)) + cos(6 * math.pi * (k / 100)))

tPF = predict(F, 10, 20)

r = arange(0, 19, 1)

PF = index_build(k, lambda k: tPF[k - 60])

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(n, None), plot_axis(sample(lambda n: F[n], n), None)), label='F[n]', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(static_axis(k, n), None), plot_axis(static_axis(CF[k], n), None)), label='k', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(n, None), plot_axis(static_axis(PF[k], n), None)), label='PF[k]', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('n')
_ax.set_ylabel('')
_ax.legend()
plt.show()

p = arange(0, 24, 1)

G = index_build(p, lambda p: p)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(p, None), plot_axis(sample(lambda p: G[p], p), None)), label='G[p]', color='#FF0000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('p')
_ax.set_ylabel('')
_ax.legend()
plt.show()

s = arange(25, 74, 1)

tCG = None
def _recur_tCG(_idx, tCG):
    for s in _idx:
        tCG = vec_set(tCG, s - 25, s)
    return tCG

tCG = _recur_tCG(s, tCG)

CG = index_build(s, lambda s: tCG[s - 25])

tPG = predict(G, 10, 100)

u = arange(25, 124, 1)

PG = index_build(u, lambda u: tPG[u - 25])

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(p, None), plot_axis(sample(lambda p: G[p], p), None)), label='G[p]', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(static_axis(s, p), None), plot_axis(static_axis(CG[s], p), None)), label='s', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(static_axis(u, p), None), plot_axis(static_axis(PG[u], p), None)), label='u', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('p')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Estimating Prior Values

X1 = transpose(matrix([0.81, 1.07, 1.83, 2.25, 3.01, 2.91, 1.87, 1.53, 1.40, 1.05]))

m = arange(0, last(X1), 1)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(m, None), plot_axis(sample(lambda m: X1[m], m), None)), label='X1[m]', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('m')
_ax.set_ylabel('')
_ax.legend()
plt.show()

Nvals = 3

Nterms = 7

P = predict(reverse(X1), Nterms, Nvals)
print(P)

X2 = reverse(P)
print(X2)

k = arange(-Nvals, -1, 1)

t = arange(-1, 0, 1)

con = lambda t: (X2[2] - X1[0]) / -1 * t + X1[0]

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(m, None), plot_axis(sample(lambda m: X1[m], m), None)), label='X1[m]', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(static_axis(k, m), None), plot_axis(static_axis(X2[k + Nvals], m), None)), label='k', color='#068149')
_ax.plot(*plot_trace(plot_axis(static_axis(t, m), None), plot_axis(static_axis(con(t), m), None)), label='t', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('m')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Polynomial Interpolation

x = col(301, 306, 318, 332, 333)

y = col(.02, 0.2, -0.04, .06, .17)

print(polyint(x, y, 328))

r = arange(0, mc_max(x) - mc_min(x), 1)

range_ = index_build(r, lambda r: r + mc_min(x))

PI = index_build(r, lambda r: polyint(x, y, r + mc_min(x))[0])

error = index_build(r, lambda r: polyint(x, y, r + mc_min(x))[1])

PI_Error = None
def _recur_PI_Error(_idx, PI_Error):
    for r in _idx:
        PI_Error = vec_set(PI_Error, (r, 0), PI[r] - error[r])
    return PI_Error

PI_Error = _recur_PI_Error(r, PI_Error)

def _recur_PI_Error(_idx, PI_Error):
    for r in _idx:
        PI_Error = vec_set(PI_Error, (r, 1), PI[r] + error[r])
    return PI_Error

PI_Error = _recur_PI_Error(r, PI_Error)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(y, None)), label='x', color='#008000')
_ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(PI, None)), label='range_', color='#0000FF')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(PI_Error, None)), label='x', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

i = arange(0, rows(x) - 1, 1)

c = index_build(i, lambda i: polycoeff(x, y)[i])

print(c)

f = lambda z: range_sum(i, lambda i: c[i] * power(z, i))

F = index_build(r, lambda r: f(r + mc_min(x)))

f1 = lambda z: derivative(lambda z: f(z), z, 1)

F1 = index_build(r, lambda r: f1(r + mc_min(x)))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(y, None)), label='x', color='#008000')
_ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(F, None)), label='range_', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(F1, None)), label='x', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

N_max = len(x) - 1

epsilon = 0.01

print(polyiter(x, y, 328, N_max, epsilon))

print(polyint(x, y, 328)[0])

# Example: Thiele Interpolation

npts = 10

j = arange(0, npts, 1)

f = lambda x: 1 / (1 + 500 * (x - 0.5)**2)

x_data = index_build(j, lambda j: j / npts)

y_data = vectorize(f(x_data))

c = Thielecoeff(x_data, y_data)

x = arange(0, 1, 0.01 - 0)

f_int = lambda x: Thiele(x_data, c, x)

fratint = lambda x: rationalint(x_data, y_data, x)

i = arange(0, 1, 0.0002 - 0)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(static_axis(x_data, x), None), plot_axis(static_axis(y_data, x), None)), label='x_data', color='#0000FF')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(sample(lambda x: f(x), x), None)), label='f(x)', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(static_axis(x_data, x), None), plot_axis(sample(lambda x: f_int(x), x), None)), label='x_data', color='#008000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(sample(lambda x: f_int(x) - f(x), x), None)), label='f_int(x) - f(x)', color='#800080')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()

X = transpose(matrix([0, 1, 2, 3, 4]))

Y = transpose(matrix([1, 1, 3 / 5, 2 / 5, 5 / 17]))

print(Thielecoeff(X, Y))

X = transpose(matrix([1, 2, 3, 4, 0]))

Y = transpose(matrix([1, 3 / 5, 2 / 5, 5 / 17, 1]))

vGamma = Thielecoeff(X, Y)
print(vGamma)

Q = lambda a: vGamma[0] + (a - X[0]) / (vGamma[1] + (a - X[1]) / (vGamma[2] + (a - X[2]) / (vGamma[3] + (a - X[3]) / vGamma[4])))

x = arange(-10, 10, -9.9 - -10)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(static_axis(X, x), None), plot_axis(static_axis(Y, x), None)), label='X', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(sample(lambda x: Q(x), x), None)), label='Q(x)', color='#008000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Using Units with the Polynomial Interpolation Functions

# redeclare variables as orig units

m = ureg.m

s = ureg.s

vx = col(4.4, 7.9, 3, 9.1, 2.0, 5.7, 2.6, 4, 8.5, 1.9)

vy = 4 / vx

x = 3

xu = m

yu = s

X = vx * xu
print(X)

Y = vy * yu
print(Y)

U = x * xu
print(U)

print(polyint(X, Y, U))

print(polyint(X, Y, 2 * U))

L = len(X) - 1

def _M():
    M = None
    for u in arange(0, L, 1):
        for v in arange(0, 1, 1):
            M = vec_set(M, (u, v), polyint(X, Y, u * ureg.m)[v])
    return M
M = _M()
print(M)

u = arange(0, L, 1)

I_int = index_build(u, lambda u: matelem(M, u, 0))

E_int = index_build(u, lambda u: matelem(M, u, 1))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_int[u], u), None)), label='I_int[u]', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_int[u] + E_int[u], u), None)), label='I_int[u] + E_int[u]', color='#068149')
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_int[u] - E_int[u], u), None)), label='I_int[u] - E_int[u]', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('u')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Polynomial Iteration

print(polyiter(X, Y, U, 2, 0.1 * s))

print(polyiter(X, Y, U, 5, 0.1 * s))

def P_itr(ord_, err):
    K = None
    N = None
    order = ord_
    error = err
    for u in arange(0, len(X) - 1, 1):
        K = vec_set(K, u, error * s)
        for v in arange(0, 2, 1):
            N = vec_set(N, (u, v), polyiter(X, Y, u * ureg.m, order, error * ureg.s)[v])
    Z = augment(N, K)
    return Z

I_itr = index_build(u, lambda u: matelem(P_itr(3, 0.25), u, 2))

E_itr = index_build(u, lambda u: matelem(P_itr(3, 0.25), u, 3))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_itr[u], u), None)), label='I_itr[u]', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_itr[u] + E_itr[u], u), None)), label='I_itr[u] + E_itr[u]', color='#008000')
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_itr[u] - E_itr[u], u), None)), label='I_itr[u] - E_itr[u]', color='#0000FF')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('u')
_ax.set_ylabel('')
_ax.legend()
plt.show()

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_int[u], u), None)), label='I_int[u]', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_itr[u], u), None)), label='I_itr[u]', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('u')
_ax.set_ylabel('')
_ax.legend()
plt.show()

I0_itr = index_build(u, lambda u: matelem(P_itr(L, 0), u, 2))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I_int[u], u), None)), label='I_int[u]', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(u, None), plot_axis(sample(lambda u: I0_itr[u], u), None)), label='I0_itr[u]', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('u')
_ax.set_ylabel('')
_ax.legend()
plt.show()
