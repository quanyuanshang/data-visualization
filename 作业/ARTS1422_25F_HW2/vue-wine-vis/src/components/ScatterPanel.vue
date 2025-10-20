<template>
    <div
        class="panel"
        style="
            border: 1px solid #ddd;
            padding: 10px;
            background: #fff;
            border-radius: 8px;
        "
    >
        <h3>{{ title }}</h3>
        <svg
            ref="svg"
            :width="width"
            :height="height"
            style="background: #fafafa"
        ></svg>
    </div>
</template>

<script>
import * as d3 from 'd3'
import { pointInPolygon } from './lasso.js'

export default {
    name: 'ScatterPanel',
    props: ['title', 'csvpath', 'sharedSelection', 'sharedHoverIndex'],
    //name: 组件名称
    //props: 从父组件接收的参数
    data() {
        return {
            width: 350,
            height: 300,
            data: [],
            margin: { top: 10, right: 10, bottom: 30, left: 30 },
            hoverIndex: null
        }
        //     width/height: SVG画布尺寸
        // data: 存储从CSV加载的数据
        // margin: 图表边距
        // hoverIndex: 当前鼠标悬停的点的索引
    },
    watch: {
        //监听器
        sharedSelection() {
            this.updateHighlights()
        }, //当sharedSelection改变时，自动更新高亮显示
        sharedHoverIndex() {
            this.updateHighlights()
        } //当hoverIndex改变时，自动更新高亮显示
    },
    mounted() {
        this.loadAndDraw() //组件挂载到DOM后，开始加载数据并绘制图表
    },
    methods: {
        async loadAndDraw() {
            const raw = await d3.csv(this.csvpath, d3.autoType)
            // expecting columns: idx, x, y, class
            this.data = raw.map((d) => ({
                idx: +d.idx,
                x: +d.x,
                y: +d.y,
                class: +d.class
            }))

            this.draw()
        },
        draw() {
            const svg = d3.select(this.$refs.svg)
            svg.selectAll('*').remove()
            const innerW = this.width - this.margin.left - this.margin.right
            const innerH = this.height - this.margin.top - this.margin.bottom

            const g = svg
                .append('g')
                .attr(
                    'transform',
                    `translate(${this.margin.left},${this.margin.top})`
                )

            const xExtent = d3.extent(this.data, (d) => d.x)
            const yExtent = d3.extent(this.data, (d) => d.y)

            const x = d3.scaleLinear().domain(xExtent).range([0, innerW]).nice()
            const y = d3.scaleLinear().domain(yExtent).range([innerH, 0]).nice()

            g.append('g')
                .attr('transform', `translate(0,${innerH})`)
                .call(d3.axisBottom(x).ticks(4))
            g.append('g').call(d3.axisLeft(y).ticks(4))

            // points group
            const pts = g.append('g').attr('class', 'points')

            pts.selectAll('circle')
                .data(this.data)
                .enter()
                .append('circle')
                .attr('cx', (d) => x(d.x))
                .attr('cy', (d) => y(d.y))
                .attr('r', 4)
                .attr('fill', (d) => this.colorByClass(d.class))
                .attr('stroke', '#333')
                .attr('stroke-width', 0.6)
                .attr('opacity', 0.95)
                .on('mouseover', (event, d) => {
                    this.$emit('hover-index', d.idx)
                    this.hoverIndex = d.idx
                    this.updateHighlights()
                })
                .on('mouseout', () => {
                    this.$emit('hover-index', null)
                    this.hoverIndex = null
                    this.updateHighlights()
                })

            // lasso handling
            // we implement a simple polygon lasso: record mouse points while left button pressed
            let isDrawing = false
            const lassoPts = []
            const self = this

            svg.on('mousedown', function (event) {
                if (event.button !== 0) return // only left
                isDrawing = true
                lassoPts.length = 0
                const [mx, my] = d3.pointer(event, this)

                const adjustedX = mx - self.margin.left
                const adjustedY = my - self.margin.top
                lassoPts.push([adjustedX, adjustedY])
                g.append('path')
                    .attr('class', 'lasso')
                    .attr('fill', 'rgba(0,0,200,0.05)')
                    .attr('stroke', 'rgba(0,0,200,0.6)')
                    .attr('stroke-width', 2)
                    .attr('stroke-dasharray', '5,5') // 可选：虚线效果
                    .attr('d', d3.line()(lassoPts)) // 添加这行，立即绘制起始点;
            })

            svg.on('mousemove', function (event) {
                if (!isDrawing) return
                const [mx, my] = d3.pointer(event, this)
                const adjustedX = mx - self.margin.left
                const adjustedY = my - self.margin.top
                lassoPts.push([adjustedX, adjustedY])
                g.select('path.lasso').attr('d', d3.line()(lassoPts))
            })

            svg.on('mouseup', (event) => {
                if (!isDrawing) return
                isDrawing = false
                const selected = []
                // convert each point's position
                this.data.forEach((d) => {
                    const px = x(d.x) // 数据点在图表内的x像素位置
                    const py = y(d.y)
                    if (pointInPolygon([px, py], lassoPts)) {
                        //图表内坐标 → SVG坐标
                        selected.push(d.idx)
                    }
                })
                // cleanup lasso path
                g.selectAll('path.lasso').remove()
                // emit selected indices (unique)
                this.$emit('update-selection', Array.from(new Set(selected)))
            })

            // save scales for coordinate checks
            this._x = x
            this._y = y
            this.updateHighlights()
        },
        colorByClass(c) {
            const palette = ['#9b59b6', '#3498db', '#e67e22']
            return palette[(c - 1) % palette.length]
        },
        updateHighlights() {
            const svg = d3.select(this.$refs.svg)
            const circles = svg.selectAll('circle')
            const sel = this.sharedSelection || new Set()
            // 使用共享的悬停状态，如果没有则使用本地状态
            const hover = this.sharedHoverIndex

            circles
                .attr('opacity', function (d) {
                    // highlight logic: if selected globally -> larger/opaque; else if hovered -> highlight; else fade
                    if (sel.size > 0) {
                        // 被选中的点保持完全不透明
                        if (sel.has(d.idx)) return 1.0
                        // 未被选中的点变半透明
                        return 0.25
                    }
                    if (
                        hover !== null &&
                        hover !== undefined &&
                        d.idx === hover
                    ) {
                        return 1.0 // 悬停的点高亮
                    }
                    return 1.0 // 其他点正常显示
                })
                .attr('r', function (d) {
                    const isSelected = sel.has(d.idx)
                    const isHovered =
                        hover !== null && hover !== undefined && d.idx === hover

                    if (isSelected && isHovered) {
                        return 10 // 被选中且悬停：最大
                    }
                    if (isSelected) {
                        return 7 // 仅被选中：中等放大
                    }
                    if (isHovered) {
                        return 6 // 仅悬停：轻微放大
                    }
                    return 4 // 默认大小
                })
                .attr('stroke-width', function (d) {
                    // 悬停的点边框更粗
                    const isSelected = sel.has(d.idx)
                    const isHovered =
                        hover !== null && hover !== undefined && d.idx === hover

                    if (isSelected && isHovered) {
                        return 1.5 // 被选中且悬停：最粗边框
                    }
                    if (isSelected) {
                        return 1 // 仅被选中：中等边框
                    }
                    if (isHovered) {
                        return 1 // 仅悬停：稍粗边框
                    }
                    return 0.6 // 默认边框
                })
        }
    }
}
</script>
