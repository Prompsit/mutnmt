$(document).ready(function() {
    let users_table = $(".users-table").DataTable({
        processing: true,
        serverSide: true,
        responsive: true,
        ajax: {
            url: "users_feed",
            method: "post"
        },
        columnDefs: [
            { targets: 0, responsivePriority: 1 },
            { 
                targets: 4,
                responsivePriority: 1,
                className: "actions",
                searchable: false,
                sortable: false,
                render: function(data, type, row) {
                    if ($("#current_user").val() != row[0]) {
                        let template = document.importNode(document.querySelector("#users-table-actions-template").content, true);
                        $(template).find(".delete-user").attr("href", `delete_user?id=${row[0]}`);
                        $(template).find(".delete-user").removeClass("d-none");

                        $(".become-admin").attr("href", "become/admin/" + row[0]);
                        $(".become-expert").attr("href", "become/expert/" + row[0]);
                        $(".become-normal").attr("href", "become/normal/" + row[0]);

                        if (row[5]) { // is admin
                            $(".become-admin").addClass("d-none");
                        } else if (row[6]) { // is expert
                            $(".become-expert").addClass("d-none");
                        } else {
                            $(".become-normal").addClass("d-none");
                        }
                        
                        let ghost = document.createElement('div');
                        ghost.appendChild(template);
                        return ghost.innerHTML;
                    } else {
                        return "";
                    }
                }
            }
        ]
    });
});