$(document).ready(function() {
    let instances_table = $(".instances-table").DataTable({
        processing: true,
        serverSide: true,
        responsive: true,
        ajax: {
            url: "instances_feed",
            method: "post"
        },
        columnDefs: [
            { targets: 0, responsivePriority: 1 },
            { 
                targets: 2,
                render: function(data, type, row) {
                    return (data ? data : "—")
                }
            },
            { 
                targets: 4,
                responsivePriority: 1,
                className: "actions",
                searchable: false,
                sortable: false,
                render: function(data, type, row) {
                    let template = document.importNode(document.querySelector("#instances-table-actions-template").content, true);
                    $(template).find(".stop-engine").attr("href", `stop_engine?id=${row[0]}`);
                    let ghost = document.createElement('div');
                    ghost.appendChild(template);
                    return ghost.innerHTML;
                }
            }
        ]
    });
});