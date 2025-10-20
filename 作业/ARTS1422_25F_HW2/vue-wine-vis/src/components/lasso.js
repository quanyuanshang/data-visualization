// lasso.js
export function pointInPolygon(pt, polygon) {
    // pt = [x,y], polygon = [[x1,y1],[x2,y2],...]
    let x = pt[0], y = pt[1]
    let inside = false
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i][0], yi = polygon[i][1]
        const xj = polygon[j][0], yj = polygon[j][1]
        const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi + 0.0) + xi)
        if (intersect) inside = !inside
    }
    return inside
}

// 第一部分：(yi > y) !== (yj > y)
// 检查当前边是否跨越水平线y
// 如果边的两个端点都在y上方或都在y下方，则不相交
// 只有一个在上方，一个在下方时，才可能相交
// 第二部分：x < (xj - xi) * (y - yi) / (yj - yi) + xi
// 计算射线与当前边的交点的x坐标
// (xj - xi) * (y - yi) / (yj - yi) + xi 是线性插值公式
// 如果待测点的x坐标小于交点x坐标，说明射线确实穿过了这条边

// 遍历过程处理的边：
// 迭代1: j=3, i=0 → 处理边 [0,1] → [0,0] (从顶点3到顶点0)
// 迭代2: j=0, i=1 → 处理边 [0,0] → [1,0] (从顶点0到顶点1)
// 迭代3: j=1, i=2 → 处理边 [1,0] → [1,1] (从顶点1到顶点2)
// 迭代4: j=2, i=3 → 处理边 [1,1] → [0,1] (从顶点2到顶点3)