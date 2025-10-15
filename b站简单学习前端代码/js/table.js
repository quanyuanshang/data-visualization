//新增数据
function addRow() {
    var table = document.getElementById("dataTable");
    //console.log(table);
    var lenth = table.rows.length;//获取插入位置
    var newrow = table.insertRow(lenth);//插入行
    console.log(newrow);
    //newrow.innerHTML = "123";
    //插入列节点
    var newcol = newrow.insertCell(0);
    newcol.innerHTML = "未命名";
    var newcol2 = newrow.insertCell(1);
    newcol2.innerHTML = "无联系方式";
    var newcol3 = newrow.insertCell(2);
    newcol3.innerHTML = `
        <button onclick="editRow(this)">编辑</button>
        <button onclick="deleteRow(this)">删除</button>`;
}

function deleteRow(button) {
    var row = button.parentNode.parentNode;
    console.log(row);
    row.parentNode.removeChild(row);
}

function editRow(button) {
    var row = button.parentNode.parentNode;
    var name = row.cells[0];
    var contact = row.cells[1];
    var newName = prompt("编辑姓名:", name);
    var newContact = prompt("编辑联系方式:", contact);
    if (newName != "") name.innerHTML = newName;
    if (newContact != "") contact.innerHTML = newContact;
}