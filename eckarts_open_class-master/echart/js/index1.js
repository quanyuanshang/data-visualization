//为了防止变量污染，采用立即执行函数
(function () {
    var myChart = echarts.init(document.
        querySelector('.bar .chart'));
    option = {
        color: ["#2f89cf"],
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        grid: {
            left: '0%',
            top: '10px',
            right: '0%',
            bottom: '4%',
            containLabel: true
        },
        xAxis: [
            {
                type: 'category',
                data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                axisTick: {
                    alignWithLabel: true
                },
                axisLabel: {
                    color: "rgba(255,255,255,.6)",
                    fontSize: '6'
                },
                axisLine: {
                    show: false
                }


            }
        ],
        yAxis: [
            {
                type: 'value',
                axisLabel: {
                    color: "rgba(255,255,255,.6)",
                    fontSize: '12'
                },
                axisLine: {
                    lineSyle: {
                        color: "rgba(255,255,255,.1)",
                        width: 2,
                    }
                },
                splitLine: {
                    lineStyle: {
                        color: "rgba(255,255,255,.1)"
                    }
                }

            }

        ],
        series: [
            {
                name: 'Direct',
                type: 'bar',
                barWidth: '35%',
                data: [10, 52, 200, 334, 390, 330, 220],
                itemStyle: {
                    barBorderRadius: 5

                }
            }
        ]
    };
    myChart.setOption(option);
    //让图表跟随屏幕自动的去适应
    window.addEventListener('resize', function () {
        myChart.resize();
    });
})();




(function () {
    var myChart = echarts.init(document.querySelector('.bar2 .chart'));
    var myColor = ["#1089E7", "#F57474", "#56D0E3", "#F8B448", "#8B78F6"];
    var option = {

        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },

        grid: {
            top: "10%",
            left: "22%",
            bottom: "10%"
        },
        xAxis: {
            type: 'value',
            boundaryGap: [0, 0.01],
            xAxis: {
                show: false
            },
        },
        yAxis: [

            {
                type: "category",
                // y轴更换第一个对象更换data数据
                data: ["HTML5", "CSS3", "javascript", "VUE", "NODE"],
                // y轴更换第二个对象更换data数据
                // 不显示y轴的线
                axisLine: {
                    show: false
                },
                // 不显示刻度
                axisTick: {
                    show: false
                },
                // 把刻度标签里面的文字颜色设置为白色
                axisLabel: {
                    color: "#fff"
                }
            },
            {
                show: true,
                data: [702, 350, 610, 793, 664],
                // 不显示y轴的线
                axisLine: {
                    show: false
                },
                // 不显示刻度
                axisTick: {
                    show: false
                },
                axisLabel: {

                    fontSize: 12,
                    color: "#fff"

                }
            }
        ],


        series: [
            {
                name: "条",

                type: 'bar',

                yAxisIndex: 0,
                // 柱子之间的距离
                barCategoryGap: 50,
                //柱子的宽度
                barWidth: 10,
                // 柱子设为圆角
                itemStyle: {

                    barBorderRadius: 20,
                    color: function (params) {
                        // dataIndex 是当前柱子的索引号
                        return myColor[params.dataIndex];

                    }
                }, label: {

                    show: true,
                    // 图形内显示
                    position: "inside",
                    // 文字的显示格式
                    formatter: "{c}%"

                }, data: [70, 34, 60, 78, 69]


            },
            {
                yAxisIndex: 1,
                name: "框",
                type: "bar",
                barCategoryGap: 50,
                barWidth: 15,
                itemStyle: {
                    color: "none",
                    borderColor: "#00c1de",
                    borderWidth: 3,
                    barBorderRadius: 15
                },
                data: [100, 100, 100, 100, 100]

            }
        ]

    };
    myChart.setOption(option);
    //让图表跟随屏幕自动的去适应
    window.addEventListener('resize', function () {
        myChart.resize();
    });
})();