document.getElementById("uploadBtn").addEventListener("click", async () => {
    document.getElementById("statusText").innerText =
        "Files uploaded successfully";
});

document.getElementById("compareBtn").addEventListener("click", async () => {

    document.getElementById("rowsChanged").innerText = 25;
    document.getElementById("columnsChanged").innerText = 4;
    document.getElementById("newRows").innerText = 12;
    document.getElementById("deletedRows").innerText = 6;

    document.getElementById("statusText").innerText =
        "Comparison completed";

    document.getElementById("resultTable").innerHTML = `
        <tr>
            <td>Sheet1</td>
            <td>B12</td>
            <td>100</td>
            <td>250</td>
            <td>Modified</td>
        </tr>
        <tr>
            <td>Sheet2</td>
            <td>D5</td>
            <td>Active</td>
            <td>Inactive</td>
            <td>Modified</td>
        </tr>
    `;
});

document.getElementById("downloadBtn").addEventListener("click", async () => {
    document.getElementById("statusText").innerText =
        "Downloading report...";
});