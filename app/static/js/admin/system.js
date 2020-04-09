$(document).ready(function() {
    let users_table = $(".users-table").DataTable({
        processing: true,
        serverSide: true,
        responsive: true,
        ajax: {
            url: "python_feed",
            method: "post"
        },
        columnDefs: [
            {
                targets: 4,
                width: "40%"
            }
        ]
    });
});