$(document).ready(function() {
    $('.engine-select').on('change', function() {
        $('.translate-form').attr('data-status', 'false');
    });

    let onsubmit = (e) => {
        $('.inspect-row').addClass("d-none");
        $('.inspect-content').html("");

        if ($('.translate-form').attr('data-status') != 'launching') {
            $('.translate-form').attr('data-status', 'launching');

            $.ajax({
                url: `details`,
                data: { 
                    "line": $('.translate-text').val(),
                    "engine_id": $('.engine-select option:selected').val()
                },
                method: "post"
            }).done(function(task_id) {
                longpoll(1000, {
                    url: "get_details",
                    method: "POST",
                    data: { task_id: task_id }
                }, (data) => {
                    if (data.result == 200) {
                        let inspection = data.details;
                        $('.preproc_input').html(inspection['preproc_input'])
                        $('.preproc_output').html(inspection['preproc_output'])
                        $('.postproc_output').html(inspection['postproc_output'])
                        for (sentence of inspection.nbest) {
                            let p = document.createElement("p")
                            $(p).html(sentence)
                            $(p).addClass("mb-1");
                            $(".nbest").append(p)
                        }

                        $(".inspect-row").removeClass("d-none");
                        $('.translate-form').attr('data-status', 'ready');

                        return false;
                    }
                });
            });
        }

        return false;
    }

    $('.translate-form').on('submit', function() {
        return onsubmit()
    });
});

$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
})