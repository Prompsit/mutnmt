let force_quit = false;

$(document).ready(function() {
    let task_id = $('#task_id').val();

    longpoll(5000, {
        url: "../launch_status",
        method: "POST",
        data: { task_id: task_id }
    }, (task_status) => {
        if (task_status.result == 200) {
            $.ajax({
                url: "../launch",
                method: "POST",
                data: { engine_id: task_status.engine_id }
            }).done(function(url) {
                force_quit = true;
                window.location.href = url;
                return false;
            });
    
            return false;
        }
    });
});

$(window).on('beforeunload', () => {
    return !force_quit;
})